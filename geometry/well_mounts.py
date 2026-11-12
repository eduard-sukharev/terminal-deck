"""Plate boss stations and ear outlines (ADR-0014).

The keyboard plate hangs under the Deck's Well, screwed flat against the lower
faces of the Well's 2 mm ring from below. This module computes that mounting
pattern in plan, as pure data:

* **eight M2 insert stations** -- four per plate Section: front-outer,
  front-at-Seam, rear-at-Seam, rear-outer, each mirrored in X. The boss is
  merged to the ring's *outer* face in the front/rear lips, so an M2 bore only
  needs ``merged_boss.bore_margin`` towards the ring and
  ``chassis_joint.boss_margin`` towards the lip's outer wall;
* **ears** -- the plate's ring-width border cannot hold the M2 clearance hole
  with its edge margin, so a filleted tab grows outboard of the ring under each
  station, one plate thickness thick;
* **notches** -- the chassis band joint (ADR-0012) and the bearing-clamp seats
  must not collide with the plate. A chassis feature whose Z span overlaps the
  plate's and whose plan footprint reaches the plate becomes a notch rectangle
  the plate builder cuts out; the plate has to stay one connected sheet
  afterwards, which is checked by rasterising the sheet.

Everything is derived from the configuration, the fastener library and the
slide budget -- no dimension is chosen here. The module is pure data: no CAD
import, and no import from the ``components`` or ``case`` packages (the budget
and the Well are duck-typed parameters), so the data layer can size and check
the mounts before any solid exists.

Plan coordinates are the chassis frame (X right, Y along the slide, origin at
the chassis footprint's centre). Plate-local coordinates are centred on the
plate -- the same frame the keyboard's geometry model uses.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from utilities import fasteners

#: The four stations per plate Section, in the ADR-0014 pattern.
STATIONS: tuple[str, ...] = ("front-outer", "front-seam", "rear-seam", "rear-outer")

#: Tolerance for "surfaces touch but do not overlap" (mm).
_EPS = 1e-9


# -- plan geometry -------------------------------------------------------


@dataclass(frozen=True)
class PlanRect:
    """An axis-aligned rectangle in a plan (mm)."""

    x0: float
    y0: float
    x1: float
    y1: float

    def __post_init__(self) -> None:
        if self.x1 < self.x0 or self.y1 < self.y0:
            raise ValueError(f"PlanRect is inside out: {self}")

    @classmethod
    def from_centre(cls, cx: float, cy: float, width: float, depth: float) -> "PlanRect":
        return cls(cx - width / 2.0, cy - depth / 2.0, cx + width / 2.0, cy + depth / 2.0)

    @classmethod
    def from_circle(cls, cx: float, cy: float, diameter: float) -> "PlanRect":
        """The bounding square of a circle -- a disc's plan footprint."""
        return cls.from_centre(cx, cy, diameter, diameter)

    @classmethod
    def from_points(cls, points) -> "PlanRect":
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        return cls(min(xs), min(ys), max(xs), max(ys))

    @property
    def width(self) -> float:
        return self.x1 - self.x0

    @property
    def depth(self) -> float:
        return self.y1 - self.y0

    @property
    def cx(self) -> float:
        return (self.x0 + self.x1) / 2.0

    @property
    def cy(self) -> float:
        return (self.y0 + self.y1) / 2.0

    def expanded(self, amount: float) -> "PlanRect":
        return PlanRect(
            self.x0 - amount, self.y0 - amount, self.x1 + amount, self.y1 + amount
        )

    def translated(self, dx: float, dy: float) -> "PlanRect":
        return PlanRect(self.x0 + dx, self.y0 + dy, self.x1 + dx, self.y1 + dy)

    def intersection(self, other: "PlanRect") -> "PlanRect | None":
        x0, x1 = max(self.x0, other.x0), min(self.x1, other.x1)
        y0, y1 = max(self.y0, other.y0), min(self.y1, other.y1)
        if x1 <= x0 or y1 <= y0:
            return None
        return PlanRect(x0, y0, x1, y1)

    def overlaps(self, other: "PlanRect", clearance: float = 0.0) -> bool:
        """True when the rectangles are closer than ``clearance``.

        Touching faces (a shared edge) count as *no* overlap: the plate may
        sit exactly on a feature, it just may not share volume with it.
        """
        return not (
            self.x0 - clearance >= other.x1
            or other.x0 >= self.x1 + clearance
            or self.y0 - clearance >= other.y1
            or other.y0 >= self.y1 + clearance
        )

    def contains_inner(self, inner: "PlanRect", margin: float = 0.0) -> bool:
        """True when ``inner`` lies inside by at least ``margin`` on every side."""
        return (
            inner.x0 - margin >= self.x0 - _EPS
            and inner.x1 + margin <= self.x1 + _EPS
            and inner.y0 - margin >= self.y0 - _EPS
            and inner.y1 + margin <= self.y1 + _EPS
        )

    def contains_point(self, x: float, y: float) -> bool:
        return (
            self.x0 - _EPS <= x <= self.x1 + _EPS
            and self.y0 - _EPS <= y <= self.y1 + _EPS
        )


