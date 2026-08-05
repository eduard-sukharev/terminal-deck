"""Region resolver: ensures a component lies within a named region of the enclosure."""

from __future__ import annotations

from typing import Any

from layouts.base import Placement
from layouts.composer import ConstraintResolver, ResolverResult
from layouts.constraints import RegionConstraint
from layouts.resolvers._helpers import estimate_enclosure, interior_bounds


class RegionResolver:
    """Validate that a component lies within a named region of the enclosure interior.

    Regions: ``"upper_half"``, ``"lower_half"``, ``"front_third"``,
    ``"rear_wall"``, ``"left_half"``, ``"right_half"``.

    This is a documentary/validation constraint — it does not adjust
    placement.
    """

    kind = "region"

    def resolve(
        self,
        constraint: RegionConstraint,
        components: dict[str, Any],
        current: dict[str, Placement],
        config: Any,
    ) -> ResolverResult:
        subj = components.get(constraint.subject)
        placement = current.get(constraint.subject)
        if subj is None or placement is None:
            return ResolverResult(
                True, {},
                f"{constraint.subject!r} not placed yet — skipping",
            )

        w, d, _ = estimate_enclosure(current, components, config)
        wall = getattr(config, "wall_thickness", 2.0)
        left, right, rear, front = interior_bounds(w, d, wall)
        box = subj.size()

        comp_left = placement.x - box.width / 2
        comp_right = placement.x + box.width / 2
        comp_rear = placement.y - box.depth / 2
        comp_front = placement.y + box.depth / 2

        region = constraint.region
        inside = False

        if region == "upper_half":
            mid_y = (rear + front) / 2.0
            inside = comp_rear >= mid_y
        elif region == "lower_half":
            mid_y = (rear + front) / 2.0
            inside = comp_front <= mid_y
        elif region == "front_third":
            third = (front - rear) / 3.0
            inside = comp_rear >= front - third
        elif region == "rear_wall":
            third = (front - rear) / 3.0
            inside = comp_front <= rear + third
        elif region == "left_half":
            mid_x = (left + right) / 2.0
            inside = comp_right <= mid_x
        elif region == "right_half":
            mid_x = (left + right) / 2.0
            inside = comp_left >= mid_x
        else:
            return ResolverResult(
                True, {},
                f"unknown region {region!r}",
            )

        return ResolverResult(
            True, {},
            f"{constraint.subject} in {region}: {inside}",
        )


__all__ = ["RegionResolver"]
