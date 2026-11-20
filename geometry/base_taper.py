"""The Tray's base taper on its vertical front/rear walls (ADR-0019, ADR-0022, ADR-0027).

The Tray's X walls are vertical because the accessory rail bolts to a flat,
square face; its front/rear end walls are vertical too (the guide span and the
rod end clamps are pinned to the 140 mm face budget). The end walls still read
as a taper: each leaves the table at the **band stations' axis** -- the face at
the table sits one ``chassis_joint.side_inset`` inside the wall, exactly where
the long-wall screws stand -- and runs up to the **bottom of the joint band**,
so the base is inset, the wall stands straight above it and the band itself
stays prismatic -- the old "taper + band" silhouette, on the pair of walls that
may lean. ``BaseTaper.angle`` is the resulting angle off vertical (derived, not
configured).

The taper is a **draft**: :func:`build_cutter` takes the wedge off the outside
and :func:`build_fill` puts the same wedge back inside the cavity, so the wall
keeps its thickness over the whole taper instead of thinning to a knife edge at
the table.

Only the **corner** stations keep a pad (ADR-0022). The long-wall stations
stand mid-run, and there the taper runs **through** their access cones: the
face at the table passes through the station's axis (ADR-0027), so the outboard
half of the cone's mouth is cut away and the opening flares from the inboard
half-ring up to the lip, with no sliver of floor skin to print as a knife edge;
higher up the wall's draft restores the pier around the cone in one
constant-thickness slope. The corners keep their pads because the chamfered
corner leaves no run to open into -- a pad there is the rounded stop the wall's
taper starts and ends on, set off the corner as today.

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
    """One Tray end wall's base taper, sized from the band joint (mm).

    ``inset`` is the reach at the table (the joint's ``side_inset``) and
    ``angle`` the resulting lean off vertical -- derived, never configured.
    """

    angle: float
    height: float
    inset: float
    runout: float
    pad_radius: float
    stop_radius: float
    half_depth: float
    wall: float
    wall_half_x: float
    stations: tuple[tuple[float, float], ...]  # the padded corner stations
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

    def wall_stations(self, joint: Any) -> tuple[Any, ...]:
        """The joint's stations on this taper's front/rear walls."""
        wall_y = self.half_depth - joint.side_inset
        return tuple(
            s for s in joint.stations if abs(abs(s.y) - wall_y) <= 1e-9
        )

    def through_stations(self, joint: Any) -> tuple[Any, ...]:
        """The wall stations the taper runs through (all but the corner pads)."""
        return tuple(s for s in self.wall_stations(joint) if not s.is_corner)


def cone_lip_z(taper: BaseTaper, recess: Any, mouth_radius: float, margin: float) -> float:
    """Where the access cone crosses the taper's sloped face -- the lip (mm).

    The crossing solves ``cone_r(z) == margin - inset_at(z)``: the wall face
    recedes at ``inset / height`` while the cone narrows at its own slope from
    the mouth to the head pocket.
    """
    slope = (
        taper.inset / taper.height
        + (mouth_radius - recess.pocket_radius) / recess.z_neck
    )
    return (taper.inset + mouth_radius - margin) / slope


def lip_chamfer_limit(
    taper: BaseTaper,
    recess: Any,
    mouth_radius: float,
    margin: float,
    minimum_feature: float,
) -> float:
    """Longest 45 degree chamfer leg the lip takes below the head pocket (mm).

    The lip is the near-vertical crest where the taper's sloped face opens the
    access cone. A leg ``c`` of a 45 degree chamfer runs about ``c`` up that
    crest, so it must stop one ``minimum_feature`` below the pocket's neck.
    Returns a value at or below zero when even a token chamfer would breach it.
    """
    z_lip = cone_lip_z(taper, recess, mouth_radius, margin)
    return recess.z_neck - minimum_feature - z_lip


def _corner_stations(joint: Any, half_depth: float) -> list[Any]:
    """The joint's corner stations: the ones that keep a taper pad.

    The long-wall (side) stations stand mid-run and the taper passes through
    their access cones (ADR-0022), so only the corners -- where the chamfered
    corner leaves no run to open into -- suppress the taper.
    """
    target = half_depth - joint.side_inset
    return [
        s
        for s in joint.stations
        if s.is_corner and abs(abs(s.y) - target) <= 1e-9
    ]


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
    **inset is derived** (ADR-0027): the outer face at the table sits
    ``side_inset`` inside the wall, exactly on the long-wall stations' axes, and
    the angle off vertical follows from that over ``height``. The pads follow
    the recess the joint already sized, but only the corner stations carry one
    (ADR-0022): everywhere else the taper runs straight through the wall,
    opening into the long-wall stations' access cones.
    """
    settings = config.chassis_joint
    minimum_feature = config.material.minimum_feature
    wall = config.wall_thickness
    wall_half_x = joint.band_width / 2.0 - config.corners.chamfer
    half_depth = joint.depth / 2.0
    stations = _corner_stations(joint, half_depth)
    if not stations:
        raise ValueError(
            "no band station stands at a front/rear wall corner: the base "
            "taper has nothing to stop on"
        )

    height = joint.band_z0
    inset = joint.side_inset
    if not 0.0 < inset < half_depth - wall:
        raise ValueError(
            "the base taper's reach must stay inside the wall: "
            f"inset {inset:.2f} of a {half_depth:.2f} mm half-depth"
        )
    angle = math.degrees(math.atan2(inset, height))
    mouth = max(station.mouth_radius for station in stations)
    # The pad keeps one minimum feature of material outside the access cone
    # mouth (ADR-0021), so the floor's lip never breaks into the tapered face.
    pad_radius = mouth + minimum_feature
    stop_radius = pad_radius + settings.taper_runout

    # Where a stop circle crosses the tapered face at the table: the taper
    # resumes that far to either side of the station.
    gap = half_depth - abs(stations[0].y) - inset
    if gap < 0.0 or stop_radius <= gap:
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


def _pads(taper: BaseTaper):
    """The corner stop cylinders the cutter ends on (the taper's rounded stops)."""
    from utilities import cad_helpers as ch

    return [
        ch.translate(
            ch.cylinder_centered(2.0 * taper.stop_radius, taper.height + 2.0 * _EXTRA),
            x,
            y,
            taper.height / 2.0,
        )
        for x, y in taper.stations
    ]


def build_cutter(taper: BaseTaper):
    """The solid that takes both end walls' taper off the outside of the Tray.

    The 15 degree wedge from the table up to ``height`` on each wall, with a
    cylinder of ``stop_radius`` subtracted at every corner pad: the pads keep
    their full face and the taper stops on the cylinder's arc. Everywhere else
    -- the long-wall stations included -- the wedge runs unbroken through the
    wall and opens into the access cones (cut later, in ``case.chassis``).
    """
    from utilities import cad_helpers as ch

    cutter = _both_walls(_profile(taper, taper.half_depth, -_EXTRA), taper)
    return ch.cut(cutter, *_pads(taper))


def build_fill(taper: BaseTaper):
    """The solid that moves the cavity's end faces back behind the taper.

    The wedge between the **drafted** cavity face (``inner_face_y``, one wall
    in from the cutter's line) and the **prismatic** cavity face
    ``half_depth - wall``: at the floor's top it is one ``inset`` wide and it
    closes to a line at the taper's top, where the draft reaches the band. It
    starts at the floor's top (below that the floor is solid) and runs up to
    the band.

    Unioning it back fills the slice of cavity the draft cuts away, so the wall
    keeps its thickness instead of thinning to a knife edge at the table. It
    must reach the prismatic cavity face, not stop one wall short of the
    cutter's line: the shell's inner face is that plane, and a strip that
    stopped at the cutter's line would leave a thin air gap between itself and
    the shell -- the crack that read as a notch beside the corner pad.

    It is **not** clipped on the corner stop cylinders. The pads suppress the
    cutter, so inside a pad the shell keeps the full face: there the fill's
    outer edge meets the shell's inner face on the prismatic cavity plane, and
    the two fuse into one continuous wall. Clipping the fill at a pad would
    instead cut the very material that bridges the drafted run to the pad and
    leave a full-height slot between them -- the rectangular notch beside the
    corner boss. Inside a pad the fill simply thickens the wall, which the head
    recess and the column want (ADR-0022).
    """
    from utilities import cad_helpers as ch

    inner = taper.half_depth - taper.wall
    slope = math.tan(math.radians(taper.angle))
    z0 = taper.wall
    cavity_face = inner - taper.inset + z0 * slope
    profile = [
        (cavity_face, z0),
        (inner, z0),
        (inner, taper.height),
    ]
    length = 2.0 * taper.wall_half_x
    near = ch.extrude_profile_x(profile, length)
    far = ch.extrude_profile_x([(-y, z) for y, z in profile], length)
    return ch.union(near, far)


__all__ = [
    "BaseTaper",
    "base_taper",
    "build_cutter",
    "build_fill",
    "cone_lip_z",
    "lip_chamfer_limit",
]