@dataclass(frozen=True)
class Obstacle:
    """A solid feature the plate and its bosses must keep clear of (mm).

    ``rect`` is its plan footprint, ``z0``/``z1`` its vertical span. A round
    feature (a band column, a seat boss) also carries ``circle`` --
    ``(cx, cy, radius)`` -- so the notch it forces into the plate can be the
    real chord of the disc instead of its bounding square. The chassis features
    this module derives, and the ``obstacles`` argument, are in plan
    coordinates; ``cutouts`` are plate-local, the frame the plate builder works
    in.
    """

    name: str
    rect: PlanRect
    z0: float
    z1: float
    circle: tuple[float, float, float] | None = None

    def overlaps_z(self, z0: float, z1: float) -> bool:
        return self.z0 < z1 - _EPS and self.z1 > z0 + _EPS


@dataclass(frozen=True)
class PlateFrame:
    """The plate in the chassis plan: centre plus size (mm).

    ``to_local``/``to_plan`` convert between the chassis plan and the plate's
    own centred frame, which is what the keyboard's geometry model uses.
    """

    cx: float
    cy: float
    width: float
    depth: float

    @property
    def x0(self) -> float:
        return self.cx - self.width / 2.0

    @property
    def x1(self) -> float:
        return self.cx + self.width / 2.0

    @property
    def y0(self) -> float:
        return self.cy - self.depth / 2.0

    @property
    def y1(self) -> float:
        return self.cy + self.depth / 2.0

    @property
    def rect(self) -> PlanRect:
        return PlanRect(self.x0, self.y0, self.x1, self.y1)

    @property
    def local_rect(self) -> PlanRect:
        return PlanRect.from_centre(0.0, 0.0, self.width, self.depth)

    def to_local(self, x: float, y: float) -> tuple[float, float]:
        return (x - self.cx, y - self.cy)

    def to_plan(self, x: float, y: float) -> tuple[float, float]:
        return (x + self.cx, y + self.cy)

    def to_local_rect(self, rect: PlanRect) -> PlanRect:
        return rect.translated(-self.cx, -self.cy)

    def to_plan_rect(self, rect: PlanRect) -> PlanRect:
        return rect.translated(self.cx, self.cy)


@dataclass(frozen=True)
class Ear:
    """A filleted tab extending the plate outboard of the Well ring (mm).

    ``rect`` is plate-local and includes the inboard ``overlap`` the union
    needs; ``protrusion`` is how far the tab reaches past the ring's outer face
    (which is the plate's own edge).
    """

    rect: PlanRect
    protrusion: float
    overlap: float
    fillet: float | None
    thickness: float


@dataclass(frozen=True)
class WellMount:
    """One M2 insert station under the Well's front or rear lip (mm).

    ``x``/``y`` are chassis plan, ``plate_xy`` is the same point in the plate's
    centred frame. ``boss_z0``/``boss_z1`` is the boss's vertical span: it stands
    on the plate's top face and merges into the ring's outer face. ``reasons``
    lists every check that failed -- a station is never moved or dropped
    silently.
    """

    station: str
    side: int
    x: float
    y: float
    plate_xy: tuple[float, float]
    boss_diameter: float
    insert_hole_diameter: float
    insert_depth: float
    boss_z0: float
    boss_z1: float
    clearance_hole_diameter: float
    ear: Ear | None
    reasons: tuple[str, ...]

    @property
    def section(self) -> str:
        return "left" if self.side < 0 else "right"

    @property
    def name(self) -> str:
        return f"{self.station}-{self.section}"

    @property
    def valid(self) -> bool:
        return not self.reasons

    @property
    def is_front(self) -> bool:
        return self.station.startswith("front")

    @property
    def plan_rect(self) -> PlanRect:
        """The boss's plan footprint (its disc's bounding square)."""
        return PlanRect.from_circle(self.x, self.y, self.boss_diameter)

    @property
    def ear_half_width(self) -> float:
        """Half the ear's width across the station (mm)."""
        return 0.0 if self.ear is None else self.ear.rect.width / 2.0

    def summary(self) -> str:
        state = "ok" if self.valid else "FAIL: " + "; ".join(self.reasons)
        ear = (
            "ear none"
            if self.ear is None
            else f"ear {self.ear.rect.width:.2f} x {self.ear.rect.depth:.2f}"
        )
        return (
            f"  {self.name:22s} x={self.x:8.2f} y={self.y:8.2f} "
            f"boss Ø{self.boss_diameter:.2f} {ear} [{state}]"
        )


