"""The chassis Tray <-> Deck band joint (ADR-0012).

The chassis splits at the Parting plane (ADR 0003). The ``band`` is split
evenly around the plane: the Tray is prismatic from its base up to the Parting
plane (ADR-0019 removed its X draft -- the accessory rail needs a flat, square
face) and so is the Deck all the way to the closed face. The silhouette does
not taper; the base taper on the front/rear walls lives in
:mod:`geometry.base_taper`. This is the chassis counterpart of the lid's
Bezel <-> Back band joint (ADR-0011).

Twelve M3 screws are driven from below, through a **keyhole recess** in the
Tray's floor and a column standing on that floor, into a heat-set insert in a
boss in the Deck's band (ADR-0018: an ordinary button head seats in a
counterbored pocket with a 45 degree lift-out ramp, not a flush countersink):

* four corners,
* three per long side (front and rear walls) -- one of them on the centreline,
* one per short side (left and right walls).

The centreline long-wall stations are ADR-0015's interlock: the Tray's Seam and
the Deck's Seam run past it on opposite sides, so the screw ties the two
staggered cuts together.

Every wall is vertical now, so the floor skin is exactly the band's skin: the
column is a straight boss from the floor to the Parting plane and its diameter
is only capped by the plan distance from the station to the nearest free face
(``2 * (margin - minimum_feature)``). The station diameters are derived per
station from the local wall, never assumed.

Pure data: no CAD import, so the data layer can size and check the joint
before the case is built.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from geometry import head_recess
from geometry.parting import DeckScrew, deck_screw, parting_height
from utilities import fasteners


@dataclass(frozen=True)
class TrayStation:
    """One Tray <-> Deck fastener station, in the chassis plan (mm).

    All values are on the ``+x``/``+y`` side; the case mirrors them.
    """

    x: float
    y: float
    kind: str  # "corner" | "side" | "end"
    #: Outward unit normal in XY (from the station towards the near outer face).
    normal: tuple[float, float]
    #: Distance from the station to the band's outer face along ``normal``.
    surface: float
    #: Insert boss / column diameter at the Parting plane.
    boss: float
    #: Column diameter on the Tray floor (never larger than :attr:`boss`).
    base_boss: float
    #: Distance from the station to the Tray's outer skin at the floor.
    base_distance: float
    #: Plan margin to the nearest free face of the floor skin -- what the
    #: head recess's mouth is measured against (``base_distance``'s twin; the
    #: floor skin is where the recess is cut).
    margin: float
    #: The 45 degree chamfer that fairs the recess mouth (mm).
    mouth_chamfer: float
    #: Material left between the recess mouth and that free face (mm).
    edge_margin: float

    @property
    def is_corner(self) -> bool:
        return self.kind == "corner"

    @property
    def is_side(self) -> bool:
        return self.kind == "side"

    @property
    def is_end(self) -> bool:
        return self.kind == "end"


@dataclass(frozen=True)
class ChassisJoint:
    """Sized Tray <-> Deck band joint: the stations, the band and the screw."""

    band: float
    boss: float
    boss_margin: float
    station_inset: float
    side_inset: float
    insert_hole: float
    insert_depth: float
    recess: fasteners.HeadRecess
    screw: DeckScrew
    grip: float
    chassis_top: float
    parting_z: float
    band_z0: float
    band_z1: float
    band_width: float
    base_width: float
    depth: float
    stations: tuple[TrayStation, ...]

    @property
    def corner_stations(self) -> tuple[TrayStation, ...]:
        return tuple(s for s in self.stations if s.is_corner)

    @property
    def side_stations(self) -> tuple[TrayStation, ...]:
        return tuple(s for s in self.stations if s.is_side)

    @property
    def end_stations(self) -> tuple[TrayStation, ...]:
        return tuple(s for s in self.stations if s.is_end)

    @property
    def station_count(self) -> int:
        return len(self.stations)

    def smallest_boss(self) -> float:
        """The tightest insert boss (the front/rear walls, next to the keys)."""
        return min(station.boss for station in self.stations)

    def smallest_base_boss(self) -> float:
        """The tightest Tray column at the floor (the short walls next to it)."""
        return min(station.base_boss for station in self.stations)


def _station(
    x: float,
    y: float,
    kind: str,
    *,
    band_half_x: float,
    band_half_y: float,
    base_half_x: float,
    base_half_y: float,
    chamfer: float,
    boss: float,
    minimum_feature: float,
    pocket_radius: float,
) -> TrayStation:
    """Size one station from the wall it sits against.

    The band (and therefore the station's ``surface``) is prismatic and the
    Tray's walls are vertical (ADR-0019), so ``surface`` and the floor margin
    measure the same plan distance.
    """
    if kind == "side":
        normal = (0.0, math.copysign(1.0, y))
    elif kind == "end":
        normal = (math.copysign(1.0, x), 0.0)
    else:
        root = math.sqrt(0.5)
        normal = (math.copysign(root, x), math.copysign(root, y))

    ax, ay = abs(x), abs(y)
    # The 45 deg corner chamfer is the outer face on the diagonal.
    chamfer_surface = (band_half_x + band_half_y - chamfer - ax - ay) * math.sqrt(0.5)
    if kind == "side":
        surface = band_half_y - ay
    elif kind == "end":
        # The short-side stations sit in the free band behind the keyboard (the
        # narrow case leaves no band beside the keys), so they are close to two
        # walls: cap the boss by the nearer.
        surface = min(band_half_x - ax, band_half_y - ay)
    else:
        # A corner is close to both walls and on the diagonal chamfer; the
        # tightest of the three is what the boss may grow to.
        surface = min(chamfer_surface, band_half_x - ax, band_half_y - ay)

    # Every wall is vertical, so the floor skin is the band's skin: this is the
    # margin the column *and* the head recess in the floor are measured
    # against, so the two are sized from one number.
    base_chamfer = (base_half_x + base_half_y - chamfer - ax - ay) * math.sqrt(0.5)
    margin = min(base_half_x - ax, base_half_y - ay, base_chamfer)

    # The boss may grow until its surface reaches the outer skin; the column
    # additionally has to stay inside the Tray's skin at the floor.
    station_boss = min(boss, 2.0 * (surface - minimum_feature))
    base_boss = min(station_boss, 2.0 * (margin - minimum_feature))
    return TrayStation(
        x=x,
        y=y,
        kind=kind,
        normal=normal,
        surface=surface,
        boss=station_boss,
        base_boss=base_boss,
        base_distance=margin,
        margin=margin,
        mouth_chamfer=head_recess.mouth_chamfer(
            pocket_radius, margin, minimum_feature
        ),
        edge_margin=head_recess.edge_margin(pocket_radius, margin, minimum_feature),
    )


def chassis_joint(
    *,
    width: float,
    depth: float,
    chassis_top: float,
    content_y1: float,
    minimum_feature: float,
    chamfer: float,
    parting: object,
    joint: object,
    head_fit: float,
) -> ChassisJoint:
    """Size the chassis' band joint from the envelope and the Parting plane.

    The band is split evenly around the Parting plane: ``band_z0`` is the
    bottom of the Tray's half, ``band_z1`` is the top of the Deck's (halfway up
    the Deck, in practice). Both halves are prismatic (ADR-0019), so the band
    width *and* the base width are the full closed-face width.

    ``content_y1`` is the plan Y of the tallest content's rear edge (the
    keyboard): the case is only as wide as the content plus a thin wall, so the
    band beside the keys has no room for a station and the short sides are
    fastened in the free band behind the keyboard instead.

    ``head_fit`` is the radial gap around the button head and its recess
    ``depth`` clearance below the floor face (``clearance.head``).

    Raises ``ValueError`` when no stock screw fits the Tray column and the Deck
    insert; the data layer turns that into a HARD check.
    """
    insert = fasteners.heat_insert(joint.screw)
    recess = fasteners.head_recess(
        joint.screw,
        joint.head,
        fit=head_fit,
        depth_margin=head_fit,
        ramp_angle=head_recess.RAMP_ANGLE_DEG,
    )
    hole = insert.printed_hole_diameter

    parting_z = parting_height(parting, chassis_top)
    band_z0 = parting_z - joint.band / 2.0
    band_z1 = parting_z + joint.band / 2.0
    # Both halves are prismatic (ADR-0019): the Tray no longer drafts inward
    # from its band, so its base is the closed-face width as well.
    band_width = width
    base_width = width
    grip = parting_z - recess.depth
    screw = deck_screw(joint.screw, grip)

    base_half_x = base_width / 2.0
    band_half_x = band_width / 2.0
    depth_half = depth / 2.0

    x_edge = band_half_x - joint.station_inset
    # Every long-wall station -- the corners included -- sits `side_inset` from
    # the vertical front/rear wall: the narrow case leaves only this much band
    # beside the keyboard, which caps those bosses at 2 x (inset - min feature).
    y_wall = depth_half - joint.side_inset
    # One station per short side, in the middle of the free band behind the
    # keyboard. There is no band beside the keys at this width, and the 10 mm
    # front strip is narrower than a boss.
    y_end = (content_y1 + depth_half) / 2.0
    x_mid = band_width / 6.0
    if min(x_edge, y_wall, x_mid) <= 0.0 or y_end <= 0.0:
        raise ValueError(
            "chassis joint station inset is too large for the chassis plan "
            f"(band {band_width:.2f} x {depth:.2f} mm)"
        )

    common = dict(
        band_half_x=band_half_x,
        band_half_y=depth_half,
        base_half_x=base_half_x,
        base_half_y=depth_half,
        chamfer=chamfer,
        boss=joint.boss,
        minimum_feature=minimum_feature,
        pocket_radius=recess.pocket_radius,
    )

    stations: list[TrayStation] = []

    def add(x: float, y: float, kind: str) -> None:
        for sx in ((-1, 1) if x else (1,)):
            for sy in ((-1, 1) if y else (1,)):
                stations.append(_station(sx * x, sy * y, kind, **common))

    add(x_edge, y_wall, "corner")
    add(x_mid, y_wall, "side")
    # ADR-0015: one more station per long wall, on the centreline. The Tray's
    # Seam and the Deck's Seam pass on either side of it, so this screw is what
    # cross-ties the two staggered cuts: its insert boss belongs to one Deck
    # half and its Tray column to the other Tray half.
    add(0.0, y_wall, "side")
    for sx in (-1, 1):
        stations.append(_station(sx * x_edge, y_end, "end", **common))

    return ChassisJoint(
        band=joint.band,
        boss=joint.boss,
        boss_margin=joint.boss_margin,
        station_inset=joint.station_inset,
        side_inset=joint.side_inset,
        insert_hole=hole,
        insert_depth=insert.depth,
        recess=recess,
        screw=screw,
        grip=grip,
        chassis_top=chassis_top,
        parting_z=parting_z,
        band_z0=band_z0,
        band_z1=band_z1,
        band_width=band_width,
        base_width=base_width,
        depth=depth,
        stations=tuple(stations),
    )


__all__ = ["ChassisJoint", "TrayStation", "chassis_joint"]
