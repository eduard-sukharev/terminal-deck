"""CablePath resolver: validates cable route between connectors."""

from __future__ import annotations

from typing import Any

from layouts.base import Placement
from layouts.composer import ConstraintResolver, ResolverResult
from layouts.constraints import CablePath
from routing.cable_routing import CableRouter


class CablePathResolver:
    """Validate a cable route between two connectors.

    Checks that both connectors exist, that the routed bend radius meets the
    cable type's documented minimum, and that the declared tunnel is wide
    enough for the bundle. Produces no placements.
    """

    kind = "cable_path"

    def resolve(
        self,
        constraint: CablePath,
        components: dict[str, Any],
        current: dict[str, Placement],
        config: Any,
        context: dict[str, Any],
    ) -> ResolverResult:
        from_comp = components.get(constraint.from_component)
        to_comp = components.get(constraint.to_component)
        from_placement = current.get(constraint.from_component)
        to_placement = current.get(constraint.to_component)

        if from_comp is None or to_comp is None:
            missing = (
                constraint.from_component if from_comp is None
                else constraint.to_component
            )
            return ResolverResult(False, {}, f"component {missing!r} not found")
        if from_placement is None or to_placement is None:
            unplaced = (
                constraint.from_component if from_placement is None
                else constraint.to_component
            )
            return ResolverResult(
                False, {},
                f"{unplaced!r} not placed before this cable check",
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
                False, {},
                f"{constraint.from_component} has no {constraint.from_connector_type}",
            )
        if to_conn is None:
            return ResolverResult(
                False, {},
                f"{constraint.to_component} has no {constraint.to_connector_type}",
            )

        # World-frame connector positions.
        fx = from_placement.x + from_conn.x
        fy = from_placement.y + from_conn.y
        fz = from_placement.z + from_conn.z
        tx = to_placement.x + to_conn.x
        ty = to_placement.y + to_conn.y
        tz = to_placement.z + to_conn.z

        # Route the cable through the real routing engine so the bend and
        # bundle-diameter rules come from one place rather than being
        # re-stated here.
        clearance = getattr(getattr(config, "clearance", None), "shell", 0.35)
        router = CableRouter(clearance=clearance)
        cable = constraint.from_connector_type
        if constraint.via_point is not None:
            via = tuple(constraint.via_point)
            router.track(cable, (fx, fy, fz), via, constraint.bend_radius)
            router.track(cable, via, (tx, ty, tz), constraint.bend_radius)
        else:
            router.track(cable, (fx, fy, fz), (tx, ty, tz), constraint.bend_radius)

        total = sum(route.length for route in router.routes)
        needed_diameter = router.tunnel_diameter()

        problems: list[str] = []
        if router.failing_routes():
            problems.append(
                f"bend radius {constraint.bend_radius:.1f} mm is tighter than "
                f"{cable} allows"
            )
        if constraint.clearance_diameter < needed_diameter:
            problems.append(
                f"tunnel {constraint.clearance_diameter:.1f} mm is narrower than "
                f"the {needed_diameter:.1f} mm the bundle needs"
            )

        if problems:
            return ResolverResult(
                False, {},
                f"{cable} path {total:.1f} mm — " + "; ".join(problems),
            )
        return ResolverResult(
            True, {},
            f"{cable} path: {total:.1f} mm, bend {constraint.bend_radius:.1f} mm, "
            f"tunnel >= {needed_diameter:.1f} mm",
        )


__all__ = ["CablePathResolver"]
