"""Barrel hinge subsystem.

A dedicated subsystem, never integrated into the enclosure math. Exports the
hinge parts and their geometry:

* left / right hinge barrels
* hinge pin
* wire tunnel (for HDMI / USB / power cables)
* rotation stop

Dimensions from ``config/default.yaml`` (``hinge`` section). All CAD
generation is deferred; the placement/clearance data is real.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from components.base import BoundingBox, Component
from utilities.constants import DIR_NEG_X, DIR_POS_X


@dataclass(frozen=True)
class HingeParameters:
    """Parameter snapshot for a barrel hinge."""

    diameter: float
    pin: float
    wire_tunnel: float
    wall_thickness: float

    def barrel_length(self, case_depth: float, end_inset: float = 5.0) -> float:
        """Barrel length spans most of the hinge edge (mm)."""
        return case_depth - 2 * end_inset


class Hinge(Component):
    """Complete hinge subsystem: two barrels, a pin, and a wire tunnel.

    ``build()`` returns the combined hinge solid; the left and right barrels
    are offset by :meth:`barrel_offsets`.
    """

    name = "Hinge"

    def __init__(self, hinge: dict[str, Any] | None = None, wall_thickness: float = 2.5) -> None:
        data = hinge or {}
        self.diameter = float(data.get("diameter", 10.0))
        self.pin = float(data.get("pin", 3.0))
        self.wire_tunnel = float(data.get("wire_tunnel", 8.0))
        self.wall_thickness = wall_thickness

    def parameters(self) -> HingeParameters:
        return HingeParameters(
            diameter=self.diameter,
            pin=self.pin,
            wire_tunnel=self.wire_tunnel,
            wall_thickness=self.wall_thickness,
        )

    def size(self) -> BoundingBox:
        # Placeholder length; real length derives from case depth.
        return BoundingBox(self.diameter, 80.0, self.diameter)

    def barrel_offsets(self, case_depth: float) -> tuple[float, float]:
        """Return (x_left, x_right) barrel centers along the hinge axis (mm)."""
        span = self.parameters().barrel_length(case_depth)
        return (-span / 2 + self.diameter / 2, span / 2 - self.diameter / 2)

    def build(self, case_depth: float = 80.0):
        """Generate the barrel assembly: two hollow barrels along the hinge axis.

        The hinge axis runs along X through the origin. The caller translates
        the result to the case rear edge.
        """
        from utilities import cq_helpers

        cq = cq_helpers.require_cq()
        xl, xr = self.barrel_offsets(case_depth)
        # Each barrel is a short cylinder along the hinge axis near the case
        # edge; barrel_offsets spans the two ends of the hinge edge.
        barrel_len = self.diameter
        parts = []
        for cx in (xl, xr):
            barrel = cq.Workplane("XY").cylinder(radius=self.diameter / 2.0, height=barrel_len)
            barrel = barrel.rotate((0, 0, 0), (0, 1, 0), 90).translate((cx, 0, 0))
            bore = cq.Workplane("XY").cylinder(radius=self.pin / 2.0, height=barrel_len + 1.0)
            bore = bore.rotate((0, 0, 0), (0, 1, 0), 90).translate((cx, 0, 0))
            parts.append(barrel.cut(bore))
        result = parts[0]
        for part in parts[1:]:
            result = result.union(part)
        return result


class HingePin(Component):
    """The hinge pin (a cylinder)."""

    name = "Hinge Pin"

    def __init__(self, hinge: dict[str, Any] | None = None) -> None:
        data = hinge or {}
        self.pin = float(data.get("pin", 3.0))

    def size(self) -> BoundingBox:
        return BoundingBox(self.pin, 90.0, self.pin)

    def build(self, case_depth: float = 90.0):
        """Generate the hinge pin solid (axis along X)."""
        from utilities import cq_helpers

        cq = cq_helpers.require_cq()
        pin = cq.Workplane("XY").cylinder(radius=self.pin / 2.0, height=case_depth)
        return pin.rotate((0, 0, 0), (0, 1, 0), 90)


class WireTunnel(Component):
    """Cable tunnel running through the hinge axis."""

    name = "Wire Tunnel"

    def __init__(self, hinge: dict[str, Any] | None = None) -> None:
        data = hinge or {}
        self.wire_tunnel = float(data.get("wire_tunnel", 8.0))

    def size(self) -> BoundingBox:
        return BoundingBox(self.wire_tunnel, 90.0, self.wire_tunnel)

    def build(self, case_depth: float = 90.0):
        """Generate the wire tunnel solid (axis along X; a void marker)."""
        from utilities import cq_helpers

        cq = cq_helpers.require_cq()
        tunnel = cq.Workplane("XY").cylinder(radius=self.wire_tunnel / 2.0, height=case_depth)
        return tunnel.rotate((0, 0, 0), (0, 1, 0), 90)
