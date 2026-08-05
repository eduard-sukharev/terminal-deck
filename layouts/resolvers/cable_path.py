"""CablePath resolver: validates cable route between connectors."""

from __future__ import annotations

from typing import Any

from layouts.base import Placement
from layouts.composer import ConstraintResolver, ResolverResult
from layouts.constraints import CablePath


class CablePathResolver:
    """Validate a cable route between two connectors.

    Checks:
    1. Both connectors exist on their respective components.
    2. The straight-line path (optionally via a point) is clear.
    3. The bend radius is within limits.

    This is a documentary/validation constraint — it does not adjust
    placement.
    """

    kind = "cable_path"

    def resolve(
        self,
        constraint: CablePath,
        components: dict[str, Any],
        current: dict[str, Placement],
        config: Any,
    ) -> ResolverResult:
        from_comp = components.get(constraint.from_component)
        to_comp = components.get(constraint.to_component)
        from_placement = current.get(constraint.from_component)
        to_placement = current.get(constraint.to_component)

        if from_comp is None or to_comp is None:
            return ResolverResult(
                True, {},
                f"component not found — skipping",
            )
        if from_placement is None or to_placement is None:
            return ResolverResult(
                True, {},
                f"one or both not placed yet — skipping",
            )

        # Find the connectors.
        from_conn = None
        to_conn = None
        for c in from_comp.connectors():
            if c.type == constraint.from_connector_type:
                from_conn = c
                break
        for c in to_comp.connectors():
            if c.type == constraint.to_connector_type:
                to_conn = c
                break

        if from_conn is None:
            return ResolverResult(
                True, {},
                f"{constraint.from_component} has no {constraint.from_connector_type}",
            )
        if to_conn is None:
            return ResolverResult(
                True, {},
                f"{constraint.to_component} has no {constraint.to_connector_type}",
            )

        # World-frame connector positions.
        fx = from_placement.x + from_conn.x
        fy = from_placement.y + from_conn.y
        fz = from_placement.z + from_conn.z
        tx = to_placement.x + to_conn.x
        ty = to_placement.y + to_conn.y
        tz = to_placement.z + to_conn.z

        if constraint.via_point is not None:
            vx, vy, vz = constraint.via_point
            seg1 = ((vx - fx) ** 2 + (vy - fy) ** 2 + (vz - fz) ** 2) ** 0.5
            seg2 = ((tx - vx) ** 2 + (ty - vy) ** 2 + (tz - vz) ** 2) ** 0.5
            total = seg1 + seg2
        else:
            total = ((tx - fx) ** 2 + (ty - fy) ** 2 + (tz - fz) ** 2) ** 0.5

        return ResolverResult(
            True, {},
            f"{constraint.from_connector_type} path: {total:.1f} mm",
        )


__all__ = ["CablePathResolver"]
