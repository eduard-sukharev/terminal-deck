"""RelativePlacement resolver: places a component at an explicit offset from another."""

from __future__ import annotations

from typing import Any

from layouts.base import Placement
from layouts.composer import ConstraintResolver, ResolverResult
from layouts.constraints import RelativePlacement


class RelativePlacementResolver:
    """Place a component at a fixed offset from another component's origin."""

    kind = "relative_placement"

    def resolve(
        self,
        constraint: RelativePlacement,
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

        target_placement = current.get(constraint.target)
        if target_placement is None:
            return ResolverResult(
                False, {},
                f"target {constraint.target!r} not placed yet",
            )

        offset_x, offset_y, offset_z = (
            constraint.offset_x, constraint.offset_y, constraint.offset_z
        )
        source = "recipe offsets"
        if constraint.use_reference_origin:
            ref_x, ref_y, ref_z = subj.reference_origin()
            # The recipe still owns Z: reference_origin() describes the in-plane
            # mounting offset, not which side of the partner the board sits on.
            offset_x, offset_y = ref_x, ref_y
            offset_z = constraint.offset_z or ref_z
            source = "reference_origin()"

        x = target_placement.x + offset_x
        y = target_placement.y + offset_y
        z = target_placement.z + offset_z
        existing = current.get(constraint.subject)
        rotation = (
            constraint.rotation
            if constraint.rotation is not None
            else (existing.rotation if existing is not None else 0.0)
        )

        return ResolverResult(
            True,
            {constraint.subject: Placement(subj, x, y, rotation, z)},
            f"{constraint.subject} @ ({x:.1f}, {y:.1f}, {z:.1f}) "
            f"rel. to {constraint.target} via {source}",
        )


__all__ = ["RelativePlacementResolver"]