@dataclass(frozen=True)
class PlateNotch:
    """A rectangle the chassis forces the plate to give up (plate-local mm).

    ``source`` names the chassis feature that produced it; ``depth`` is how far
    it bites into the sheet from the nearest plate edge, ``intrusion`` how far
    the feature itself reaches past the ring's outer face -- the reach that must
    not pierce the ring.
    """

    rect: PlanRect
    source: str
    obstacle: PlanRect
    clearance: float
    depth: float
    intrusion: float


@dataclass(frozen=True)
class WellMounts:
    """The plate's eight boss stations, their ears and the forced notches."""

    frame: PlateFrame
    mounts: tuple[WellMount, ...]
    notches: tuple[PlateNotch, ...]
    failures: tuple[str, ...]
    sheet_connected: bool
    # -- one source for the screw and the boss ---------------------------
    screw: str
    boss_diameter: float
    boss_height: float
    insert_hole_diameter: float
    insert_depth: float
    clearance_hole_diameter: float
    head_diameter: float
    head_depth: float
    # -- derived plan margins --------------------------------------------
    bore_margin: float
    boss_margin: float
    ear_half_width: float
    ear_protrusion: float
    ear_fillet: float | None
    lip_required: float
    seam_far: float
    seam_clearance: float
    # -- the Well and the plate they were derived from --------------------
    plate_width: float
    plate_depth: float
    plate_thickness: float
    plate_bottom: float
    plate_top: float
    ring: float
    front_lip: float
    rear_lip: float

    @property
    def ok(self) -> bool:
        return self.sheet_connected and not self.failures

    @property
    def invalid(self) -> tuple[WellMount, ...]:
        return tuple(m for m in self.mounts if not m.valid)

    @property
    def section_mounts(self) -> dict[str, tuple[WellMount, ...]]:
        return {
            section: tuple(m for m in self.mounts if m.section == section)
            for section in ("left", "right")
        }

    @property
    def front_lip_slack(self) -> float:
        """Material the front lip has left beyond what the boss needs (mm)."""
        return self.front_lip - self.lip_required

    @property
    def cutout_rect(self) -> PlanRect:
        """The Well Cutout in plan: the plate inset by the ring on every side."""
        return PlanRect(
            self.frame.x0 + self.ring,
            self.frame.y0 + self.ring,
            self.frame.x1 - self.ring,
            self.frame.y1 - self.ring,
        )

    def mount(self, name: str) -> WellMount:
        for mount in self.mounts:
            if mount.name == name:
                return mount
        raise KeyError(name)

    def summary(self) -> str:
        state = "PASS" if self.ok else "FAIL"
        first = self.mounts[0]
        lines = [
            f"plate mounts: {len(self.mounts)} x {self.screw} "
            f"(boss Ø{self.boss_diameter:.2f}, "
            f"insert Ø{self.insert_hole_diameter:.2f} x {self.insert_depth:.1f} "
            f"deep, z {first.boss_z0:.2f}-{first.boss_z1:.2f}) on a "
            f"{self.plate_width:.2f} x {self.plate_depth:.2f} x "
            f"{self.plate_thickness:.1f} plate (ring {self.ring:.2f}, "
            f"front lip {self.front_lip:.2f}, rear lip {self.rear_lip:.2f})",
            f"  seam clearance {self.seam_clearance:.2f} mm (Seam reaches "
            f"{self.seam_far:.2f} + ear {self.ear_half_width:.2f} + min feature)",
        ]
        lines.extend(mount.summary() for mount in self.mounts)
        lines.append(
            f"  notches: {len(self.notches)}"
            + "".join(
                f" [{n.source} -> {n.rect.width:.2f} x {n.rect.depth:.2f}, "
                f"{n.depth:.2f} deep]"
                for n in self.notches
            )
        )
        lines.append(
            f"  sheet {'connected' if self.sheet_connected else 'SEVERED'} "
            f"-> {state}"
        )
        lines.extend(f"  [FAIL] {failure}" for failure in self.failures)
        return "\n".join(lines)


