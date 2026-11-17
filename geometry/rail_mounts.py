"""The accessory rail's stations and its printed parts (ADR-0020).

The rail bolts to the Tray's vertical X walls (ADR-0019 made them vertical for
exactly this). Everything about the interface is derived here, as pure data, so
the pocket in the Tray, the pad around it, the ribs that carry the clamp load
and the rail's own holes come from one source:

* **two M4 stations per wall**, mirrored fore and aft of the wall's centre, on
  the wall's mid-height. The spacing is a configuration value and must be a
  whole number of slot pitches, which is also what puts both screws on the
  profile's bridge centres instead of in a slot;
* **a pad** at each station: a square column ``2 * wall`` deep into the cavity,
  from the floor up to the Parting plane, so it merges into the wall and the
  floor and nothing of it is a free-hanging boss. It carries the square pocket
  the printed washer puck drops into;
* **two 45 degree gussets** at the pad's fore and aft faces, down to the floor.
  Their run is derived from the nearest obstacle on either side (the band
  joint's columns stand on this wall) and the pair is kept symmetric, so a
  tight neighbour shortens both instead of making one rib stubby;
* **the washer puck**: a square printed washer that captures a DIN 562 M4
  square nut. It cannot rotate (square pocket), it cannot fall in (the pad's
  pocket floor behind it) and it lifts back out (it protrudes one fit);
* **the rail blank**: the MIL-STD-1913 width across the wall, ``height`` thick,
  one slot pitch of run past each end, with a counterbored M4 hole on each
  station. The profile itself (slots, hex top) is a later slice on top of an
  unchanged interface, which is why the bridge-centre rule is checked now.

The module is pure data -- no CAD import -- so the checks and the drawings can
size the interface before any solid exists. The solids are built by
:mod:`case.chassis` (the Tray features) and :mod:`components.accessory_rail`
(the two printed parts).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from utilities import fasteners

#: Tolerance for "surfaces touch but do not overlap" (mm).
_EPS = 1e-9


@dataclass(frozen=True)
class RailStation:
    """One M4 rail station on one Tray X wall.

    ``x_outer``/``x_inner`` are the wall's outer and cavity faces as positive
    numbers: the station is mirrored onto both walls by its ``side``. The pad
    runs from ``x_inner`` where ``pad_depth`` deep into the cavity, so the
    pocket opens at ``x_pad_in`` and its floor -- the face the puck bears on --
    is ``pocket_floor``. ``gusset_run`` is how far each 45 degree gusset runs
    from the pad's face along the wall before it is truncated.
    """

    name: str
    side: int
    y: float
    z: float
    x_outer: float
    x_inner: float
    pad_width: float
    pad_depth: float
    pocket_side: float
    pocket_depth: float
    gusset_run: float
    clearance_hole: float
    reasons: tuple[str, ...] = ()

    @property
    def x_pad_in(self) -> float:
        """The pad's cavity face: where the pocket opens (mm)."""
        return self.x_inner - self.pad_depth

    @property
    def pocket_floor(self) -> float:
        """The pocket's floor: the face the washer puck bears on (mm)."""
        return self.x_pad_in + self.pocket_depth

    @property
    def gusset_height(self) -> float:
        """The gusset's apex height above the floor (45 degrees, so = run)."""
        return self.gusset_run

    @property
    def y0(self) -> float:
        """The pad's lower Y edge (mm)."""
        return self.y - self.pad_width / 2.0

    @property
    def y1(self) -> float:
        """The pad's upper Y edge (mm)."""
        return self.y + self.pad_width / 2.0

    @property
    def valid(self) -> bool:
        return not self.reasons

    def summary(self) -> str:
        state = "ok" if self.valid else "FAIL: " + "; ".join(self.reasons)
        return (
            f"  {self.name:14s} x={self.side * self.x_outer:8.2f} "
            f"y={self.y:8.2f} z={self.z:6.2f} pad {self.pad_width:.2f} x "
            f"{self.pad_depth:.2f} pocket {self.pocket_side:.2f} x "
            f"{self.pocket_depth:.2f} gussets {self.gusset_run:.2f} [{state}]"
        )


