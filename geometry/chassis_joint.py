"""The chassis Tray <-> Deck band joint (ADR-0012).

The chassis splits at the Parting plane (ADR 0003). The ``band`` is split
evenly around the plane: the Tray is drafted from its base up to ``band_z0``
and prismatic from ``band_z0`` to the Parting plane; the Deck is prismatic all
the way from the plane to the closed face. Only the lower half of the
silhouette tapers; the Deck and the closed face stay straight. This is the
chassis counterpart of the lid's Bezel <-> Back band joint (ADR-0011).

Ten M3 screws are driven from below, through a countersink in the Tray's floor
and a column standing on that floor, into a heat-set insert in a boss in the
Deck's band:

* four corners,
* two per long side (front and rear walls),
* one per short side (left and right walls).

Because the Tray is drafted, a straight column of the full boss diameter
cannot both stay inside the Tray's outer skin at the floor and merge into the
prismatic band's wall at the plane. The column is therefore a frustum: the
boss diameter at the plane, tapering to whatever the floor skin allows. The
station diameters are derived per station from the local wall, never assumed.

Each half also gets a shallow scallop at every station, straddling the seam:
the Tray's 3 mm below the plane, the Deck's 3 mm above it. Both scallops cut a
prismatic wall, so they are straight prisms a constant ``scallop_depth`` deep.

Pure data: no CAD import, so the data layer can size and check the joint
before the case is built.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

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
    scallop_width: float
    scallop_depth: float
    scallop_height: float
    insert_hole: float
    insert_depth: float
    boss_height: float
    countersink: fasteners.Countersink
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
        """The tightest Tray column at the floor (the drafted X walls)."""
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
) -> TrayStation:
    """Size one station from the wall it sits against.

    The band (and therefore the station's ``surface``) is prismatic; the Tray's
    drafted X walls only pull the floor skin inward, which is what
    ``base_distance`` measures.
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
        surface = band_half_x - ax
    else:
        surface = chamfer_surface

    # At the floor the drafted X walls have receded toward the station by the
    # full draft inset; the Y walls are still where they were.
    base_chamfer = (base_half_x + base_half_y - chamfer - ax - ay) * math.sqrt(0.5)
    base_distance = min(base_half_x - ax, base_half_y - ay, base_chamfer)

    # The boss may grow until its surface reaches the outer skin; the column
    # additionally has to stay inside the Tray's skin at the floor.
    station_boss = min(boss, 2.0 * (surface - minimum_feature))
    base_boss = min(station_boss, 2.0 * (base_distance - minimum_feature))
    return TrayStation(
        x=x,
        y=y,
        kind=kind,
        normal=normal,
        surface=surface,
        boss=station_boss,
        base_boss=base_boss,
        base_distance=base_distance,
    )


def chassis_joint(
    *,
    width: float,
    depth: float,
    chassis_top: float,
    draft_angle: float,
    minimum_feature: float,
    chamfer: float,
    parting: object,
    joint: object,
) -> ChassisJoint:
    """Size the chassis' band joint from the envelope and the Parting plane.

    The band is split evenly around the Parting plane: ``band_z0`` is where the
    Tray's draft ends and its prismatic band begins, ``band_z1`` is the top of
    the Deck's prismatic band (halfway up the Deck, in practice). Because the
    Deck is prismatic, the band width is the full closed-face width and the
    base is the drafted width at ``band_z0`` rather than at the table. Raises
    ``ValueError`` when no stock screw fits the Tray column and the Deck
    insert; the data layer turns that into a HARD check.
    """
    insert = fasteners.heat_insert(joint.screw)
    countersink = fasteners.countersink(joint.screw)
    hole = insert.printed_hole_diameter

    draft_tan = math.tan(math.radians(draft_angle))
    parting_z = parting_height(parting, chassis_top)
    band_z0 = parting_z - joint.band / 2.0
    band_z1 = parting_z + joint.band / 2.0
    # The Deck (and therefore the band across the joint) is prismatic at the
    # closed-face width; only the Tray below band_z0 is drafted.
    band_width = width
    base_width = width - 2.0 * draft_tan * band_z0
    grip = parting_z - countersink.depth
    screw = deck_screw(joint.screw, grip)

    base_half_x = base_width / 2.0
    band_half_x = band_width / 2.0
    depth_half = depth / 2.0

    x_edge = band_half_x - joint.station_inset
    y_corner = depth_half - joint.station_inset
    y_side = depth_half - joint.side_inset
    x_mid = band_width / 6.0
    if min(x_edge, y_corner, y_side, x_mid) <= 0.0:
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
    )

    stations: list[TrayStation] = []

    def add(x: float, y: float, kind: str) -> None:
        for sx in ((-1, 1) if x else (1,)):
            for sy in ((-1, 1) if y else (1,)):
                stations.append(_station(sx * x, sy * y, kind, **common))

    add(x_edge, y_corner, "corner")
    add(x_mid, y_side, "side")
    add(x_edge, 0.0, "end")

    return ChassisJoint(
        band=joint.band,
        boss=joint.boss,
        boss_margin=joint.boss_margin,
        station_inset=joint.station_inset,
        side_inset=joint.side_inset,
        scallop_width=joint.scallop_width,
        scallop_depth=joint.scallop_depth,
        scallop_height=joint.scallop_height,
        insert_hole=hole,
        insert_depth=insert.depth,
        # The Deck's half of the band is only `band/2` tall; the insert boss
        # rises out of it far enough to hold the full insert plus a margin.
        boss_height=insert.depth + joint.boss_margin,
        countersink=countersink,
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
