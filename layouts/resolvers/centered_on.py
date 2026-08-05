"""CenteredOn resolver: centers a component on one or more axes."""

from __future__ import annotations

from typing import Any

from layouts.base import Placement
from layouts.composer import ConstraintResolver, ResolverResult
from layouts.constraints import CenteredOn
from layouts.resolvers._helpers import estimate_enclosure, interior_bounds


class CenteredOnResolver:
    """Center a component on X and/or Y within the enclosure or relative to another component."""

    kind = "centered_on"

    def resolve(
        self,
        constraint: CenteredOn,
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
        subj_x = existing.x if existing is not None else 0.0
        subj_y = existing.y if existing is not None else 0.0
        subj_z = existing.z if existing is not None else 0.0
        subj_rot = existing.rotation if existing is not None else 0.0

        if constraint.relative_to is None or constraint.relative_to == "enclosure":
            w, d, _ = estimate_enclosure(current, components, config)
            wall = getattr(config, "wall_thickness", 2.0)
            left, right, rear, front = interior_bounds(w, d, wall)
            center_x = (left + right) / 2.0
            center_y = (rear + front) / 2.0
        else:
            target_placement = current.get(constraint.relative_to)
            if target_placement is None:
                return ResolverResult(
                    False, {},
                    f"target {constraint.relative_to!r} not placed yet",
                )
            center_x = target_placement.x
            center_y = target_placement.y

        for axis in constraint.axes:
            if axis == "x":
                subj_x = center_x
            elif axis == "y":
                subj_y = center_y

        return ResolverResult(
            True,
            {constraint.subject: Placement(subj, subj_x, subj_y, subj_rot, subj_z)},
            f"{constraint.subject} centered on {','.join(constraint.axes)}",
        )


__all__ = ["CenteredOnResolver"]