@dataclass(frozen=True)
class RailMounts:
    """The whole accessory-rail interface: stations, printed parts, screw."""

    stations: tuple[RailStation, ...]
    interface: str
    width: float
    height: float
    length: float
    pitch: float
    spacing: float
    wall: float
    minimum_feature: float
    head_recess: fasteners.HeadRecess
    screw: fasteners.Screw
    nut: fasteners.SquareNut
    screw_stack: float
    stock_length: float
    puck_width: float
    puck_thickness: float
    puck_pocket: float
    puck_floor: float
    protrusion: float
    reasons: tuple[str, ...] = ()

    @property
    def ok(self) -> bool:
        return not self.reasons and all(s.valid for s in self.stations)

    @property
    def failures(self) -> tuple[str, ...]:
        return self.reasons + tuple(
            f"{s.name}: {reason}" for s in self.stations for reason in s.reasons
        )

    @property
    def station_offsets(self) -> tuple[float, ...]:
        """The stations' Y offsets from the wall's centre (mm)."""
        return tuple(sorted({s.y for s in self.stations}))

    @property
    def rail_half_span(self) -> float:
        """Half the rail's length (mm)."""
        return self.length / 2.0

    @property
    def x_outer(self) -> float:
        """The Tray X wall's outer face, as a positive X (mm)."""
        return self.stations[0].x_outer

    @property
    def rail_center_x(self) -> float:
        """The rail blank's own centre, as a positive X (mm)."""
        return self.x_outer + self.height / 2.0

    def summary(self) -> str:
        lines = [
            f"Accessory rail ({self.interface}): {len(self.stations)} "
            f"stations, spacing {self.spacing:.2f} mm",
            f"  rail {self.width:.2f} x {self.length:.2f} x "
            f"{self.height:.2f} mm, pitch {self.pitch:.2f}",
            f"  puck {self.puck_width:.2f} sq x {self.puck_thickness:.2f}, "
            f"nut pocket {self.puck_pocket:.2f} x {self.puck_pocket:.2f}",
            f"  screw {self.screw.size} x {self.stock_length:.0f} "
            f"(stack {self.screw_stack:.2f})",
        ]
        lines.extend(s.summary() for s in self.stations)
        for reason in self.reasons:
            lines.append(f"  FAIL: {reason}")
        return "\n".join(lines)


def plan_gap(x: float, y: float, rect: tuple[float, float, float, float]) -> float:
    """Distance from a point to an axis-aligned rectangle (0 inside) (mm)."""
    x0, y0, x1, y1 = rect
    dx = max(x0 - x, 0.0, x - x1)
    dy = max(y0 - y, 0.0, y - y1)
    return math.hypot(dx, dy)


def station_offsets(count: int, spacing: float) -> tuple[float, ...]:
    """The stations' Y offsets for an even ``count`` on one wall (mm).

    They are mirrored about the wall's centre and one ``spacing`` apart, so an
    even count never puts a station on the centreline (where the lid's band
    post and the Tray's band stations live).
    """
    if count % 2:
        raise ValueError("the rail stations must be mirrored: count must be even")
    half = count // 2
    return tuple(
        sorted(
            sign * (k + 0.5) * spacing
            for k in range(half)
            for sign in (-1, 1)
        )
    )


