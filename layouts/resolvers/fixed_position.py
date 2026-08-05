"""FixedPosition resolver: sets a component's position directly."""

from __future__ import annotations

from typing import Any

from layouts.base import Placement
from layouts.composer import ConstraintResolver, ResolverResult
from layouts.constraints import FixedPosition


class FixedPositionResolver:
    """Set a component's position on specified axes."""

    kind = "fixed_position"

    def resolve(
        self,
        constraint: FixedPosition,
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

        existing = current.get(constraint.subject)
        x = constraint.x if constraint.x is not None else (existing.x if existing is not None else 0.0)
        y = constraint.y if constraint.y is not None else (existing.y if existing is not None else 0.0)
        z = constraint.z if constraint.z is not None else (existing.z if existing is not None else 0.0)

        return ResolverResult(
            True,
            {constraint.subject: Placement(subj, x, y, constraint.rotation, z)},
            f"{constraint.subject} @ ({x:.1f}, {y:.1f}, {z:.1f})",
        )


__all__ = ["FixedPositionResolver"]
