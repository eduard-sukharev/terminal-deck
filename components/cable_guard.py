"""Cable guard (ADR 0007): the display cable's one turn around the Hinge axis.

A load-free printed sleeve on the Hinge axis, facing the driver's HDMI
connector. Radially, from the axis out:

    core | coil (one FPC turn + fit) | Deck ring | fit | Lid ring

and along X:

    [Deck disc][fit][        Lid ring span (FPC + fit)        ][fit][Deck disc]

The core, the Deck ring and the two end discs are one piece with the Deck,
held by an arm from each disc to the Deck's rear face. The Lid ring sits
between the discs and turns with the Lid, held by a web to the Lid's rear
face. The cable enters from the Base just below the axis and from the Lid
just above it (in the Lid's own turning frame), each through an entry
``entry_angle`` wide; neither ring may ever cover an entry through the whole
``travel``, which fixes each ring's sector.

Angles are polar, measured from +Y (toward the case interior) toward +Z, in
the hinge frame: the Hinge axis along X through the origin, the case rear
face at ``y = setback``. Opening the Lid by ``theta`` turns a Lid point's
angle by ``+theta``.
"""

from __future__ import annotations

import math
from typing import Any

#: Angular step of the polygonal arcs (deg); fine enough for a printed cover.
ARC_STEP = 5.0