def rail_mounts(config: Any, joint: Any) -> RailMounts:
    """Size the accessory rail's interface from the configuration and band.

    ``joint`` is the chassis band joint (it carries the width, the parting
    plane and the stations); the rail needs nothing else from the budget, so
    the data layer can size and check it before any solid exists.
    """
    settings = config.slide.rail
    minimum = config.material.minimum_feature
    wall = config.wall_thickness

    nut = fasteners.square_nut(settings.nut)
    screw = fasteners.screw(settings.screw)
    head = fasteners.head_recess(
        settings.screw,
        settings.head,
        fit=config.clearance.head,
        depth_margin=config.clearance.head,
    )

    # The printed washer puck: its square pocket is the nut's pocket, its rim
    # is two minimum features so the 0.6 mm floor it leaves under the nut is
    # not a washer with no washer left around it.
    puck_pocket = nut.pocket
    puck_width = puck_pocket + 4.0 * minimum
    puck_thickness = nut.height + minimum
    protrusion = settings.fit
    puck_floor = puck_thickness - nut.height
    pocket_side = puck_width + 2.0 * settings.fit
    pocket_depth = puck_thickness - protrusion

    pad_width = pocket_side + 2.0 * minimum
    pad_depth = 2.0 * wall

    x_outer = joint.band_width / 2.0
    x_inner = x_outer - wall
    z = joint.parting_z / 2.0
    spacing = settings.station_spacing
    length = spacing + 2.0 * settings.pitch

    # Where the rail's own screws bear: the head sits in a counterbore, so the
    # rail's web under it, the wall, the pad behind the pocket, the puck's
    # floor and the nut are the stack the screw has to span.
    rail_web = settings.height - head.depth
    screw_stack = (
        rail_web + wall + (pad_depth - pocket_depth) + puck_floor + nut.height
    )
    stock = next(
        (
            candidate
            for candidate in fasteners.STANDARD_LENGTHS[settings.screw]
            if candidate >= screw_stack + minimum
        ),
        None,
    )
    reasons: list[str] = []
    if stock is None:
        reasons.append(
            f"no stock {settings.screw} screw spans the {screw_stack:.2f} mm "
            "station stack"
        )
        stock = max(fasteners.STANDARD_LENGTHS[settings.screw])
    elif stock > screw_stack + settings.pitch:
        reasons.append(
            f"the stock {settings.screw} x {stock:.0f} leaves more than one "
            f"pitch of thread past the nut ({stock - screw_stack:.2f} mm)"
        )
    if rail_web < minimum:
        reasons.append(
            f"the rail's web under the head is {rail_web:.2f} < min feature "
            f"{minimum:.2f}; raise slide.rail.height or use a lower head"
        )

    # The band joint's columns stand on this wall; the pad and the gussets
    # have to keep clear of them or a cusp would form between two solids.
    x_wall_stations = [
        (station.x, station.y, station.boss)
        for station in joint.stations
        if station.kind == "end"
    ]
    straight_end = joint.depth / 2.0 - config.corners.chamfer

    # One rib shape for the whole interface: the stations' tightest free run
    # decides, so a station next to a band column shortens its partner too
    # rather than leaving one rib a fin and one a stub. The axis height caps
    # it -- a rib taller than the screw it serves stiffens nothing.
    prepared: list[dict[str, Any]] = []
    for side in (-1, 1):
        side_stations = [
            (x, y, boss)
            for x, y, boss in x_wall_stations
            if (x > 0) == (side > 0)
        ]
        for name, offset in zip(
            ("front", "rear"),
            station_offsets(settings.stations, spacing),
        ):
            y = offset
            pad_y0 = y - pad_width / 2.0
            pad_y1 = y + pad_width / 2.0
            pad_rect = (x_inner - pad_depth, pad_y0, x_inner, pad_y1)
            reasons_here: list[str] = []

            # The free run on each side of the pad, as a plan distance to the
            # nearest band column (the wall's straight end is the other bound).
            runs = []
            for direction, edge in ((-1, pad_y0), (1, pad_y1)):
                space = straight_end - edge if direction > 0 else edge + straight_end
                for sx, sy, boss in side_stations:
                    clearance = plan_gap(abs(sx), sy, pad_rect) - boss / 2.0
                    if clearance < -_EPS:
                        reasons_here.append(
                            f"the pad runs into the band column at "
                            f"({sx:.2f}, {sy:.2f})"
                        )
                        space = 0.0
                        continue
                    # Only an obstacle on this side bounds this side's run.
                    if (sy > y) == (direction > 0):
                        beyond = (
                            sy - boss / 2.0 - edge
                            if direction > 0
                            else edge - (sy + boss / 2.0)
                        )
                        space = min(space, beyond)
                runs.append(max(space, 0.0))

            pocket_z0 = z - pocket_side / 2.0
            pocket_z1 = z + pocket_side / 2.0
            if pocket_z0 - wall < minimum:
                reasons_here.append(
                    f"the pocket's lower edge ({pocket_z0:.2f}) is closer than "
                    f"min feature {minimum:.2f} to the floor top ({wall:.2f})"
                )
            if joint.parting_z - pocket_z1 < minimum:
                reasons_here.append(
                    f"the pocket's upper edge ({pocket_z1:.2f}) is closer than "
                    f"min feature {minimum:.2f} to the Parting plane "
                    f"({joint.parting_z:.2f})"
                )
            prepared.append(
                {
                    "name": f"{name}-{'left' if side < 0 else 'right'}",
                    "side": side,
                    "y": y,
                    "runs": runs,
                    "reasons": reasons_here,
                }
            )

    tightest = min(min(item["runs"]) for item in prepared)
    gusset_run = min(tightest, z - wall) - minimum
    if gusset_run < minimum:
        reasons.append(
            f"no room for a 45 degree gusset: the tightest side leaves "
            f"{tightest:.2f} mm"
        )
        gusset_run = minimum

    stations = [
        RailStation(
            name=item["name"],
            side=item["side"],
            y=item["y"],
            z=z,
            x_outer=x_outer,
            x_inner=x_inner,
            pad_width=pad_width,
            pad_depth=pad_depth,
            pocket_side=pocket_side,
            pocket_depth=pocket_depth,
            gusset_run=gusset_run,
            clearance_hole=screw.clearance,
            reasons=tuple(item["reasons"]),
        )
        for item in prepared
    ]

    return RailMounts(
        stations=tuple(stations),
        interface=settings.interface,
        width=settings.width,
        height=settings.height,
        length=length,
        pitch=settings.pitch,
        spacing=spacing,
        wall=wall,
        minimum_feature=minimum,
        head_recess=head,
        screw=screw,
        nut=nut,
        screw_stack=screw_stack,
        stock_length=float(stock),
        puck_width=puck_width,
        puck_thickness=puck_thickness,
        puck_pocket=puck_pocket,
        puck_floor=puck_floor,
        protrusion=protrusion,
        reasons=tuple(reasons),
    )


__all__ = [
    "RailMounts",
    "RailStation",
    "plan_gap",
    "rail_mounts",
    "station_offsets",
]
