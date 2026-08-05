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

        x = target_placement.x + constraint.offset_x
        y = target_placement.y + constraint.offset_y
        z = target_placement.z + constraint.offset_z

        return ResolverResult(
            True,
            {constraint.subject: Placement(subj, x, y, constraint.rotation, z)},
            f"{constraint.subject} @ ({x:.1f}, {y:.1f}, {z:.1f}) rel. to {constraint.target}",
        )


__all__ = ["RelativePlacementResolver"]
