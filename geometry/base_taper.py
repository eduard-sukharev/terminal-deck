"""The Tray's base taper on its vertical front/rear walls (ADR-0019).

The Tray's X walls are vertical because the accessory rail bolts to a flat,
square face; its front/rear end walls are vertical too (the guide span and the
rod end clamps are pinned to the 140 mm face budget). The end walls still read
as a taper: each leaves the table `chassis_joint.taper_angle` (15 degrees) off
vertical and runs at that angle up to the **bottom of the joint band**, so the
base is inset, the wall stands straight above it and the band itself stays
prismatic -- the old "taper + band" silhouette, on the pair of walls that may
lean.

The taper is a **draft**: :func:`build_cutter` takes the wedge off the outside
and :func:`build_fill` puts the same wedge back inside the cavity, so the wall
keeps its thickness over the whole taper instead of thinning to a knife edge at
the table.

The **pad** around every station is what makes that legal. The band joint's
access cone mouths sit in the floor right beside those walls, so the taper
would break the floor's lip around them, and the station's column (which
carries the screw from the floor to the plane) would stand proud of the tapered
face. Suppressing the taper within a circle of ``stop_radius`` around each
station bolts both back -- the pad keeps the full face at the cone mouth and
swallows the column -- and the circle's arc is the rounded stop the wall is
drawn with.

Everything here is pure data -- the plan of the taper, its segments along the
wall and the pad circles -- so the drawings, the checks and the CAD agree; only
:func:`build_cutter` and :func:`build_fill` need a CAD library.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

#: The taper's cross-sections overshoot the part on both ends, so the booleans
#: trim clean faces instead of leaving a skin (mm).
_EXTRA = 0.2


@dataclass(frozen=True)
class BaseTaper:
    """One Tray end wall's base taper, sized from the band joint (mm)."""

    angle: float
    height: float
    inset: float
    runout: float
    pad_radius: float
    stop_radius: float
    half_depth: float
    wall: float
    wall_half_x: float
    stations: tuple[tuple[float, float], ...]
    segments: tuple[tuple[float, float], ...]

    @property
    def depth(self) -> float:
        """The Tray's outer depth (mm)."""
        return 2.0 * self.half_depth

    @property
    def base_depth(self) -> float:
        """The footprint's depth between the two tapered walls (mm)."""
        return self.depth - 2.0 * self.inset

    def inset_at(self, z: float) -> float:
        """How far the outer face is pulled in at height ``z`` (mm)."""
        if z <= 0.0:
            return self.inset
        if z >= self.height:
            return 0.0
        return self.inset * (1.0 - z / self.height)

    def face_y(self, z: float) -> float:
        """Plan magnitude of the outer face's Y at height ``z`` (mm)."""
        return self.half_depth - self.inset_at(z)

    def inner_face_y(self, z: float) -> float:
        """Plan magnitude of the cavity's end face at height ``z`` (mm)."""
        return self.half_depth - self.wall - self.inset_at(z)

    def in_pad(self, x: float, y: float) -> bool:
        """Is ``(x, y)`` inside a station's stop circle (taper suppressed)?"""
        return any(
            math.hypot(x - sx, y - sy) <= self.stop_radius for sx, sy in self.stations
        )


def _wall_stations(joint: Any, half_depth: float) -> list[Any]:
    """The joint's stations that stand against a front/rear wall.

    They are the ones inset ``side_inset`` from that wall's outer face
    (``y_wall`` in :func:`geometry.chassis_joint.chassis_joint`), which is what
    the base taper has to step around.
    """
    target = half_depth - joint.side_inset
    return [s for s in joint.stations if abs(abs(s.y) - target) <= 1e-9]


def _segments(
    xs: list[float], crossing: float, wall_half_x: float
) -> tuple[tuple[float, float], ...]:
    """The runs of wall between the station pads, as ``(x0, x1)`` in mm.

    ``xs`` are the stations' ``|x|`` (the wall is symmetric), ``crossing`` is
    where a stop circle meets the tapered face at the table, so the wall
    carries the full taper from ``x + crossing`` to the next station's
    ``x - crossing``. Runs the pads swallow whole are dropped.
    """
    stops = sorted(
        {
            sign * (x + offset)
            for x in xs
            for offset in (-crossing, crossing)
            for sign in (-1.0, 1.0)
        }
    )
    edges = [-wall_half_x, *stops, wall_half_x]
    runs = []
    for x0, x1 in zip(edges[0::2], edges[1::2]):
        if x1 - x0 > 1e-9:
            runs.append((x0, x1))
    return tuple(runs)


