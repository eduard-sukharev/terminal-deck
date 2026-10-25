"""Printed friction hinge (ADR 0004, 0005): P6-style layout, separate Base knuckle.

A dedicated subsystem, never integrated into the enclosure math. Along the
hinge axis (X) it is, left to right::

    [cheek][g][ Lid knuckle ][g][     Base knuckle     ][g][ Lid knuckle ][g][cheek]
                                  land | tunnel | land

* two Lid corner knuckles, fused to the Lid shell's side Sections
* one long Base knuckle in the middle: a D-profile bar whose flat faces the
  case interior; between its two bolt lands it is hollow, the display cable
  tunnel (``wire_tunnel``), which opens into the case through the flat
* the Base knuckle is its own printed part (:meth:`Hinge.build_base_part`),
  seated in a pocket in the Deck's rear edge (:meth:`Hinge.build_base_notches`)
  with its flat against the Deck's saddle blocks (ADR 0005)
* two outer end cheeks (:meth:`Hinge.build_cheeks`), fused to the Deck, one per
  Deck Section
* per side, an M3 friction bolt: head in a recess in the cheek's outer face
  under a removable service cap, through the cheek, a washer stack, the Lid
  knuckle, a second stack and the Base land into a captive nyloc nut in a hex
  pocket opening into the tunnel. Head and nut are both on the stationary Base
  side, so opening the Lid never walks the nut; tightening the bolt sets the
  friction.

Dimensions from ``config/default.yaml`` (``hinge`` section). Geometry is built
on the hinge axis along X through the origin, ``+Y`` toward the case interior
and the case's rear outer face at ``y = 0``; the caller translates the result
onto the case rear edge at the hinge axis height.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from components.base import BoundingBox, Component
from utilities import fasteners



@dataclass(frozen=True)
class HingeParameters:
    """Parameter snapshot for the hinge."""

    diameter: float
    wire_tunnel: float
    wall_thickness: float
    lid_knuckle: float
    washer_stack: float
    land: float
    end_cheek: float
    saddle: float
    fit: float
    cap_thickness: float
    cap_plug: float
    end_inset: float
    friction_bolt: str
    swing_clearance: float
    side_overrun: float
    head_recess_margin: float
    cap_margin: float


class Hinge(Component):
    """Complete hinge: Lid knuckles, Base knuckle part, bolts and service caps."""

    name = "Hinge"

    def __init__(self, hinge: dict[str, Any] | None = None, wall_thickness: float = 2.5) -> None:
        data = hinge or {}
        self.diameter = float(data.get("diameter", 13.0))
        self.wire_tunnel = float(data.get("wire_tunnel", 8.0))
        self.lid_knuckle = float(data.get("lid_knuckle", 20.0))
        self.washer_stack = float(data.get("washer_stack", 1.2))
        self.land = float(data.get("land", 8.0))
        self.end_cheek = float(data.get("end_cheek", 5.0))
        self.saddle = float(data.get("saddle", 6.0))
        self.fit = float(data.get("fit", 0.2))
        self.cap_thickness = float(data.get("cap_thickness", 2.0))
        self.cap_plug = float(data.get("cap_plug", 4.0))
        self.end_inset = float(data.get("end_inset", 9.0))
        self.friction_bolt = str(data.get("friction_bolt", "M3"))
        self.swing_clearance = float(data.get("swing_clearance", 0.5))
        self.side_overrun = float(data.get("side_overrun", 1.0))
        self.head_recess_margin = float(data.get("head_recess_margin", 0.5))
        self.cap_margin = float(data.get("cap_margin", 2.0))
        self.wall_thickness = wall_thickness
        tunnel_wall = (self.diameter - self.wire_tunnel) / 2.0
        if tunnel_wall < wall_thickness:
            raise ValueError(
                f"hinge.diameter {self.diameter} leaves a {tunnel_wall:.2f} mm wall around the "
                f"{self.wire_tunnel} mm cable tunnel; need >= wall.thickness {wall_thickness}"
            )
        bolt = fasteners.screw(self.friction_bolt)
        if self.diameter < bolt.head_diameter + 2 * wall_thickness:
            raise ValueError(
                f"hinge.diameter {self.diameter} cannot hold a {bolt.head_diameter} mm "
                f"{self.friction_bolt} head recess with a wall of {wall_thickness} mm"
            )

    def parameters(self) -> HingeParameters:
        return HingeParameters(
            diameter=self.diameter, wire_tunnel=self.wire_tunnel,
            wall_thickness=self.wall_thickness, lid_knuckle=self.lid_knuckle,
            washer_stack=self.washer_stack, land=self.land, end_cheek=self.end_cheek,
            saddle=self.saddle, fit=self.fit,
            cap_thickness=self.cap_thickness, cap_plug=self.cap_plug,
            end_inset=self.end_inset, friction_bolt=self.friction_bolt,
            swing_clearance=self.swing_clearance, side_overrun=self.side_overrun,
            head_recess_margin=self.head_recess_margin, cap_margin=self.cap_margin,
        )

    # -- layout along the hinge axis (all X, centered on 0) -------------------

    @property
    def radius(self) -> float:
        return self.diameter / 2.0

    def span(self, case_width: float) -> float:
        """Hinge span: the case width less the end inset on both sides (mm)."""
        return case_width - 2 * self.end_inset

    def cheek_spans(self, case_width: float) -> tuple[tuple[float, float], tuple[float, float]]:
        """((x_min, x_max) left, right) of the outer Base end cheeks (mm)."""
        half = self.span(case_width) / 2.0
        return ((-half, -half + self.end_cheek), (half - self.end_cheek, half))

    def lid_knuckle_spans(self, case_width: float) -> tuple[tuple[float, float], tuple[float, float]]:
        """((x_min, x_max) left, (x_min, x_max) right) of the Lid knuckles (mm)."""
        half = self.span(case_width) / 2.0
        a = -half + self.end_cheek + self.washer_stack
        return ((a, a + self.lid_knuckle), (-a - self.lid_knuckle, -a))

    def base_knuckle_span(self, case_width: float) -> tuple[float, float]:
        """(x_min, x_max) of the Base knuckle bar (mm), a washer stack inside each Lid knuckle."""
        (_, l1), (r0, _) = self.lid_knuckle_spans(case_width)
        return (l1 + self.washer_stack, r0 - self.washer_stack)

    def tunnel_span(self, case_width: float) -> tuple[float, float]:
        """(x_min, x_max) of the open cable tunnel inside the Base knuckle (mm)."""
        lo, hi = self.base_knuckle_span(case_width)
        return (lo + self.land, hi - self.land)

    def land_spans(self, case_width: float) -> tuple[tuple[float, float], tuple[float, float]]:
        """((x_min, x_max) left, right) of the Base knuckle's solid bolt lands (mm):
        where the Deck's saddle blocks back the bar."""
        b0, b1 = self.base_knuckle_span(case_width)
        t0, t1 = self.tunnel_span(case_width)
        return ((b0, t0), (t1, b1))

    def bolt_length(self) -> int:
        """Stock length of the friction bolt (mm).

        From the head seat in the cheek recess to the far end of the nut: the
        cheek less the recess, two washer stacks, the Lid knuckle and the Base
        land, whose inner nut_height holds the nut.
        """
        fasteners.screw(self.friction_bolt)
        run = (
            self.end_cheek - self.head_recess_depth() + 2 * self.washer_stack
            + self.lid_knuckle + self.land
        )
        fitting = [n for n in fasteners.STANDARD_LENGTHS[self.friction_bolt] if n <= run + 1e-9]
        if not fitting:
            raise ValueError(f"no stock {self.friction_bolt} bolt fits a {run:g} mm run")
        return max(fitting)

    def head_recess_depth(self) -> float:
        """Depth of the bolt-head recess in the cheek's outer face (mm)."""
        return fasteners.screw(self.friction_bolt).head_depth + self.head_recess_margin

    def size(self) -> BoundingBox:
        # Placeholder length; real length derives from case width.
        return BoundingBox(80.0, self.diameter, self.diameter)

    # -- geometry --------------------------------------------------------------

    def _x_cylinder(self, diameter: float, x0: float, x1: float):
        """Cylinder along X from ``x0`` to ``x1`` on the hinge axis."""
        from utilities import cad_helpers

        body = cad_helpers.rotate_y(cad_helpers.cylinder_centered(diameter, x1 - x0), 90)
        return cad_helpers.translate(body, (x0 + x1) / 2.0, 0, 0)

    def _d_bar(self, x0: float, x1: float, grow: float = 0.0):
        """A D-profile bar: the knuckle circle trimmed flat at the wall's inner face.

        ``grow`` inflates the round and moves the flat inward by that much (the
        pocket a bar sits in)."""
        from utilities import cad_helpers

        tube = self._x_cylinder(self.diameter + 2 * grow, x0, x1)
        reach = self.radius + grow + 1.0
        flat = self.wall_thickness + grow
        keep = cad_helpers.translate(
            cad_helpers.box_centered(x1 - x0 + 2.0, reach + flat, self.diameter + 2 * grow + 2.0),
            (x0 + x1) / 2.0, (flat - reach) / 2.0, 0.0,
        )
        return cad_helpers.intersect(tube, keep)

    def _box(self, x0: float, x1: float, y0: float, y1: float, z0: float, z1: float):
        from utilities import cad_helpers

        return cad_helpers.translate(
            cad_helpers.box_centered(x1 - x0, y1 - y0, z1 - z0),
            (x0 + x1) / 2.0, (y0 + y1) / 2.0, (z0 + z1) / 2.0,
        )

    def build_lid_knuckles(self, case_width: float = 80.0):
        """The two Lid corner knuckles, with the bolt's clearance bore through each."""
        from utilities import cad_helpers

        bolt = fasteners.screw(self.friction_bolt)
        out = []
        for x0, x1 in self.lid_knuckle_spans(case_width):
            tube = self._x_cylinder(self.diameter, x0, x1)
            out.append(cad_helpers.cut(tube, self._x_cylinder(bolt.clearance, x0 - 1.0, x1 + 1.0)))
        return cad_helpers.union(*out)

    def build_base_part(self, case_width: float = 80.0):
        """The Base knuckle: a D-bar with the cable tunnel between its two lands.

        Each land is bored for the friction bolt, with a captive nyloc nut
        pocket opening into the tunnel. Seated in the Deck's pocket, flat
        against the saddle blocks (ADR 0005). Prints flat face down.
        """
        from utilities import cad_helpers

        bolt = fasteners.screw(self.friction_bolt)
        nut = fasteners.nut_trap(self.friction_bolt)
        b0, b1 = self.base_knuckle_span(case_width)
        t0, t1 = self.tunnel_span(case_width)
        cuts = [self._x_cylinder(self.wire_tunnel, t0, t1)]
        for side, (outer, land_inner) in zip((-1.0, 1.0), ((b0, t0), (b1, t1))):
            lo, hi = sorted((outer - side * 1.0, land_inner))
            cuts.append(self._x_cylinder(bolt.clearance, lo, hi))
            pocket = self._hex_prism(nut.across_flats + nut.clearance, nut.height + 0.2)
            cx = land_inner - side * (nut.height + 0.2) / 2.0 + side * 0.1
            cuts.append(self._translated_x(pocket, cx))
        return cad_helpers.cut(self._d_bar(b0, b1), *cuts)

    def build_cheeks(self, case_width: float = 80.0):
        """The two end cheeks, solid: the Deck fuses them on, then re-cuts
        :meth:`build_cheek_bores`."""
        from utilities import cad_helpers

        return cad_helpers.union(*[self._d_bar(*c) for c in self.cheek_spans(case_width)])

    def build_cheek_bores(self, case_width: float = 80.0):
        """Bolt bore through each cheek and the head recess in its outer face."""
        from utilities import cad_helpers

        bolt = fasteners.screw(self.friction_bolt)
        recess = self.head_recess_depth()
        cb = max(bolt.head_diameter, fasteners.washer(self.friction_bolt).diameter) + 0.4
        cuts = []
        for side, (c0, c1) in zip((-1.0, 1.0), self.cheek_spans(case_width)):
            outer, inner = (c0, c1) if side < 0 else (c1, c0)
            lo, hi = sorted((outer + side * 1.0, inner - side * 1.0))
            cuts.append(self._x_cylinder(bolt.clearance, lo, hi))
            lo, hi = sorted((outer + side * 1.0, outer - side * recess))
            cuts.append(self._x_cylinder(cb, lo, hi))
        return cad_helpers.union(*cuts)

    def _z_cylinder(self, diameter: float, x: float, y: float, z0: float, z1: float):
        from utilities import cad_helpers

        return cad_helpers.translate(
            cad_helpers.cylinder_centered(diameter, z1 - z0), x, y, (z0 + z1) / 2.0
        )

    def _y_cylinder(self, diameter: float, x: float, z: float, y0: float, y1: float):
        from utilities import cad_helpers

        body = cad_helpers.rotate_x(cad_helpers.cylinder_centered(diameter, y1 - y0), 90)
        return cad_helpers.translate(body, x, (y0 + y1) / 2.0, z)

    def _hex_prism(self, across_flats: float, length: float):
        """A hexagonal prism along X, flats up and down."""
        from utilities import cad_helpers

        circ = across_flats / math.cos(math.radians(30))
        pts = [
            (circ / 2 * math.cos(math.radians(60 * i)), circ / 2 * math.sin(math.radians(60 * i)))
            for i in range(6)
        ]
        return cad_helpers.rotate_z(cad_helpers.rotate_y(cad_helpers.extrude_polygon(pts, length), 90), 0)

    def _translated_x(self, shape, x: float):
        from utilities import cad_helpers

        return cad_helpers.translate(shape, x, 0.0, 0.0)

    # -- mounting into the shells ---------------------------------------------
    #
    # The Lid knuckles are printed with the Lid shell's side Sections; the Base
    # knuckle part is separate (ADR 0004). The Deck is notched where the Base
    # bar and cheeks sit and where the Lid knuckles swing, the Lid shell where
    # the bar and cheeks swing. All axis-at-origin along X, like the knuckles.

    @property
    def notch_radius(self) -> float:
        """Radius of the clearance notch around a knuckle (mm): knuckle plus the swing clearance."""
        return self.radius + self.swing_clearance

    def corner_notch_spans(self, case_width: float) -> tuple[tuple[float, float], ...]:
        """(x_min, x_max) Deck notches around the fused end cheeks (mm).

        Per side: the Lid knuckle's swing, from its own washer stack out to the
        cheek, and the service cap's room, from the cheek past the case side.
        The cheek itself stays Deck."""
        (l0, l1), (r0, r1) = self.lid_knuckle_spans(case_width)
        (c0, c1), (d0, d1) = self.cheek_spans(case_width)
        out = case_width / 2.0 + self.side_overrun
        return (
            (-out, c0), (c1, l1 + self.washer_stack / 2.0),
            (r0 - self.washer_stack / 2.0, d0), (d1, out),
        )

    def lid_notch_spans(self, case_width: float) -> tuple[tuple[float, float], ...]:
        """(x_min, x_max) ranges of the Lid shell notched for the Base bar and cheeks (mm)."""
        b0, b1 = self.base_knuckle_span(case_width)
        (c0, c1), (d0, d1) = self.cheek_spans(case_width)
        gap = self.washer_stack / 2.0
        out = case_width / 2.0 + self.side_overrun
        return ((-out, c1 + gap), (b0 - gap, b1 + gap), (d0 - gap, out))

    def build_base_notches(self, case_width: float = 80.0):
        """Voids to cut from the Deck: the pocket the Base knuckle sits in (with
        ``fit`` all round, washer stacks included), and the notches where the
        Lid knuckles swing and the service caps sit."""
        from utilities import cad_helpers

        b0, b1 = self.base_knuckle_span(case_width)
        pocket = self._d_bar(b0 - self.washer_stack / 2.0, b1 + self.washer_stack / 2.0, grow=self.fit)
        swing = [self._x_cylinder(2 * self.notch_radius, *s) for s in self.corner_notch_spans(case_width)]
        return cad_helpers.union(pocket, *swing)

    def build_lid_notch(self, case_width: float = 80.0):
        """Void to cut from the Lid shell where the Base bar and cheeks swing."""
        from utilities import cad_helpers

        spans = self.lid_notch_spans(case_width)
        return cad_helpers.union(*[self._x_cylinder(2 * self.notch_radius, *s) for s in spans])

    def build_lid_bores(self, case_width: float = 80.0):
        """Voids to re-cut after the Lid knuckles are fused: the bolt bore through each."""
        from utilities import cad_helpers

        bolt = fasteners.screw(self.friction_bolt)
        return cad_helpers.union(
            *[self._x_cylinder(bolt.clearance, x0 - 1.0, x1 + 1.0) for x0, x1 in self.lid_knuckle_spans(case_width)]
        )

    def build_lid_roll(self, case_width: float = 80.0):
        """The Lid's rolled rear edge: a full-width barrel on the hinge axis.

        The caller keeps the Lid half of it and cuts the notches, so the closed
        rear reads as one round roll with the Base knuckle in it."""
        return self._x_cylinder(self.diameter, -case_width / 2.0, case_width / 2.0)

    def build_hardware(self, case_width: float = 80.0):
        """Bought and separately printed small parts: bolts, nuts, washers, service caps."""
        from utilities import cad_helpers

        bolt = fasteners.screw(self.friction_bolt)
        nut = fasteners.nut_trap(self.friction_bolt)
        washer = fasteners.washer(self.friction_bolt)
        recess = self.head_recess_depth()
        cheeks = self.cheek_spans(case_width)
        t0, t1 = self.tunnel_span(case_width)
        parts = []
        for side, (c0, c1) in zip((-1.0, 1.0), cheeks):
            outer = c0 if side < 0 else c1
            seat = outer - side * recess
            tunnel_end = t0 if side < 0 else t1
            tip = tunnel_end - side * 0.1
            lo, hi = sorted((seat, tip))
            parts.append(self._x_cylinder(bolt.clearance - 0.2, lo, hi))
            lo, hi = sorted((seat, seat + side * bolt.head_depth))
            parts.append(self._x_cylinder(bolt.head_diameter, lo, hi))
            lo, hi = sorted((tunnel_end, tunnel_end - side * nut.height))
            parts.append(self._translated_x(self._hex_prism(nut.across_flats, nut.height), (lo + hi) / 2.0))
            # Washer stacks on both faces of the Lid knuckle.
            for edge in (c1 if side < 0 else c0, tunnel_end - side * self.land):
                lo, hi = sorted((edge, edge + side * self.washer_stack))
                parts.append(self._x_cylinder(washer.diameter, lo, hi))
            # Service cap: a head over the recess and a plug into it.
            lo, hi = sorted((outer, outer + side * self.cap_thickness))
            parts.append(self._x_cylinder(self.diameter - self.cap_margin, lo, hi))
            lo, hi = sorted((outer, outer - side * min(self.cap_plug, recess)))
            parts.append(self._x_cylinder(bolt.head_diameter + 0.2, lo, hi))
        return cad_helpers.union(*parts)

    def build(self, case_depth: float = 80.0):
        """The combined separate hinge parts for ``case_depth`` (the case width
        along X): Lid knuckles, Base knuckle and hardware. The end cheeks belong
        to the Deck."""
        from utilities import cad_helpers

        return cad_helpers.union(
            self.build_lid_knuckles(case_depth),
            self.build_base_part(case_depth),
            self.build_hardware(case_depth),
        )


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