# -- chassis features the plate must clear -------------------------------


def _band_station_obstacles(joint) -> tuple[Obstacle, ...]:
    """The Tray columns / Deck bosses of the chassis band joint (ADR-0012)."""
    return tuple(
        Obstacle(
            name=f"chassis-joint:{station.kind}@{station.x:.2f},{station.y:.2f}",
            rect=PlanRect.from_circle(station.x, station.y, station.boss),
            z0=joint.band_z0,
            z1=joint.parting_z + joint.boss_height,
            circle=(station.x, station.y, station.boss / 2.0),
        )
        for station in joint.stations
    )


def bearing_seat_obstacles(config, budget) -> tuple[Obstacle, ...]:
    """The Deck's two bearing-clamp seat blocks, one per guide rod (mm).

    Derived the way :class:`~case.slider_frame.SliderFrame` derives them: the
    pocket is the clamp foot plus the seat fit, and the block adds the seat wall
    around it. The block hangs from the Deck's top face, so its underside is
    above the plate -- the Z check states the gap rather than assuming it.
    """
    clamp = config.slide.bearing_clamp
    margin = clamp.seat_fit + clamp.seat_wall
    half_width = budget.clamp_width / 2.0 + margin
    half_length = clamp.foot_length / 2.0 + margin
    seat_height = clamp.foot_thickness + clamp.seat_floor
    z0 = budget.chassis_top - seat_height
    return tuple(
        Obstacle(
            name=f"bearing-seat:{'left' if side < 0 else 'right'}",
            rect=PlanRect.from_centre(
                side * budget.rod_x,
                budget.clamp_center_y,
                2.0 * half_width,
                2.0 * half_length,
            ),
            z0=z0,
            z1=budget.chassis_top,
        )
        for side in (-1, 1)
    )


# -- derivation helpers --------------------------------------------------


def _screw_size(config) -> str:
    mounting = getattr(config.keyboard, "mounting", None) or {}
    return str(mounting.get("screw", "M2"))


def _plate_corner_radius(config) -> float:
    plate = getattr(config.keyboard, "plate", None) or {}
    return float(plate.get("corner_radius", 0.0))


def _seam_far(config, override: float | None) -> float:
    """How far in X the plate's Seam may sweep from the centreline (mm).

    The plate keeps a straight Seam today, but its Sections must already be
    laid out for the stepped Seam the chassis and lid use (ADR-0003), so the
    widest of the two sweeps is taken -- either can be overridden with the plate
    Seam's real path (the row-jogging Seam, T5).
    """
    if override is not None:
        return abs(override)
    split = config.slide.split
    far = 0.0
    for name in ("chassis", "keyboard_plate"):
        part = split.get(name)
        if part is not None:
            far = max(far, *(abs(v) for v in part.seams()[0].x_range))
    return far


def _inboard_x(
    limit: float,
    band: tuple[float, float],
    obstacles,
    clearance: float,
    half: float,
) -> float:
    """Walk ``limit`` inboard until a tab of ``half`` clears every obstacle.

    Only obstacles that can reach a tab on the +X side are considered: the
    pattern mirrors, and the Seam keeps every tab out of the far half, so a
    left-hand obstacle can never collide with a right-hand tab.
    """
    x = limit
    for _ in range(len(obstacles) + 2):
        hit = None
        for obstacle in obstacles:
            rect = obstacle.rect
            if rect.x1 <= 0.0:
                continue
            if rect.y1 + clearance <= band[0] or rect.y0 - clearance >= band[1]:
                continue
            if rect.x1 <= x - half - clearance or rect.x0 >= x + half + clearance:
                continue
            hit = obstacle
            break
        if hit is None:
            return x
        x = min(x, hit.rect.x0 - clearance - half)
    return x


