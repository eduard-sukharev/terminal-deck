"""EdgeAlignment resolver: aligns a component edge to another edge or enclosure wall."""

from __future__ import annotations

from typing import Any

from layouts.base import Placement
from layouts.composer import ConstraintResolver, ResolverResult
from layouts.constraints import EdgeAlignment
from layouts.resolvers._helpers import align_edges, estimate_enclosure, interior_bounds


class EdgeAlignmentResolver:
    """Align a component's edge to another component's edge or the enclosure wall."""

    kind = "edge_alignment"

    def resolve(
        self,
        constraint: EdgeAlignment,
        components: dict[str, Any],
        current: dict[str, Placement],
        config: Any,
        context: dict[str, Any],
    ) -> ResolverResult:
        subj = components.get(constraint.subject)
        if subj is None:
            return ResolverResult(
                False, {},
                f"component {constraint.subject!r} not found",
            )

        subj_size = subj.size()

        if constraint.target == "enclosure":
            w, d, _ = estimate_enclosure(current, components, config, context=context)
            wall = getattr(config, "wall_thickness", 2.0)
            clearance = getattr(getattr(config, "clearance", None), "shell", 0.35)
            left, right, rear, front = interior_bounds(w, d, wall, clearance)
            target_edges = {
                "front": (0.0, front),
                "rear": (0.0, rear),
                "left": (left, 0.0),
                "right": (right, 0.0),
            }
            if constraint.target_edge not in target_edges:
                return ResolverResult(
                    False, {},
                    f"unknown enclosure edge: {constraint.target_edge!r}",
                )
            tx, ty = target_edges[constraint.target_edge]
            target_w, target_d = 0.0, 0.0
        else:
            target_placement = current.get(constraint.target)
            if target_placement is None:
                return ResolverResult(
                    False, {},
                    f"target {constraint.target!r} not placed yet",
                )
            target_comp = components.get(constraint.target)
            if target_comp is None:
                return ResolverResult(
                    False, {},
                    f"target component {constraint.target!r} not found",
                )
            target_size = target_comp.size()
            tx, ty = target_placement.x, target_placement.y
            target_w, target_d = target_size.width, target_size.depth

        x, y = align_edges(
            subj_size.width, subj_size.depth,
            tx, ty, target_w, target_d,
            constraint.subject_edge, constraint.target_edge,
            constraint.offset,
        )

        # Aligning one edge constrains one axis only. Keep whatever the other
        # axis (and z/rotation) already resolved to, so ordering an alignment
        # after a positioning constraint refines it instead of erasing it.
        existing = current.get(constraint.subject)
        if constraint.subject_edge in ("front", "rear"):
            x = existing.x if existing is not None else x
        else:
            y = existing.y if existing is not None else y
        z = existing.z if existing is not None else 0.0
        rotation = existing.rotation if existing is not None else 0.0
        flip_x = existing.flip_x if existing is not None else False

        return ResolverResult(
            True,
            {constraint.subject: Placement(subj, x, y, rotation, z, flip_x)},
            f"{constraint.subject} {constraint.subject_edge} → {constraint.target} "
            f"{constraint.target_edge} @ ({x:.1f}, {y:.1f})",
        )


__all__ = ["EdgeAlignmentResolver"]
