"""The screen lid's Bezel <-> Back band joint (ADR-0011).

The lid splits at the Back panel's inner face: a flat 4 mm Back plate and the
Bezel that carries the display, the glass opening and a prismatic fastening
band. Ten stations run round the band — four corners, two per long side and one
on each long side's centreline — with an M3 countersunk screw driven from the
Back's outer face into a heat-set insert in the Bezel's band. The centreline
pair is the Section-Seam interlock (ADR-0015): the Bezel's Seam runs at -14 and
the Back plate's at +10..+18, so a screw there clamps a Bezel piece to the
*other* Back piece instead of leaving the two pairs free to hinge.

The free middle of each *short* side is the Bearing-clamp slot, and the four
corners are where the four Rod clamps sit. The guide rods are now *under* the
display (ADR-0013), so the corner posts sit **inboard of the cavity wall** and
follow the Rod clamp's outer edge: nothing widens the case for them any more.
``post_inner = rod_x + rod_clamp.width/2 + corner_clearance``; the post runs
from there out to the wall and carries the insert with its boss margin.

Pure data: no CAD import, so the data layer can size and check the joint before
the case is built.
"""

from __future__ import annotations

from dataclasses import dataclass

from geometry.parting import DeckScrew, deck_screw
from utilities import fasteners


@dataclass(frozen=True)
class BandStation:
    """One Bezel <-> Back fastener, in the lid's plan coordinates (mm)."""

    x: float
    y: float
    kind: str  # "corner" | "front" | "rear"

    @property
    def is_corner(self) -> bool:
        return self.kind == "corner"


@dataclass(frozen=True)
class LidJoint:
    """Sized band joint: the stations, the posts and the screw.

    All plan values are on the ``+x``/``+y`` side; the case mirrors them.
    """

    band: float
    boss: float
    boss_margin: float
    corner_clearance: float
    corner_length: float
    corner_post_width: float
    post_x: tuple[float, float]
    post_y: tuple[float, float]
    insert_hole: float
    insert_depth: float
    countersink: fasteners.Countersink
    screw: DeckScrew
    grip: float
    stations: tuple[BandStation, ...]

    @property
    def corner_stations(self) -> tuple[BandStation, ...]:
        return tuple(station for station in self.stations if station.is_corner)

    @property
    def edge_stations(self) -> tuple[BandStation, ...]:
        return tuple(station for station in self.stations if not station.is_corner)

    @property
    def station_count(self) -> int:
        return len(self.stations)


def lid_joint(
    *,
    width: float,
    lid_height: float,
    lid_back: float,
    rod_x: float,
    rod_clamp_width: float,
    joint: object,
    wall: float,
) -> LidJoint:
    """Size the lid's band joint from the lid's plan and the guide hardware.

    Raises ``ValueError`` when no stock screw fits the Back's countersink and
    the Bezel's insert; the data layer turns that into a HARD check.
    """
    insert = fasteners.heat_insert(joint.screw)
    countersink = fasteners.countersink(joint.screw)
    hole = insert.printed_hole_diameter
    grip = lid_back - countersink.depth
    screw = deck_screw(joint.screw, grip)

    # The insert has to sit a boss margin clear of every free face it is not
    # merged into: the outer face and the station's own edge.
    inset = max(joint.station_inset, hole / 2.0 + joint.boss_margin)
    y = lid_height / 2.0 - inset
    x_corner = width / 2.0 - (hole / 2.0 + joint.boss_margin)
    x_edge = width / 6.0

    stations: list[BandStation] = []
    for sign in (-1, 1):
        for x, kind in (
            (x_corner, "corner"),
            (-x_corner, "corner"),
            (x_edge, "front" if sign < 0 else "rear"),
            (-x_edge, "front" if sign < 0 else "rear"),
            # ADR-0015's interlock: the Bezel Seam runs at -14 and the Back
            # plate's at +10..+18, so a station on the centreline sits between
            # them and clamps a Bezel piece to the *other* Back piece.
            (0.0, "front" if sign < 0 else "rear"),
        ):
            stations.append(BandStation(x=x, y=sign * y, kind=kind))

    # Corner post: from just outboard of the Rod clamp to the cavity wall, and
    # `corner_length` along the side. It merges with the two walls. The guide
    # rods are under the display (ADR-0013), so this post no longer grows the
    # case: its width is whatever is left between the clamp and the wall.
    post_outer_x = width / 2.0 - wall
    post_inner_x = rod_x + rod_clamp_width / 2.0 + joint.corner_clearance
    if post_inner_x >= post_outer_x:
        raise ValueError(
            "the lid band's corner post has no width: the Rod clamp at "
            f"x {rod_x:.2f} reaches the cavity wall (post inner "
            f"{post_inner_x:.2f} >= outer {post_outer_x:.2f} mm)"
        )
    return LidJoint(
        band=joint.band,
        boss=joint.boss,
        boss_margin=joint.boss_margin,
        corner_clearance=joint.corner_clearance,
        corner_length=joint.corner_length,
        corner_post_width=post_outer_x - post_inner_x,
        post_x=(post_inner_x, post_outer_x),
        post_y=(lid_height / 2.0 - joint.corner_length, lid_height / 2.0 - wall),
        insert_hole=hole,
        insert_depth=insert.depth,
        countersink=countersink,
        screw=screw,
        grip=grip,
        stations=tuple(stations),
    )


__all__ = ["BandStation", "LidJoint", "lid_joint"]