def _footprint_bite(
    obstacle: Obstacle, plate_rect: PlanRect, minimum: float
) -> PlanRect | None:
    """The bounding rectangle of the feature's plan area inside the plate.

    A round feature uses its real disc, sampled at the printable minimum
    feature (chords shorter than that are invisible to the printer), so a
    corner column that only clips the plate's corner bites a chord, not its
    whole bounding square. A rectangular feature is cut by the plate exactly.
    """
    if obstacle.circle is None:
        return plate_rect.intersection(obstacle.rect)
    cx, cy, radius = obstacle.circle
    segments = max(16, int(math.ceil(2.0 * math.pi * radius / minimum)))
    xs: list[float] = []
    ys: list[float] = []

    def add(x: float, y: float) -> None:
        if plate_rect.contains_point(x, y):
            xs.append(min(max(x, plate_rect.x0), plate_rect.x1))
            ys.append(min(max(y, plate_rect.y0), plate_rect.y1))

    for index in range(segments):
        angle = 2.0 * math.pi * index / segments
        add(cx + radius * math.cos(angle), cy + radius * math.sin(angle))
    # The disc's axis extremes: the sampling may straddle them.
    for x, y in (
        (cx, cy - radius),
        (cx, cy + radius),
        (cx - radius, cy),
        (cx + radius, cy),
    ):
        add(x, y)
    # The plate corners inside the disc ...
    for x, y in (
        (plate_rect.x0, plate_rect.y0),
        (plate_rect.x1, plate_rect.y0),
        (plate_rect.x0, plate_rect.y1),
        (plate_rect.x1, plate_rect.y1),
    ):
        if (x - cx) ** 2 + (y - cy) ** 2 <= radius * radius:
            add(x, y)
    # ... and where the plate's edges cut the disc: those chord ends are the
    # extremes the sampling cannot hit exactly.
    for edge in (plate_rect.y0, plate_rect.y1):
        if abs(edge - cy) < radius:
            half = math.sqrt(radius * radius - (edge - cy) ** 2)
            add(cx - half, edge)
            add(cx + half, edge)
    for edge in (plate_rect.x0, plate_rect.x1):
        if abs(edge - cx) < radius:
            half = math.sqrt(radius * radius - (edge - cx) ** 2)
            add(edge, cy - half)
            add(edge, cy + half)
    if not xs:
        return None
    return PlanRect(min(xs), min(ys), max(xs), max(ys))


def _notch_depth(local: PlanRect, frame: PlateFrame) -> float:
    """How far a notch bites into the sheet from the plate edge it crosses.

    A notch in a plate corner crosses two edges; the shallowest of the two
    reaches is reported. The rectangle itself carries the full shape, so this
    is only the one-number summary (and the check that it is not a full-width
    cut).
    """
    half_w, half_d = frame.width / 2.0, frame.depth / 2.0
    reaches = []
    if local.x0 < -half_w + _EPS:
        reaches.append(local.x1 + half_w)
    if local.x1 > half_w - _EPS:
        reaches.append(half_w - local.x0)
    if local.y0 < -half_d + _EPS:
        reaches.append(local.y1 + half_d)
    if local.y1 > half_d - _EPS:
        reaches.append(half_d - local.y0)
    return min(reaches) if reaches else min(local.width, local.depth)


def _sheet_connected(positives, negatives, resolution: float) -> bool:
    """Flood-fill the sheet: is every remaining cell reachable from one cell?

    The sheet is rasterised at the printable minimum feature, so anything
    thinner than that does not count as material: a notch that only leaves a
    sliver cannot keep the plate "connected". Interior holes (switch cutouts)
    are removed too, but cannot disconnect anything by themselves.
    """
    if not positives:
        return False
    x0 = min(r.x0 for r in positives)
    y0 = min(r.y0 for r in positives)
    x1 = max(r.x1 for r in positives)
    y1 = max(r.y1 for r in positives)
    nx = max(1, int(math.ceil((x1 - x0) / resolution)))
    ny = max(1, int(math.ceil((y1 - y0) / resolution)))
    dx, dy = (x1 - x0) / nx, (y1 - y0) / ny

    def fill(mask: bytearray, rect: PlanRect, value: int) -> None:
        i0 = max(0, int(math.floor((rect.x0 - x0) / dx)))
        i1 = min(nx, int(math.ceil((rect.x1 - x0) / dx)))
        j0 = max(0, int(math.floor((rect.y0 - y0) / dy)))
        j1 = min(ny, int(math.ceil((rect.y1 - y0) / dy)))
        for j in range(j0, j1):
            cy = y0 + (j + 0.5) * dy
            if not (rect.y0 - _EPS <= cy <= rect.y1 + _EPS):
                continue
            for i in range(i0, i1):
                cx = x0 + (i + 0.5) * dx
                if rect.x0 - _EPS <= cx <= rect.x1 + _EPS:
                    mask[j * nx + i] = value

    mask = bytearray(nx * ny)
    for rect in positives:
        fill(mask, rect, 1)
    for rect in negatives:
        fill(mask, rect, 0)

    solid = [index for index, value in enumerate(mask) if value]
    if not solid:
        return False
    seen = bytearray(nx * ny)
    seen[solid[0]] = 1
    stack = [solid[0]]
    reached = 1
    while stack:
        index = stack.pop()
        j, i = divmod(index, nx)
        for ni, nj in ((i - 1, j), (i + 1, j), (i, j - 1), (i, j + 1)):
            if not (0 <= ni < nx and 0 <= nj < ny):
                continue
            neighbour = nj * nx + ni
            if mask[neighbour] and not seen[neighbour]:
                seen[neighbour] = 1
                reached += 1
                stack.append(neighbour)
    return reached == len(solid)


