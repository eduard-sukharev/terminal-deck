"""P6-style three-knuckle hinge subsystem.

A dedicated subsystem, never integrated into the enclosure math. Along the
hinge axis (X) it is, left to right::

    [cap][ Lid knuckle ] gap [   Base knuckle   ] gap [ Lid knuckle ][cap]
                              land | tunnel | land

* two Lid knuckles at the corners
* one long Base knuckle in the middle; between its two solid pin lands it is
  a hollow tube — the display cable tunnel (``wire_tunnel``)
* two pins, one per side, each running from a service cap through a Lid
  knuckle into the adjacent Base land
* two removable service caps closing the pin ends

Dimensions from ``config/default.yaml`` (``hinge`` section). The hinge axis
runs along X through the origin; the caller translates the result to the case
rear edge.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from components.base import BoundingBox, Component

#: How far a notch or bore runs past the case side, so the cut exits cleanly (mm).
SIDE_OVERRUN = 1.0


@dataclass(frozen=True)
class HingeParameters:
    """Parameter snapshot for the hinge."""

    diameter: float
    pin: float
    wire_tunnel: float
    wall_thickness: float
    lid_knuckle: float
    knuckle_gap: float
    pin_land: float
    pin_clearance: float
    cap_thickness: float
    cap_plug: float
    end_inset: float


class Hinge(Component):
    """Complete hinge: Lid knuckles, Base knuckle, pins, service caps.

    ``build()`` returns the combined hinge solid; the individual parts come
    from ``build_lid_knuckles()``, ``build_base_knuckle()``, ``build_pins()``
    and ``build_caps()``.
    """

    name = "Hinge"

    def __init__(self, hinge: dict[str, Any] | None = None, wall_thickness: float = 2.5) -> None:
        data = hinge or {}
        self.diameter = float(data.get("diameter", 13.0))
        self.pin = float(data.get("pin", 3.0))
        self.wire_tunnel = float(data.get("wire_tunnel", 8.0))
        self.lid_knuckle = float(data.get("lid_knuckle", 20.0))
        self.knuckle_gap = float(data.get("knuckle_gap", 0.5))
        self.pin_land = float(data.get("pin_land", 8.0))
        self.pin_clearance = float(data.get("pin_clearance", 0.2))
        self.cap_thickness = float(data.get("cap_thickness", 2.0))
        self.cap_plug = float(data.get("cap_plug", 4.0))
        self.end_inset = float(data.get("end_inset", 5.0))
        self.wall_thickness = wall_thickness
        tunnel_wall = (self.diameter - self.wire_tunnel) / 2.0
        if tunnel_wall < wall_thickness:
            raise ValueError(
                f"hinge.diameter {self.diameter} leaves a {tunnel_wall:.2f} mm wall around the "
                f"{self.wire_tunnel} mm cable tunnel; need >= wall.thickness {wall_thickness}"
            )

    def parameters(self) -> HingeParameters:
        return HingeParameters(
            diameter=self.diameter,
            pin=self.pin,
            wire_tunnel=self.wire_tunnel,
            wall_thickness=self.wall_thickness,
            lid_knuckle=self.lid_knuckle,
            knuckle_gap=self.knuckle_gap,
            pin_land=self.pin_land,
            pin_clearance=self.pin_clearance,
            cap_thickness=self.cap_thickness,
            cap_plug=self.cap_plug,
            end_inset=self.end_inset,
        )

    # -- layout along the hinge axis (all X, centered on 0) -------------------

    def span(self, case_width: float) -> float:
        """Knuckle span: the case width less the end inset on both sides (mm)."""
        return case_width - 2 * self.end_inset

    def base_knuckle_span(self, case_width: float) -> tuple[float, float]:
        """(x_min, x_max) of the Base knuckle (mm)."""
        half = self.span(case_width) / 2.0
        edge = half - self.lid_knuckle - self.knuckle_gap
        return (-edge, edge)

    def lid_knuckle_spans(self, case_width: float) -> tuple[tuple[float, float], tuple[float, float]]:
        """((x_min, x_max) left, (x_min, x_max) right) of the Lid knuckles (mm)."""
        half = self.span(case_width) / 2.0
        return ((-half, -half + self.lid_knuckle), (half - self.lid_knuckle, half))

    def tunnel_span(self, case_width: float) -> tuple[float, float]:
        """(x_min, x_max) of the open cable tunnel inside the Base knuckle (mm)."""
        lo, hi = self.base_knuckle_span(case_width)
        return (lo + self.pin_land, hi - self.pin_land)

    def pin_length(self) -> float:
        """One pin: the Lid knuckle less the cap plug, plus the gap and the Base land."""
        return self.lid_knuckle - self.cap_plug + self.knuckle_gap + self.pin_land

    def size(self) -> BoundingBox:
        # Placeholder length; real length derives from case width.
        return BoundingBox(80.0, self.diameter, self.diameter)

    # -- geometry --------------------------------------------------------------

    def _x_cylinder(self, diameter: float, x0: float, x1: float):
        """Cylinder along X from ``x0`` to ``x1`` on the hinge axis."""
        from utilities import cad_helpers

        body = cad_helpers.rotate_y(cad_helpers.cylinder_centered(diameter, x1 - x0), 90)
        return cad_helpers.translate(body, (x0 + x1) / 2.0, 0, 0)

    def _knuckle(self, x0: float, x1: float):
        """A knuckle tube with the pin bore through it."""
        from utilities import cad_helpers

        tube = self._x_cylinder(self.diameter, x0, x1)
        bore = self._x_cylinder(self.pin + self.pin_clearance, x0 - 1.0, x1 + 1.0)
        return cad_helpers.cut(tube, bore)

    def build_lid_knuckles(self, case_width: float = 80.0):
        """The two Lid corner knuckles, as one two-solid shape."""
        from utilities import cad_helpers

        left, right = self.lid_knuckle_spans(case_width)
        return cad_helpers.union(self._knuckle(*left), self._knuckle(*right))

    def build_base_knuckle(self, case_width: float = 80.0):
        """The long Base knuckle: pin lands at both ends, cable tunnel between."""
        from utilities import cad_helpers

        lo, hi = self.base_knuckle_span(case_width)
        knuckle = self._knuckle(lo, hi)
        t0, t1 = self.tunnel_span(case_width)
        return cad_helpers.cut(knuckle, self._x_cylinder(self.wire_tunnel, t0, t1))

    def build_pins(self, case_width: float = 80.0):
        """The two pins, each from behind its cap plug through the Lid knuckle into the Base land."""
        from utilities import cad_helpers

        half = self.span(case_width) / 2.0
        length = self.pin_length()
        return cad_helpers.union(
            self._x_cylinder(self.pin, -half + self.cap_plug, -half + self.cap_plug + length),
            self._x_cylinder(self.pin, half - self.cap_plug - length, half - self.cap_plug),
        )

    def build_caps(self, case_width: float = 80.0):
        """The two removable service caps: a head outside each end, a plug in the bore."""
        from utilities import cad_helpers

        half = self.span(case_width) / 2.0
        plug = self.pin
        caps = []
        for sign in (-1.0, 1.0):
            head = self._x_cylinder(self.diameter, 0.0, self.cap_thickness)
            stem = self._x_cylinder(plug, -self.cap_plug, 0.0)
            cap = cad_helpers.union(head, stem)
            if sign < 0:
                cap = cad_helpers.rotate_z(cap, 180)
            caps.append(cad_helpers.translate(cap, sign * half, 0, 0))
        return cad_helpers.union(*caps)

    # -- mounting into the shells ---------------------------------------------
    #
    # The knuckles are printed with the shells (Base knuckle on the Deck, Lid
    # knuckles on the Lid shell); only the pins and caps are separate. Each
    # shell is notched where the other shell's knuckle sits, and the bores
    # are re-cut through the fused result. All of it is axis-at-origin along
    # X, like the knuckles; the caller places it on the hinge axis.

    @property
    def notch_radius(self) -> float:
        """Radius of the clearance notch around a knuckle (mm): knuckle plus the gap."""
        return self.diameter / 2.0 + self.knuckle_gap

    def corner_notch_spans(self, case_width: float) -> tuple[tuple[float, float], tuple[float, float]]:
        """((x_min, x_max) left, right) Base notches over the Lid knuckles (mm).

        Run from past the case side, so the service cap stays reachable, to the
        Base knuckle."""
        lo, hi = self.base_knuckle_span(case_width)
        out = case_width / 2.0 + SIDE_OVERRUN
        return ((-out, lo), (hi, out))

    def middle_notch_span(self, case_width: float) -> tuple[float, float]:
        """(x_min, x_max) of the Lid notch over the Base knuckle (mm)."""
        lo, hi = self.base_knuckle_span(case_width)
        return (lo - self.knuckle_gap / 2.0, hi + self.knuckle_gap / 2.0)

    def build_base_notches(self, case_width: float = 80.0):
        """Voids to cut from the Tray and Deck where the Lid knuckles swing."""
        from utilities import cad_helpers

        left, right = self.corner_notch_spans(case_width)
        return cad_helpers.union(
            self._x_cylinder(2 * self.notch_radius, *left),
            self._x_cylinder(2 * self.notch_radius, *right),
        )

    def build_lid_notch(self, case_width: float = 80.0):
        """Void to cut from the Lid shell where the Base knuckle swings."""
        return self._x_cylinder(2 * self.notch_radius, *self.middle_notch_span(case_width))

    def build_base_bores(self, case_width: float = 80.0):
        """Voids to re-cut after the Base knuckle is fused: pin bore and cable tunnel.

        The tunnel opens into the Deck, which is what lets the cable reach the Base interior."""
        from utilities import cad_helpers

        lo, hi = self.base_knuckle_span(case_width)
        t0, t1 = self.tunnel_span(case_width)
        return cad_helpers.union(
            self._x_cylinder(self.pin + self.pin_clearance, lo, hi),
            self._x_cylinder(self.wire_tunnel, t0, t1),
        )

    def build_lid_bores(self, case_width: float = 80.0):
        """Voids to re-cut after the Lid knuckles are fused: pin bore out to the case side."""
        from utilities import cad_helpers

        (l0, l1), (r0, r1) = self.lid_knuckle_spans(case_width)
        out = case_width / 2.0 + SIDE_OVERRUN
        bore = self.pin + self.pin_clearance
        return cad_helpers.union(
            self._x_cylinder(bore, -out, l1), self._x_cylinder(bore, r0, out)
        )

    def build_hardware(self, case_width: float = 80.0):
        """The separately printed or bought hinge parts: pins and service caps."""
        from utilities import cad_helpers

        return cad_helpers.union(self.build_pins(case_width), self.build_caps(case_width))

    def build(self, case_depth: float = 80.0):
        """The combined hinge solid for ``case_depth`` (the case width along X)."""
        from utilities import cad_helpers

        return cad_helpers.union(
            self.build_lid_knuckles(case_depth),
            self.build_base_knuckle(case_depth),
            self.build_pins(case_depth),
            self.build_caps(case_depth),
        )


class HingePin(Component):
    """A hinge pin (a cylinder)."""

    name = "Hinge Pin"

    def __init__(self, hinge: dict[str, Any] | None = None) -> None:
        data = hinge or {}
        self.pin = float(data.get("pin", 3.0))

    def size(self) -> BoundingBox:
        return BoundingBox(90.0, self.pin, self.pin)

    def build(self, case_depth: float = 90.0):
        """Generate a hinge pin solid (axis along X)."""
        from utilities import cad_helpers

        pin = cad_helpers.cylinder_centered(self.pin, case_depth)
        return cad_helpers.rotate_y(pin, 90)


class WireTunnel(Component):
    """Cable tunnel running through the Base knuckle."""

    name = "Wire Tunnel"

    def __init__(self, hinge: dict[str, Any] | None = None) -> None:
        data = hinge or {}
        self.wire_tunnel = float(data.get("wire_tunnel", 8.0))

    def size(self) -> BoundingBox:
        return BoundingBox(90.0, self.wire_tunnel, self.wire_tunnel)

    def build(self, case_depth: float = 90.0):
        """Generate the wire tunnel solid (axis along X; a void marker)."""
        from utilities import cad_helpers

        tunnel = cad_helpers.cylinder_centered(self.wire_tunnel, case_depth)
        return cad_helpers.rotate_y(tunnel, 90)