class CableGuard:
    """The core, rings and discs of the display cable's turn on the Hinge axis."""

    def __init__(self, cfg: Any, wall_thickness: float, x: float, travel: float) -> None:
        self.fpc_width = float(cfg.fpc_width)
        self.fpc_thickness = float(cfg.fpc_thickness)
        self.turns = int(cfg.turns)
        self.fit = float(cfg.fit)
        self.entry_angle = float(cfg.entry_angle)
        self.core_radius = float(cfg.min_bend_radius)
        self.wall_thickness = wall_thickness
        self.x = x
        self.travel = travel
        if not 0.0 < self.entry_angle < 90.0:
            raise ValueError(f"cable guard: entry_angle {self.entry_angle:g} must lie between 0 and 90 deg")
        if self.lid_sector()[1] <= self.lid_sector()[0]:
            raise ValueError(
                f"cable guard: a {travel:g} deg travel with {self.entry_angle:g} deg entries "
                "leaves no room for the Lid ring"
            )
        if self.deck_sector()[1] <= self.deck_sector()[0]:
            raise ValueError(
                f"cable guard: a {travel:g} deg travel with {self.entry_angle:g} deg entries "
                "leaves no room for the Deck ring"
            )

    # -- radii ------------------------------------------------------------------

    @property
    def coil_radius(self) -> float:
        """Outer radius of the room the cable's turn needs around the core (mm)."""
        return self.core_radius + self.turns * self.fpc_thickness + self.fit

    @property
    def deck_ring(self) -> tuple[float, float]:
        """(inner, outer) radius of the static Deck ring (mm)."""
        r = self.coil_radius
        return (r, r + self.wall_thickness)

    @property
    def lid_ring(self) -> tuple[float, float]:
        """(inner, outer) radius of the Lid ring, turning outside the Deck ring (mm)."""
        r = self.deck_ring[1] + self.fit
        return (r, r + self.wall_thickness)

    @property
    def outer_radius(self) -> float:
        return self.lid_ring[1]

    # -- sectors ----------------------------------------------------------------

    def deck_sector(self) -> tuple[float, float]:
        """(from, to) angle of the Deck ring (deg): clear of the Lid entry's
        whole sweep ``[0, entry + travel]`` and of the Base entry ``[-entry, 0]``."""
        return (self.entry_angle + self.travel, 360.0 - self.entry_angle)

    def lid_sector(self) -> tuple[float, float]:
        """(from, to) angle of the Lid ring when closed (deg): past the Lid
        entry ``[0, entry]``, and short enough that opening by ``travel``
        never brings it over the Base entry."""
        return (self.entry_angle, 360.0 - self.entry_angle - self.travel)

    # -- along X ------------------------------------------------------------------

    def lid_ring_span(self) -> tuple[float, float]:
        half = self.fpc_width / 2.0 + self.fit
        return (self.x - half, self.x + half)

    def inner_span(self) -> tuple[float, float]:
        """(x0, x1) of the core and the Deck ring, disc face to disc face."""
        a, b = self.lid_ring_span()
        return (a - self.fit, b + self.fit)

    def span(self) -> tuple[float, float]:
        """(x0, x1) of the whole guard, discs included."""
        a, b = self.inner_span()
        return (a - self.wall_thickness, b + self.wall_thickness)

    def disc_spans(self) -> tuple[tuple[float, float], tuple[float, float]]:
        (a, b), (c, d) = self.span(), self.inner_span()
        return ((a, c), (d, b))

    # -- geometry (hinge frame: axis along X at y = z = 0) ------------------------

    @staticmethod
    def _arc(radius: float, a0: float, a1: float) -> list[tuple[float, float]]:
        n = max(2, int(math.ceil(abs(a1 - a0) / ARC_STEP)) + 1)
        return [
            (radius * math.cos(math.radians(a0 + (a1 - a0) * i / (n - 1))),
             radius * math.sin(math.radians(a0 + (a1 - a0) * i / (n - 1))))
            for i in range(n)
        ]

    def _sector(self, r0: float, r1: float, a0: float, a1: float, x0: float, x1: float):
        """An annular sector between radii ``r0..r1`` and angles ``a0..a1``, along X."""
        from utilities import cad_helpers

        pts = self._arc(r1, a0, a1) + self._arc(r0, a1, a0)
        body = cad_helpers.extrude_profile_x(pts, x1 - x0)
        return cad_helpers.translate(body, (x0 + x1) / 2.0, 0.0, 0.0)

    def _x_cylinder(self, diameter: float, x0: float, x1: float):
        from utilities import cad_helpers

        body = cad_helpers.rotate_y(cad_helpers.cylinder_centered(diameter, x1 - x0), 90)
        return cad_helpers.translate(body, (x0 + x1) / 2.0, 0.0, 0.0)

    def _box(self, x0, x1, y0, y1, z0, z1):
        from utilities import cad_helpers

        return cad_helpers.translate(
            cad_helpers.box_centered(x1 - x0, y1 - y0, z1 - z0),
            (x0 + x1) / 2.0, (y0 + y1) / 2.0, (z0 + z1) / 2.0,
        )

    def arm_rect(self, setback: float) -> tuple[float, float, float, float]:
        """(x0, x1, y0, y1) in the hinge frame of the guard's Deck side, discs
        and arms included, up to a wall into the Deck's rear face."""
        x0, x1 = self.span()
        return (x0, x1, -self.outer_radius, setback + self.wall_thickness)

    def build_deck(self, setback: float):
        """Core, Deck ring and the two discs with their arms to the Deck's rear
        face (``y = setback``), sunk a wall into it. The arms stay at ``y >= 0``
        and below the axis, where the Lid never swings for a travel of up to
        180 deg."""
        from utilities import cad_helpers

        i0, i1 = self.inner_span()
        parts = [self._x_cylinder(2 * self.core_radius, i0, i1)]
        a0, a1 = self.deck_sector()
        parts.append(self._sector(*self.deck_ring, a0, a1, i0, i1))
        for d0, d1 in self.disc_spans():
            parts.append(self._x_cylinder(2 * self.outer_radius, d0, d1))
            parts.append(self._box(d0, d1, 0.0, setback + self.wall_thickness, -self.outer_radius, 0.0))
        return cad_helpers.union(*parts)

    def build_lid(self, setback: float):
        """The Lid ring and its web out to a wall into the Lid's rear face, in
        the closed position (hinge frame)."""
        from utilities import cad_helpers

        l0, l1 = self.lid_ring_span()
        a0, a1 = self.lid_sector()
        ring = self._sector(*self.lid_ring, a0, a1, l0, l1)
        reach = setback + self.wall_thickness
        web = self._sector(self.lid_ring[0], reach / math.cos(math.radians(a0)), a0, min(a1, 90.0), l0, l1)
        return cad_helpers.union(ring, web)

    def build_slot(self, which: str, setback: float):
        """The Cable slot through a rear wall into the guard's entry: below the
        axis for the Base, above it for the Lid (hinge frame, closed)."""
        x0, x1 = self.lid_ring_span()
        h = self.outer_radius * math.sin(math.radians(self.entry_angle))
        z0, z1 = (-h, 0.0) if which == "base" else (0.0, h)
        # From short of the rear face to a wall past its inner face.
        return self._box(x0, x1, setback - self.fit, setback + 2 * self.wall_thickness, z0, z1)