# -- the entry point -----------------------------------------------------


def well_mounts(
    config,
    budget,
    *,
    cutouts=(),
    obstacles=(),
    plate_origin: tuple[float, float] | None = None,
    seam_far: float | None = None,
) -> WellMounts:
    """Derive the plate's boss stations, ears and forced notches (mm).

    Parameters
    ----------
    config : Config
        Supplies the fastener surfaces (``merged_boss.bore_margin``,
        ``chassis_joint.boss_margin``), the shell clearance, the printable
        minimum feature, the keyboard's mounting screw and the Section splits.
    budget : SlideBudget
        Supplies the derived Well/plate (``budget.well``), the chassis plan
        (``chassis_height``, ``chassis_top``), the band joint
        (``budget.chassis_joint``) and the bearing-clamp seats
        (``clamp_width``, ``rod_x``, ``clamp_center_y``). Duck-typed, so this
        module stays free of the ``components`` package.
    cutouts : sequence of PlanRect
        The plate's own openings (switch/stabilizer cutouts), plate-local. They
        are checked against the ears and kept out of the connectivity raster.
    obstacles : sequence of Obstacle
        Extra chassis features to keep clear of, in plan coordinates.
    plate_origin : (x, y), optional
        The plate's centre in the chassis plan; defaults to the derived Well
        position (the keyboard is the datum and sits on the X centreline).
    seam_far : float, optional
        How far the plate's own Seam sweeps from the centreline, overriding the
        Section-split derivation.
    """
    well = budget.well
    joint = budget.chassis_joint
    wall = well.ring
    plate_top = well.plate_top
    plate_bottom = well.plate_bottom
    plate_thickness = well.plate_thickness
    minimum = config.material.minimum_feature
    clearance = config.clearance.shell

    screw_name = _screw_size(config)
    insert = fasteners.heat_insert(screw_name)
    bolt = fasteners.screw(screw_name)
    bore_margin = config.merged_boss.bore_margin
    boss_margin = config.chassis_joint.boss_margin

    # One source for the boss: the bore plus the print margin on both sides.
    hole = insert.printed_hole_diameter
    boss_diameter = hole + 2.0 * boss_margin
    boss_height = insert.depth + boss_margin
    # The station sits as close to the ring as the bore allows, so the boss
    # merges into the ring's outer face instead of floating in the lip.
    station_out = bore_margin + hole / 2.0
    # The ring-width border cannot hold the clearance hole with its edge margin,
    # hence the ear: the tab reaches one (hole radius + margin) past the station.
    clearance_hole = bolt.clearance
    ear_half = clearance_hole / 2.0 + boss_margin
    ear_protrusion = station_out + ear_half
    ear_overlap = ear_half - station_out
    corner_radius = _plate_corner_radius(config)
    ear_fillet = min(corner_radius, ear_half) if corner_radius > 0.0 else None
    lip_required = bore_margin + hole + boss_margin

    # The Seam runs between the Sections; no station, bore or ear may sit in it.
    seam = _seam_far(config, seam_far)
    seam_clearance = seam + ear_half + minimum

    width = well.plate_width
    depth = well.plate_depth
    if plate_origin is None:
        front = -budget.chassis_height / 2.0 + well.front_lip + wall
        plate_origin = (0.0, front + depth / 2.0)
    frame = PlateFrame(
        cx=float(plate_origin[0]),
        cy=float(plate_origin[1]),
        width=width,
        depth=depth,
    )
    plate_rect = frame.rect
    plate_half = width / 2.0
    ring_front, ring_rear = plate_rect.y0, plate_rect.y1

    # -- everything the plate must clear --------------------------------
    chassis = _band_station_obstacles(joint) + bearing_seat_obstacles(config, budget)
    chassis += tuple(obstacles)
    sheet_obstacles = [ob for ob in chassis if ob.overlaps_z(plate_bottom, plate_top)]
    boss_obstacles = [
        ob for ob in chassis if ob.overlaps_z(plate_top, plate_top + boss_height)
    ]

    # -- the stations' X -------------------------------------------------
    # The outer stations share one X so the pattern is symmetric front/rear;
    # it is the tightest of the two lips. The Seam stations take the tightest
    # Seam-clear X. Both are walked inboard past anything in their lip band.
    # The clearance walk uses the wider of the boss and the ear: the boss may
    # be the one that reaches a band column first.
    station_half = max(boss_diameter / 2.0, ear_half)

    def outer_limit(station_y: float) -> float:
        band = (
            station_y - station_half - clearance,
            station_y + station_half + clearance,
        )
        return _inboard_x(
            plate_half - station_half, band, sheet_obstacles, clearance, station_half
        )

    front_y = ring_front - station_out
    rear_y = ring_rear + station_out
    outer_x = min(outer_limit(front_y), outer_limit(rear_y))

    # -- the mounts ------------------------------------------------------
    mounts: list[WellMount] = []
    for side in (-1, 1):
        for station, x, y in (
            ("front-outer", outer_x, front_y),
            ("front-seam", seam_clearance, front_y),
            ("rear-seam", seam_clearance, rear_y),
            ("rear-outer", outer_x, rear_y),
        ):
            reasons: list[str] = []
            sx = side * x
            forward = -1.0 if station.startswith("front") else 1.0
            lip = well.front_lip if forward < 0 else well.rear_lip
            ring_face = ring_front if forward < 0 else ring_rear

            # The lip has to host the boss, with its bore margin to the ring.
            if lip + _EPS < lip_required:
                reasons.append(
                    f"lip: needs {lip_required:.2f} mm, the lip is {lip:.2f} mm"
                )

            # The boss merges into the ring's outer face but must not reach its
            # inner face (the Cutout).
            outboard = forward * (y - ring_face)
            near_inboard = outboard - boss_diameter / 2.0
            far_outboard = outboard + boss_diameter / 2.0
            if not (-wall < near_inboard < 0.0):
                reasons.append(
                    f"ring: the boss' inboard edge sits {near_inboard:.2f} mm off "
                    f"the ring's outer face (it must merge into the "
                    f"{wall:.2f} mm ring, not cross it)"
                )
            if far_outboard > lip + _EPS:
                reasons.append(
                    f"lip: the boss reaches {far_outboard:.2f} mm into a "
                    f"{lip:.2f} mm lip"
                )

            # The Seam must not cut the station, its bore or its ear.
            if abs(sx) - ear_half < seam + minimum - _EPS:
                reasons.append(
                    f"seam: the ear's inner edge at |x|={abs(sx) - ear_half:.2f} mm "
                    f"is inside the {seam + minimum:.2f} mm Seam band"
                )

            # The ear has to stay inside the plate's X envelope and overlap the
            # plate by a printable ligature.
            ear_rect = PlanRect.from_centre(sx, y, 2.0 * ear_half, 2.0 * ear_half)
            ear_local = frame.to_local_rect(ear_rect)
            if ear_local.x0 < -plate_half - _EPS or ear_local.x1 > plate_half + _EPS:
                reasons.append(
                    f"plate: the ear {ear_local.x0:.2f}..{ear_local.x1:.2f} leaves "
                    f"the plate's +/-{plate_half:.2f} mm envelope"
                )
            if ear_overlap < minimum - _EPS:
                reasons.append(
                    f"ear: overlaps the plate by {ear_overlap:.2f} mm, less than "
                    f"the {minimum:.2f} mm printable feature"
                )

            # Nothing may share volume with the boss (it is Deck material) ...
            boss_rect = PlanRect.from_circle(sx, y, boss_diameter)
            for obstacle in boss_obstacles:
                if boss_rect.overlaps(obstacle.rect, clearance):
                    reasons.append(
                        f"clash: boss vs {obstacle.name} "
                        f"(z {obstacle.z0:.2f}-{obstacle.z1:.2f})"
                    )
            # ... nor sit under the plate where the ear has to be.
            for obstacle in sheet_obstacles:
                if ear_rect.overlaps(obstacle.rect, clearance):
                    reasons.append(f"clash: ear vs {obstacle.name}")
            for index, cut in enumerate(cutouts):
                if ear_local.overlaps(cut):
                    reasons.append(f"cutout: ear vs cutout-{index}")

            mounts.append(
                WellMount(
                    station=station,
                    side=side,
                    x=sx,
                    y=y,
                    plate_xy=frame.to_local(sx, y),
                    boss_diameter=boss_diameter,
                    insert_hole_diameter=hole,
                    insert_depth=insert.depth,
                    boss_z0=plate_top,
                    boss_z1=plate_top + boss_height,
                    clearance_hole_diameter=clearance_hole,
                    ear=Ear(
                        rect=ear_local,
                        protrusion=ear_protrusion,
                        overlap=ear_overlap,
                        fillet=ear_fillet,
                        thickness=plate_thickness,
                    ),
                    reasons=tuple(reasons),
                )
            )

    # -- the notches the sheet has to give up ----------------------------
    notches: list[PlateNotch] = []
    for obstacle in sheet_obstacles:
        bite = _footprint_bite(obstacle, plate_rect, minimum)
        if bite is None:
            continue
        local_bite = frame.to_local_rect(bite)
        under_an_ear = any(
            mount.ear is not None and mount.ear.rect.overlaps(local_bite, clearance)
            for mount in mounts
        )
        if under_an_ear:
            # An ear is the whole point of the tab: losing it is a station
            # failure (reported above), never something to notch away.
            continue
        local = frame.to_local_rect(bite.expanded(clearance))
        notches.append(
            PlateNotch(
                rect=local,
                source=obstacle.name,
                obstacle=frame.to_local_rect(obstacle.rect),
                clearance=clearance,
                depth=_notch_depth(local, frame),
                # How deep the feature itself (no air gap) bites into the
                # border: the reach that must not pierce the Well ring.
                intrusion=_notch_depth(local_bite, frame),
            )
        )

    # -- the sheet has to stay one piece ---------------------------------
    connected = _sheet_connected(
        [frame.local_rect] + [m.ear.rect for m in mounts if m.ear is not None],
        [n.rect for n in notches] + list(cutouts),
        minimum,
    )
    failures: list[str] = []
    for mount in mounts:
        failures.extend(f"{mount.name}: {reason}" for reason in mount.reasons)
    for notch in notches:
        if notch.intrusion >= wall - minimum + _EPS:
            failures.append(
                f"{notch.source}: reaches {notch.intrusion:.2f} mm past the ring's "
                f"outer face, leaving less than the {minimum:.2f} mm printable "
                f"feature of the {wall:.2f} mm Well ring"
            )
    if not connected:
        failures.append("structural: the plate sheet is severed by the notches")

    return WellMounts(
        frame=frame,
        mounts=tuple(mounts),
        notches=tuple(notches),
        failures=tuple(failures),
        sheet_connected=connected,
        screw=screw_name,
        boss_diameter=boss_diameter,
        boss_height=boss_height,
        insert_hole_diameter=hole,
        insert_depth=insert.depth,
        clearance_hole_diameter=clearance_hole,
        head_diameter=bolt.head_diameter,
        head_depth=bolt.head_depth,
        bore_margin=bore_margin,
        boss_margin=boss_margin,
        ear_half_width=ear_half,
        ear_protrusion=ear_protrusion,
        ear_fillet=ear_fillet,
        lip_required=lip_required,
        seam_far=seam,
        seam_clearance=seam_clearance,
        plate_width=width,
        plate_depth=depth,
        plate_thickness=plate_thickness,
        plate_bottom=plate_bottom,
        plate_top=plate_top,
        ring=wall,
        front_lip=well.front_lip,
        rear_lip=well.rear_lip,
    )


__all__ = [
    "Ear",
    "Obstacle",
    "PlanRect",
    "PlateFrame",
    "PlateNotch",
    "STATIONS",
    "WellMount",
    "WellMounts",
    "bearing_seat_obstacles",
    "well_mounts",
]
