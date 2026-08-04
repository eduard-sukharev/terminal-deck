"""Cable routing engine.

A dedicated routing engine that tracks the HDMI, USB, and power cables and
computes minimum bend radius and clearance tunnels. Kept out of the enclosure
math so routing rules can change independently.

Outputs
-------
* minimum bend radius per route
* clearance tunnel (diameter) for the wire bundle
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from utilities.constants import (
    CONNECTOR_HDMI,
    CONNECTOR_POWER,
    CONNECTOR_USB_A,
    CONNECTOR_USB_C,
)

#: Common minimum bend radii, in mm, for the cables in this build.
#: Values are conservative manufacturer figures; measure the actual cable.
MIN_BEND_RADIUS_MM: dict[str, float] = {
    CONNECTOR_HDMI: 30.0,
    CONNECTOR_USB_C: 15.0,
    CONNECTOR_USB_A: 15.0,
    CONNECTOR_POWER: 12.0,
}

#: Outer diameter of the cable types, in mm (for tunnel sizing).
CABLE_DIAMETER_MM: dict[str, float] = {
    CONNECTOR_HDMI: 5.0,
    CONNECTOR_USB_C: 4.0,
    CONNECTOR_USB_A: 4.0,
    CONNECTOR_POWER: 3.5,
}


@dataclass(frozen=True)
class CableRoute:
    """A tracked cable route.

    Attributes
    ----------
    cable_type : str
        Connector/cable identifier (see ``utilities.constants``).
    start : tuple[float, float, float]
        Route start (mm).
    end : tuple[float, float, float]
        Route end (mm).
    bend_radius : float
        Actual bend radius used by this route (mm).
    """

    cable_type: str
    start: tuple[float, float, float]
    end: tuple[float, float, float]
    bend_radius: float

    @property
    def length(self) -> float:
        """Straight-line route length (mm)."""
        dx = self.end[0] - self.start[0]
        dy = self.end[1] - self.start[1]
        dz = self.end[2] - self.start[2]
        return math.sqrt(dx * dx + dy * dy + dz * dz)

    def passes_bend(self) -> bool:
        """True if the route bend radius meets the minimum for its cable."""
        return self.bend_radius >= MIN_BEND_RADIUS_MM.get(self.cable_type, 0.0)


class CableRouter:
    """Tracks cable routes and computes clearance requirements."""

    def __init__(self, clearance: float = 2.0) -> None:
        self.clearance = clearance
        self._routes: list[CableRoute] = []

    def track(
        self,
        cable_type: str,
        start: tuple[float, float, float],
        end: tuple[float, float, float],
        bend_radius: float | None = None,
    ) -> CableRoute:
        """Record a cable route between two points (mm).

        Parameters
        ----------
        cable_type : str
            Cable identifier; supplies the minimum bend radius.
        start, end : tuple[float, float, float]
            Route endpoints in the world frame (mm).
        bend_radius : float or None
            Actual bend radius; defaults to the minimum for the cable type.

        Returns
        -------
        CableRoute
            The recorded route.
        """
        if bend_radius is None:
            bend_radius = MIN_BEND_RADIUS_MM.get(cable_type, 5.0)
        route = CableRoute(cable_type, start, end, bend_radius)
        self._routes.append(route)
        return route

    @property
    def routes(self) -> list[CableRoute]:
        return list(self._routes)

    def tunnel_diameter(self) -> float:
        """Clearance tunnel diameter for all tracked cables (mm)."""
        bundle = max((CABLE_DIAMETER_MM.get(r.cable_type, 0.0) for r in self._routes), default=0.0)
        return bundle + 2 * self.clearance

    def failing_routes(self) -> list[CableRoute]:
        """Routes whose bend radius is below the minimum for their cable."""
        return [route for route in self._routes if not route.passes_bend()]
