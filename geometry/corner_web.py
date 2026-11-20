"""The corner stations' web into the Tray's and Deck's X walls (ADR-0029).

A corner band station stands ``side_inset`` from the vertical front/rear wall
and ``station_inset`` from the vertical X wall. Its round column therefore
pierces the front/rear cavity wall -- which the merge fillet eases
(:func:`geometry.edge_treatment.merge_column_walls`, ADR-0024) -- but it also
clips the **inner corner chamfer** (ADR-0016) by less than a millimetre. The
chord it leaves on that 45 degree face is a reentrant crease in a gorge only
30-40 degrees wide: the merge fillet cannot roll there (a 1.5 mm round needs
about 4 mm of surface on each side, and the face has 1.3 mm to its outer
corner), so the corner boss would keep one sharp side.

The fix is not to move the screw: the corner column gets a **web** into the X
wall, so it merges into both walls and the corner chop is filled by material
instead of being crossed by a round. The web is a prism from the column's axis
to the X wall, as wide as the column and tangent to it on both sides, clipped
to the part's outer solid (it overshoots into the walls and must never break
the outer skin). Its tangency means it adds no crease against the column: the
only new edges are

* one vertical chord where the web's inboard face crosses the X wall face
  (a clean 90 degree reentrant corner, so the merge fillet fits), and
* one horizontal base edge where that face meets the Tray's floor / the Deck's
  ceiling (rounded by the boss-base fillet).

The web is tangent to the column at the radius the column has over its height:
the Deck's boss is one diameter, while the Tray's column is wider at the floor
than above the access cone's neck, so the Tray passes its strict radius -- the
frustum is wider there and simply swallows the web's side face.

Everything here is pure data (the web's plan, its chord and its base segment);
only :func:`case.chassis.Chassis` needs a CAD library.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

#: How far the web runs into its X wall (mm): buried, so the union trims a
#: clean face instead of relying on a coincident one.
_WALL_OVER = 0.5


@dataclass(frozen=True)
class CornerWeb:
    """One corner column's web into the X wall, in the chassis plan (mm).

    ``x``/``y`` are the station axis, ``radius`` the column radius the web is
    tangent to, ``x_wall``/``y_wall`` the signed cavity faces it stands on and
    ``y_in`` the web's inboard side (``y + side * radius`` on the inside).
    """

    x: float
    y: float
    radius: float
    x_wall: float
    y_wall: float

    @property
    def x_side(self) -> float:
        return math.copysign(1.0, self.x)

    @property
    def y_side(self) -> float:
        return math.copysign(1.0, self.y)

    @property
    def y_in(self) -> float:
        """The inboard side: the plane tangent to the column, toward ``y = 0``."""
        return self.y - self.y_side * self.radius

    @property
    def y_out(self) -> float:
        """The outboard side: tangent too, and buried in the front/rear wall."""
        return self.y + self.y_side * self.radius

    @property
    def x_out(self) -> float:
        """The outer end: one ``_WALL_OVER`` into the X wall."""
        return self.x_side * (abs(self.x_wall) + _WALL_OVER)

    def plan(self) -> tuple[float, float, float, float]:
        """``(x0, x1, y0, y1)`` of the web's prism, signed."""
        x0, x1 = sorted((self.x, self.x_out))
        y0, y1 = sorted((self.y_in, self.y_out))
        return x0, x1, y0, y1

    @property
    def chord(self) -> tuple[float, float]:
        """Where the web's inboard face crosses the X wall: the new chord."""
        return abs(self.x_wall) * self.x_side, self.y_in

    @property
    def tangent(self) -> tuple[float, float]:
        """Where the web leaves the column: tangent, so no crease."""
        return self.x, self.y_in

    @property
    def base_midpoint(self) -> tuple[float, float]:
        """Midpoint of the base edge between the tangent point and the chord."""
        cx, cy = self.chord
        return (self.x + cx) / 2.0, cy

    @property
    def base_span(self) -> tuple[float, float]:
        """The base edge's X range (from the tangent point to the chord)."""
        x0, x1 = sorted((self.x, self.chord[0]))
        return x0, x1


@dataclass(frozen=True)
class CornerWebs:
    """The four corner webs, plus what has to hold for them to be sound."""

    webs: tuple[CornerWeb, ...]
    failures: tuple[str, ...] = ()

    @property
    def ok(self) -> bool:
        return not self.failures


def corner_webs(
    joint: Any,
    wall: float,
    chamfer: float,
    radius: float,
) -> CornerWebs:
    """Build one web per corner station (ADR-0029).

    ``radius`` is the column radius the web is tangent to over the height it is
    built on: the Tray passes its strict radius (the cone below the neck is
    wider and swallows the web's side face), the Deck its boss radius.

    The web has to reach the X wall and cover the inner corner chamfer, or the
    column would still cross the chop: its outward side must pass the chamfer's
    foot on that wall, and its inboard side must stay inside the cavity.
    """
    from utilities.cad_helpers import inner_corner_chamfer

    x_wall = joint.band_width / 2.0 - wall
    y_wall = joint.depth / 2.0 - wall
    relief = inner_corner_chamfer(chamfer, wall)

    webs: list[CornerWeb] = []
    failures: list[str] = []
    for station in joint.corner_stations:
        web = CornerWeb(
            x=station.x,
            y=station.y,
            radius=radius,
            x_wall=math.copysign(x_wall, station.x),
            y_wall=math.copysign(y_wall, station.y),
        )
        # The chamfer's foot on the X wall: where the chop meets the wall face.
        foot = abs(y_wall) - relief
        if abs(web.y_out) < foot:
            failures.append(
                f"corner web at ({station.x:.2f}, {station.y:.2f}) stops "
                f"{foot - abs(web.y_out):.2f} mm short of the corner chamfer "
                f"(foot {foot:.2f}, web side {abs(web.y_out):.2f})"
            )
        if abs(web.y_in) > foot:
            failures.append(
                f"corner web at ({station.x:.2f}, {station.y:.2f}) has no "
                f"cavity side (inboard {abs(web.y_in):.2f} vs chamfer foot "
                f"{foot:.2f})"
            )
        if abs(web.x_out) <= abs(web.x_wall):
            failures.append(
                f"corner web at ({station.x:.2f}, {station.y:.2f}) does not "
                f"reach the X wall {abs(web.x_wall):.2f}"
            )
        webs.append(web)
    return CornerWebs(tuple(webs), tuple(failures))


__all__ = ["CornerWeb", "CornerWebs", "corner_webs"]
