"""The chassis Tray <-> Deck band joint (ADR-0012).

The chassis splits at the Parting plane (ADR 0003). The ``band`` is split
evenly around the plane: the Tray is prismatic from its base up to the Parting
plane (ADR-0019 removed its X draft -- the accessory rail needs a flat, square
face) and so is the Deck all the way to the closed face. The silhouette does
not taper; the base taper on the front/rear walls lives in
:mod:`geometry.base_taper`. This is the chassis counterpart of the lid's
Bezel <-> Back band joint (ADR-0011).

Twelve M3 screws are driven from below, through a **deep conical recess** in
the Tray's floor and a column standing on that floor, into a heat-set insert
in a boss in the Deck's band (ADR-0021: the button head is buried at the top
of the cavity, one wall below the Parting plane, and the driver reaches it
down a cone that widens to the floor face -- no keyhole ramp, ADR-0018's
profile stays the lid's):

* four corners,
* three per long side (front and rear walls) -- one of them on the centreline,
* one per short side (left and right walls).

The centreline long-wall stations are ADR-0015's interlock: the Tray's Seam and
the Deck's Seam run past it on opposite sides, so the screw ties the two
staggered cuts together.

Every wall is vertical now, so the floor skin is exactly the band's skin: the
column runs straight from the floor to the Parting plane and its diameter is
capped by the plan distance from the station to the nearest free face
(``2 * (margin - minimum_feature)``). All stations share one boss diameter --
the tightest station's own cap (the long-wall stations', pinned by the
keyboard plate) -- so a station standing in free space does not grow fatter
than the wall beside the keys requires.

The access cone's mouth stays one minimum feature inside the station's column
footprint, so the pier keeps a thick ring at the floor (``margin - mouth`` = the
skin lip plus one minimum feature where the margin binds) instead of a knife
edge. From the cone's neck to the Parting plane the column is cylindrical with
strict dimensions (the head pocket plus one minimum feature a side); below the
neck both the cavity and the column's outer wall run conical, the column as a
frustum from its floor footprint down to the strict diameter. The head pocket
and its seat stay inside the column.

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
    #: Column diameter in the strict zone above the access cone's neck (the
    #: head pocket and the skin under the Parting plane): the pocket plus two
    #: minimum features, cylindrical while the head and the screw need exact
    #: surroundings (ADR-0021).
    strict_boss: float
    #: Distance from the station to the Tray's outer skin at the floor.
    base_distance: float
    #: Plan margin to the nearest free face of the floor skin -- what the
    #: recess's mouth is measured against (``base_distance``'s twin; the floor
    #: skin is where the recess is cut).
    margin: float
    #: The access cone's radius at the floor face (mm) -- one minimum feature
    #: inside the column's floor footprint, so the pier keeps a thick ring.
    mouth_radius: float
    #: Material left between the access cone mouth and that free face (mm) --
    #: the pier's wall at the floor.
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
    recess: head_recess.DeepRecess
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
    def skin(self) -> float:
        """Material between the head's seat and the Parting plane (mm)."""
        return self.parting_z - self.recess.z_seat

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


