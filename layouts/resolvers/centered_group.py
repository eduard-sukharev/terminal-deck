"""CenteredGroup resolver: centers a group of components on one or more axes."""

from __future__ import annotations

from typing import Any

from layouts.base import Placement
from layouts.composer import ConstraintResolver, ResolverResult
from layouts.constraints import CenteredGroup
from layouts.resolvers._helpers import estimate_enclosure, interior_bounds


class CenteredGroupResolver:
    """Center a group of components on one or more axes.

    Computes the collective bounding box of all subjects, then shifts every
    component by the same delta so the group midpoint aligns with the target
    center.
    """

    kind = "centered_group"

    def resolve(
        self,
        constraint: CenteredGroup,
        components: dict[str, Any],
        current: dict[str, Placement],
        config: Any,
    ) -> ResolverResult:
        if not constraint.subjects:
            return ResolverResult(True, {}, "empty group — nothing to center")

        # Collect bounding box of all subjects that have placements.
        xs: list[float] = []
        ys: list[float] = []
        for name in constraint.subjects:
            comp = components.get(name)
            placement = current.get(name)
            if comp is None or placement is None:
                continue
            box = comp.size()
            xs.extend([placement.x - box.width / 2, placement.x + box.width / 2])
            ys.extend([placement.y - box.depth / 2, placement.y + box.depth / 2])

        if not xs:
            return ResolverResult(False, {}, "no subjects have placements yet")

        group_cx = (min(xs) + max(xs)) / 2.0
        group_cy = (min(ys) + max(ys)) / 2.0

        if constraint.relative_to is None or constraint.relative_to == "enclosure":
            w, d, _ = estimate_enclosure(current, components, config)
            wall = getattr(config, "wall_thickness", 2.0)
            left, right, rear, front = interior_bounds(w, d, wall)
            target_cx = (left + right) / 2.0
            target_cy = (rear + front) / 2.0
        else:
            target_placement = current.get(constraint.relative_to)
            if target_placement is None:
                return ResolverResult(
                    False, {},
                    f"target {constraint.relative_to!r} not placed yet",
                )
            target_cx = target_placement.x
            target_cy = target_placement.y

        dx = target_cx - group_cx if "x" in constraint.axes else 0.0
        dy = target_cy - group_cy if "y" in constraint.axes else 0.0

        placements: dict[str, Placement] = {}
        for name in constraint.subjects:
            comp = components.get(name)
            placement = current.get(name)
            if comp is None or placement is None:
                continue
            placements[name] = Placement(
                comp,
                placement.x + dx,
                placement.y + dy,
                placement.rotation,
                placement.z,
            )

        return ResolverResult(
            True,
            placements,
            f"group centered on {','.join(constraint.axes)} "
            f"(shift dx={dx:.1f}, dy={dy:.1f})",
        )


__all__ = ["CenteredGroupResolver"]
