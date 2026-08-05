"""PortAccess resolver: checks an external connector reaches its shell wall."""

from __future__ import annotations

import math
from typing import Any

from layouts.base import Placement
from layouts.composer import ConstraintResolver, ResolverResult
from layouts.constraints import PortAccess
from layouts.resolvers._helpers import estimate_enclosure

# Wall name for each dominant direction, in world axes.
_WALL_FOR_DIRECTION = {
    (1, 0): "right",
    (-1, 0): "left",
    (0, 1): "front",
    (0, -1): "rear",
}


class PortAccessResolver:
    """Verify an external connector ends up within reach of the wall it faces.

    Mirrors the reach test in
    :meth:`assemblies.assembly.Assembly.connector_cutouts`: a connector whose
    opening sits further from the wall than the component's own half-depth
    plus shell clearance and wall thickness gets no cutout there. That pass
    drops such connectors silently, so without this constraint a layout can
    bury every port and still report a clean build.

    Produces no placements.
    """

    kind = "port_access"

    def resolve(
        self,
        constraint: PortAccess,
        components: dict[str, Any],
        current: dict[str, Placement],
        config: Any,
        context: dict[str, Any],
    ) -> ResolverResult:
        subj = components.get(constraint.subject)
        placement = current.get(constraint.subject)
        if subj is None:
            return ResolverResult(
                False, {}, f"component {constraint.subject!r} not found",
            )
        if placement is None:
            return ResolverResult(
                False, {},
                f"{constraint.subject!r} not placed before this port check",
            )

        connector = next(
            (c for c in subj.connectors() if c.type == constraint.connector_type),
            None,
        )
        if connector is None:
            return ResolverResult(
                False, {},
                f"{constraint.subject} has no {constraint.connector_type} connector",
            )
        if connector.internal:
            return ResolverResult(
                False, {},
                f"{constraint.subject} {constraint.connector_type} is marked "
                "internal — it will never get a shell cutout",
            )

        wall_w, wall_d, _ = estimate_enclosure(
            current, components, config, context=context
        )
        wall = getattr(config, "wall_thickness", 2.0)
        clearance = getattr(getattr(config, "clearance", None), "shell", 0.35)

        rad = math.radians(placement.rotation)
        cos_r, sin_r = math.cos(rad), math.sin(rad)
        wx = connector.direction[0] * cos_r - connector.direction[1] * sin_r
        wy = connector.direction[0] * sin_r + connector.direction[1] * cos_r
        px = placement.x + connector.x * cos_r - connector.y * sin_r
        py = placement.y + connector.x * sin_r + connector.y * cos_r

        box = subj.size()
        if abs(wx) >= abs(wy):
            facing = (1, 0) if wx > 0.0 else (-1, 0)
            distance = (wall_w / 2 - px) if wx > 0.0 else (px + wall_w / 2)
            reach = box.width / 2 + clearance + wall
        else:
            facing = (0, 1) if wy > 0.0 else (0, -1)
            distance = (wall_d / 2 - py) if wy > 0.0 else (py + wall_d / 2)
            reach = box.depth / 2 + clearance + wall

        faced_wall = _WALL_FOR_DIRECTION[facing]
        budget = constraint.max_inset if constraint.max_inset is not None else reach

        if constraint.wall is not None and constraint.wall != faced_wall:
            return ResolverResult(
                False, {},
                f"{constraint.subject} {constraint.connector_type} faces the "
                f"{faced_wall} wall, expected {constraint.wall}",
            )
        if distance > budget:
            return ResolverResult(
                False, {},
                f"{constraint.subject} {constraint.connector_type} is "
                f"{distance:.1f} mm from the {faced_wall} wall (max {budget:.1f}) "
                "— no cutout would be generated",
            )
        return ResolverResult(
            True, {},
            f"{constraint.subject} {constraint.connector_type} reaches the "
            f"{faced_wall} wall ({distance:.1f} mm <= {budget:.1f})",
        )


__all__ = ["PortAccessResolver"]