def base_taper(config: Any, joint: Any) -> BaseTaper:
    """Size both Tray end walls' base taper from the band joint.

    ``height`` is the bottom of the joint band: the taper runs from the table
    to where the band starts, so the band itself stays prismatic and the slope
    stops 3 mm short of the Parting plane -- the "taper + band" silhouette. The
    inset then follows the configured angle, and the pads follow the recess the
    joint already sized.
    """
    settings = config.chassis_joint
    minimum_feature = config.material.minimum_feature
    wall = config.wall_thickness
    wall_half_x = joint.band_width / 2.0 - config.corners.chamfer
    half_depth = joint.depth / 2.0
    stations = _wall_stations(joint, half_depth)
    if not stations:
        raise ValueError(
            "no band station stands against a front/rear wall: the base taper "
            "has nothing to step around"
        )

    angle = settings.taper_angle
    height = joint.band_z0
    inset = math.tan(math.radians(angle)) * height
    mouth = max(station.mouth_radius for station in stations)
    # The pad keeps one minimum feature of material outside the access cone
    # mouth (ADR-0021), so the floor's lip never breaks into the tapered face.
    pad_radius = mouth + minimum_feature
    stop_radius = pad_radius + settings.taper_runout

    # Where a stop circle crosses the tapered face at the table: the taper
    # resumes that far to either side of the station.
    gap = half_depth - abs(stations[0].y) - inset
    if stop_radius <= gap:
        raise ValueError(
            "the taper's stop circle does not reach the tapered face: the pad "
            f"radius {stop_radius:.2f} <= {gap:.2f} mm"
        )
    crossing = math.sqrt(stop_radius**2 - gap**2)
    xs = sorted(abs(station.x) for station in stations)

    return BaseTaper(
        angle=angle,
        height=height,
        inset=inset,
        runout=settings.taper_runout,
        pad_radius=pad_radius,
        stop_radius=stop_radius,
        half_depth=half_depth,
        wall=wall,
        wall_half_x=wall_half_x,
        stations=tuple((station.x, station.y) for station in stations),
        segments=_segments(xs, crossing, wall_half_x),
    )


def _profile(
    taper: BaseTaper, face: float, foot: float
) -> list[tuple[float, float]]:
    """The (Y, Z) wedge outline that ends on ``face`` at ``taper.height``.

    The slope passes exactly through ``face - inset`` at the table and ``face``
    at the taper's top. ``foot`` is the outline's lowest Z: a cutter runs a
    little below the table so the boolean trims a clean face, a fill starts on
    it (it adds material, so it may not dip under the part).
    """
    slope = math.tan(math.radians(taper.angle))
    return [
        (face - taper.inset + foot * slope, foot),
        (face + _EXTRA, foot),
        (face + _EXTRA, taper.height),
        (face, taper.height),
    ]


def _both_walls(profile: list[tuple[float, float]], taper: BaseTaper):
    """Extrude one wedge outline along X and mirror it onto the other wall."""
    from utilities import cad_helpers as ch

    length = 2.0 * taper.wall_half_x
    near = ch.extrude_profile_x(profile, length)
    far = ch.extrude_profile_x([(-y, z) for y, z in profile], length)
    return ch.union(near, far)


def build_cutter(taper: BaseTaper):
    """The solid that takes both end walls' taper off the outside of the Tray.

    The 15 degree wedge from the table up to ``height`` on each wall, with a
    cylinder of ``stop_radius`` subtracted at every station: the pads keep their
    full face and the taper stops on the cylinder's arc.
    """
    from utilities import cad_helpers as ch

    cutter = _both_walls(_profile(taper, taper.half_depth, -_EXTRA), taper)
    pads = [
        ch.translate(
            ch.cylinder_centered(2.0 * taper.stop_radius, taper.height + 2.0 * _EXTRA),
            x,
            y,
            taper.height / 2.0,
        )
        for x, y in taper.stations
    ]
    return ch.cut(cutter, *pads)


def build_fill(taper: BaseTaper):
    """The solid that moves the cavity's end faces back behind the taper.

    The strip between the two slope lines -- the cutter's line on the outside
    and the same line one wall further in -- from the floor's top up to the
    taper's top. Unioning it back leaves a constant-thickness wall over the
    whole taper instead of the knife edge the cut alone leaves below the
    crossing height. It starts at the floor's top: below that there is no
    cavity to restore (the cut's deeper bottom edge stays), and it ends at the
    taper's top, where the prismatic band wall is already in place. Inside a
    station's pad the cut kept the outer face, so the strip thickens the wall
    there -- which is what the head recess and the column want.
    """
    from utilities import cad_helpers as ch

    inner = taper.half_depth - taper.wall
    slope = math.tan(math.radians(taper.angle))
    z0 = taper.wall
    cavity_face = inner - taper.inset + z0 * slope
    outer_face = cavity_face + taper.wall
    profile = [
        (cavity_face, z0),
        (outer_face, z0),
        (taper.half_depth, taper.height),
        (inner, taper.height),
    ]
    length = 2.0 * taper.wall_half_x
    near = ch.extrude_profile_x(profile, length)
    far = ch.extrude_profile_x([(-y, z) for y, z in profile], length)
    return ch.union(near, far)


__all__ = ["BaseTaper", "base_taper", "build_cutter", "build_fill"]