def _station_plan(
    x: float,
    y: float,
    kind: str,
    *,
    band_half_x: float,
    band_half_y: float,
    base_half_x: float,
    base_half_y: float,
    chamfer: float,
) -> tuple[tuple[float, float], float, float]:
    """Position one station: its outward normal and plan distances.

    Returns ``(normal, surface, margin)`` -- the distances to the band's outer
    face and to the Tray's outer skin at the floor. The band (and therefore the
    station's ``surface``) is prismatic and the Tray's walls are vertical
    (ADR-0019), so ``surface`` and the floor margin measure the same plan
    distance.
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
    return normal, surface, margin


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

    ``boss`` is the shared cap (see :func:`chassis_joint`), not the config's
    upper bound: every station's boss is the same diameter.
    """
    normal, surface, margin = _station_plan(
        x,
        y,
        kind,
        band_half_x=band_half_x,
        band_half_y=band_half_y,
        base_half_x=base_half_x,
        base_half_y=base_half_y,
        chamfer=chamfer,
    )

    # The boss may grow until its surface reaches the outer skin; the column
    # additionally has to stay inside the Tray's skin at the floor.
    station_boss = min(boss, 2.0 * (surface - minimum_feature))
    base_boss = min(station_boss, 2.0 * (margin - minimum_feature))
    # ADR-0021: the access cone's mouth stays one minimum feature inside the
    # column's floor footprint, so the pier keeps a thick ring at the floor
    # (`margin - mouth_radius` = the skin lip + one minimum feature where the
    # margin binds) instead of dying into a knife edge.
    mouth_radius = base_boss / 2.0 - minimum_feature
    # Above the cone's neck the column is cylindrical with strict dimensions:
    # the head pocket plus one minimum feature a side, no more.
    strict_boss = 2.0 * (pocket_radius + minimum_feature)
    return TrayStation(
        x=x,
        y=y,
        kind=kind,
        normal=normal,
        surface=surface,
        boss=station_boss,
        base_boss=base_boss,
        strict_boss=strict_boss,
        base_distance=margin,
        margin=margin,
        mouth_radius=mouth_radius,
        edge_margin=margin - mouth_radius,
    )


def chassis_joint(
    *,
    width: float,
    depth: float,
    chassis_top: float,
    content_y1: float,
    minimum_feature: float,
    chamfer: float,
    wall: float,
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

    ``head_fit`` is the radial gap around the button head (``clearance.head``).

    ADR-0021: the head is buried at the top of a deep conical access cavity --
    its seat sits one ``wall`` below the Parting plane, so exactly one wall of
    material is left over it, and the screw's grip is that same wall. Raises
    ``ValueError`` when no stock screw fits the Tray column and the Deck
    insert; the data layer turns that into a HARD check.
    """
    insert = fasteners.heat_insert(joint.screw)
    parting_z = parting_height(parting, chassis_top)
    z_seat = parting_z - wall
    recess = head_recess.deep_recess(
        joint.screw,
        joint.head,
        fit=head_fit,
        z_seat=z_seat,
    )
    hole = insert.printed_hole_diameter

    band_z0 = parting_z - joint.band / 2.0
    band_z1 = parting_z + joint.band / 2.0
    # Both halves are prismatic (ADR-0019): the Tray no longer drafts inward
    # from its band, so its base is the closed-face width as well.
    band_width = width
    base_width = width
    grip = parting_z - recess.z_seat
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

    plan: list[tuple[float, float, str]] = []

    def plan_add(x: float, y: float, kind: str) -> None:
        for sx in ((-1, 1) if x else (1,)):
            for sy in ((-1, 1) if y else (1,)):
                plan.append((sx * x, sy * y, kind))

    plan_add(x_edge, y_wall, "corner")
    plan_add(x_mid, y_wall, "side")
    # ADR-0015: one more station per long wall, on the centreline. The Tray's
    # Seam and the Deck's Seam pass on either side of it, so this screw is what
    # cross-ties the two staggered cuts: its insert boss belongs to one Deck
    # half and its Tray column to the other Tray half.
    plan_add(0.0, y_wall, "side")
    # The end stations mirror about the X centreplane alone: the free band
    # behind the keyboard exists only at one end.
    for sx in (-1, 1):
        plan.append((sx * x_edge, y_end, "end"))

    # Every boss is one diameter: the shared cap is the tightest station's own
    # maximum (the long-wall stations', pinned by the keyboard plate at
    # `side_inset`), so the free-standing end stations do not grow fatter just
    # because empty space allows it.
    plan_common = dict(
        band_half_x=band_half_x,
        band_half_y=depth_half,
        base_half_x=base_half_x,
        base_half_y=depth_half,
        chamfer=chamfer,
    )
    boss_cap = min(
        joint.boss,
        min(
            2.0 * (_station_plan(x, y, kind, **plan_common)[2] - minimum_feature)
            for x, y, kind in plan
        ),
    )

    common = dict(
        plan_common,
        boss=boss_cap,
        minimum_feature=minimum_feature,
        pocket_radius=recess.pocket_radius,
    )
    stations = [_station(x, y, kind, **common) for x, y, kind in plan]

    return ChassisJoint(
        band=joint.band,
        boss=boss_cap,
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
