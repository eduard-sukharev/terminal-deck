"""Visor: the Lid shell's tapered lip that takes up the Deck's slope.

Closed, the Lid's flat underside sits on a plane through the Deck's highest
point (at the hinge end); the sloped Deck leaves a wedge below it. The Visor
walls (front and both sides of the Lid shell) fill that wedge, so the closed
device is a box. Height at any Y equals the gap between that plane and the
Deck top; it is zero where the Deck stops rising (the hinge end).

Opened, the Visor stands proud of the Bezel along the top edge of the screen.

``VisorProfile`` is pure data (importable without a CAD library);
:func:`build_walls` turns it into a solid.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class VisorProfile:
    """Visor wall height along Y, linear between knots.

    ``knots`` are ``(y, height)`` pairs sorted by Y; outside the range the
    height holds the nearest knot's value. Y is the Lid shell's local Y, which
    equals the Base's Y when the Lid is closed (the Lid folds about a
    Y-parallel axis).
    """

    knots: tuple[tuple[float, float], ...]

    def height_at(self, y: float) -> float:
        knots = self.knots
        if y <= knots[0][0]:
            return knots[0][1]
        for (y0, h0), (y1, h1) in zip(knots, knots[1:]):
            if y <= y1:
                return h0 + (h1 - h0) * (y - y0) / (y1 - y0)
        return knots[-1][1]

    @property
    def max_height(self) -> float:
        return max(h for _, h in self.knots)


def build_walls(profile: VisorProfile, width: float, depth: float, wall: float,
                corner_radius: float, z_base: float):
    """Visor walls: a wall-thick perimeter ring standing on ``z_base`` and
    trimmed to ``profile`` (height along Y). The ring follows the Lid shell's
    outline, so it is flush with the shell walls."""
    from geometry import fillet
    from utilities import cad_helpers

    height = profile.max_height
    if height <= 0.0:
        return cad_helpers.empty_solid()
    outer = cad_helpers.box_centered(width, depth, height)
    outer = fillet.fillet_corners(outer, corner_radius)
    inner = cad_helpers.box_centered(width - 2 * wall, depth - 2 * wall, height + 2.0)
    inner = fillet.fillet_corners(inner, max(corner_radius - wall, 0.0))
    ring = cad_helpers.cut(outer, inner)
    ring = cad_helpers.translate(ring, 0.0, 0.0, z_base + height / 2.0)

    # Side profile (Y, Z) extruded across X trims the ring to the taper.
    pad = 1.0
    rear, front = -depth / 2.0 - pad, depth / 2.0 + pad
    pts = [(rear, z_base - pad)]
    pts += [(y, z_base + h) for y, h in profile.knots]
    pts += [(front, z_base + profile.height_at(front)), (front, z_base - pad)]
    trim = cad_helpers.extrude_profile_x(pts, width + 2 * pad)
    return cad_helpers.intersect(ring, trim)
