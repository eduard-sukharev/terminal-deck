"""Plate boss stations and ear outlines (ADR-0014).

The keyboard plate hangs under the Deck's Well, screwed flat against the lower
faces of the Well's 2 mm ring from below. This module computes that mounting
pattern in plan, as pure data:

* **eight M2 insert stations** -- four per plate Section: front-outer,
  front-at-Seam, rear-at-Seam, rear-outer, one pair per Seam end and one pair
  at the plate's outer corners. The boss is merged to the ring's *outer* face
  in the front/rear lips, so an M2 bore only needs ``merged_boss.bore_margin``
  towards the ring and ``chassis_joint.boss_margin`` towards the lip's outer
  wall;
* **the at-Seam stations straddle the plate's real Seam** (the row-jogging path
  of ``keyboard.geometry.seam.plate_seam()``): each one sits
  ``seam_clearance`` to its own Section's side of the segment where that end of
  the Seam meets the plate's edge, so the rear pair follows the spacebar row's
  jog instead of assuming the old straight ``x = 0`` cut. Where the chassis
  forces a station inboard (the front lip's band column) it is walked toward
  the Seam and reports the walk -- never silent;
* **ears** -- the plate's ring-width border cannot hold the M2 clearance hole
  with its edge margin, so a filleted tab grows outboard of the ring under each
  station, one plate thickness thick;
* **notches** -- the chassis band joint (ADR-0012) and the bearing-clamp seats
  must not collide with the plate. A chassis feature whose Z span overlaps the
  plate's and whose plan footprint reaches the plate becomes a notch rectangle
  the plate builder cuts out; the plate has to stay one connected sheet
  afterwards, which is checked by rasterising the sheet.

**Two frames, one :class:`PlateFrame`.** The layout places the keyboard (and so
the plate) *rotated* -- the spacebar faces the user, so the plate's own frame
is the point reflection of the chassis plan. Every quantity here is derived in
the chassis (world) plan and converted through the frame exactly once:

* the Well, the Cutout, the chassis obstacles, the band notches and each
  station's ``world_xy`` are the **chassis plan** the Deck builds in;
* the plate's outline, its ears, its notches copy and each station's
  ``plate_xy`` are the **plate-local** frame the keyboard's geometry model
  builds in (centred on the plate);
* the Seam arrives plate-local (that is the keyboard model's frame) and is
  converted into the chassis plan before the at-Seam stations are derived.

Nothing else may compose the 180 deg turn by hand: ``PlateFrame`` is the only
place the two frames meet.

Everything is derived from the configuration, the fastener library, the slide
budget, the plate's Seam and the keyboard's placement -- no dimension is
chosen here. The module is pure data: no CAD import, and no import from the
``components`` or ``case`` packages (the budget and the Well are duck-typed
parameters), so the data layer can size and check the mounts before any solid
exists.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, replace

from geometry.parting import deck_screw
from utilities import fasteners

#: The four stations per plate Section, in the ADR-0014 pattern.
STATIONS: tuple[str, ...] = ("front-outer", "front-seam", "rear-seam", "rear-outer")

#: Tolerance for "surfaces touch but do not overlap" (mm).
_EPS = 1e-9

#: Tolerance for the frame's angle and the placement agreement (mm / deg).
_FRAME_TOL = 1e-6


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
    real chord of the disc instead of its bounding square. ``insert_bore`` is
    the diameter of the heat-set bore inside a *chassis insert boss*: the well
    boss is Deck material above the plate and may fuse with such a boss, so
    only the two bores have to keep printable material between them. The
    chassis features this module derives, and the ``obstacles`` argument, are
    in plan coordinates; ``cutouts`` are plate-local, the frame the plate
    builder works in.
    """

    name: str
    rect: PlanRect
    z0: float
    z1: float
    circle: tuple[float, float, float] | None = None
    insert_bore: float | None = None

    def overlaps_z(self, z0: float, z1: float) -> bool:
        return self.z0 < z1 - _EPS and self.z1 > z0 + _EPS


def _axis_angle(rotation: float) -> tuple[float, float, float]:
    """Snap a Z rotation to the axis-aligned angles, or raise (deg, cos, sin).

    The plate's outline, ears and notches are axis-aligned rectangles and the
    Seam's bands are vertical runs, so the plate may only be placed square to
    the chassis (0/90/180/270 deg). Anything else would silently shear the
    pattern; it is reported instead.
    """
    angle = float(rotation) % 360.0
    for candidate in (0.0, 90.0, 180.0, 270.0, 360.0):
        if abs(angle - candidate) <= _FRAME_TOL:
            angle = candidate % 360.0
            break
    else:
        raise ValueError(
            "the plate frame needs a Z rotation that keeps the plate "
            f"axis-aligned (a multiple of 90 deg), got {rotation!r}"
        )
    cos = math.cos(math.radians(angle))
    sin = math.sin(math.radians(angle))
    return (
        angle,
        0.0 if abs(cos) < _EPS else round(cos),
        0.0 if abs(sin) < _EPS else round(sin),
    )


@dataclass(frozen=True)
class PlateFrame:
    """The plate in the chassis plan: centre, size and Z rotation (mm, deg).

    The single source for both halves: the Deck (T3) positions the Well ring and
    the insert bosses from it, and the plate (T4) builds its outline, ears and
    notches in it, so the two cannot drift apart.

    ``rotation`` is the keyboard placement's Z rotation (local -> world). The
    layout turns the keyboard so its spacebar faces the user, so the plate's own
    centred frame is the point reflection of the chassis plan. Every conversion
    between the two goes through :meth:`local_to_world` / :meth:`world_to_local`
    (or the rectangle versions) -- nothing composes the turn by hand.
    """

    cx: float
    cy: float
    width: float
    depth: float
    rotation: float = 0.0

    def __post_init__(self) -> None:
        if self.width <= 0.0 or self.depth <= 0.0:
            raise ValueError(
                f"the plate frame needs a positive size, got "
                f"{self.width} x {self.depth}"
            )
        angle, cos, sin = _axis_angle(self.rotation)
        object.__setattr__(self, "rotation", angle)
        object.__setattr__(self, "_cos", cos)
        object.__setattr__(self, "_sin", sin)

    @classmethod
    def from_placement(
        cls,
        placement,
        *,
        width: float,
        depth: float,
    ) -> "PlateFrame":
        """The frame of a plate of this size carried by ``placement``.

        ``placement`` is the keyboard's :class:`~layouts.base.Placement`: its
        origin is the plate's centre and its Z rotation is the frame's. That is
        the one fact this module cannot derive from the budget -- the budget
        sizes the plate, the layout places it.
        """
        return cls(
            cx=float(placement.x),
            cy=float(placement.y),
            width=float(width),
            depth=float(depth),
            rotation=float(placement.rotation),
        )

    @property
    def x0(self) -> float:
        return self.rect.x0

    @property
    def x1(self) -> float:
        return self.rect.x1

    @property
    def y0(self) -> float:
        return self.rect.y0

    @property
    def y1(self) -> float:
        return self.rect.y1

    @property
    def rect(self) -> PlanRect:
        """The plate's plan footprint (world axis-aligned bounding rectangle)."""
        return self.local_rect_to_world(self.local_rect)

    @property
    def local_rect(self) -> PlanRect:
        """The plate rectangle in its own centred frame."""
        return PlanRect.from_centre(0.0, 0.0, self.width, self.depth)

    def local_to_world(self, x: float, y: float) -> tuple[float, float]:
        """A plate-local point in the chassis plan."""
        return (
            self.cx + x * self._cos - y * self._sin,
            self.cy + x * self._sin + y * self._cos,
        )

    def world_to_local(self, x: float, y: float) -> tuple[float, float]:
        """A chassis-plan point in the plate's own centred frame."""
        dx, dy = x - self.cx, y - self.cy
        return (dx * self._cos + dy * self._sin, -dx * self._sin + dy * self._cos)

    def local_rect_to_world(self, rect: PlanRect) -> PlanRect:
        """A plate-local rectangle in the chassis plan (exact at 0/90/180/270)."""
        corners = [
            self.local_to_world(x, y)
            for x in (rect.x0, rect.x1)
            for y in (rect.y0, rect.y1)
        ]
        return PlanRect.from_points(corners)

    def world_rect_to_local(self, rect: PlanRect) -> PlanRect:
        """A chassis-plan rectangle in the plate's own centred frame."""
        corners = [
            self.world_to_local(x, y)
            for x in (rect.x0, rect.x1)
            for y in (rect.y0, rect.y1)
        ]
        return PlanRect.from_points(corners)

    # -- the historical names, now the correct maps ----------------------
    def to_local(self, x: float, y: float) -> tuple[float, float]:
        return self.world_to_local(x, y)

    def to_plan(self, x: float, y: float) -> tuple[float, float]:
        return self.local_to_world(x, y)

    def to_local_rect(self, rect: PlanRect) -> PlanRect:
        return self.world_rect_to_local(rect)

    def to_plan_rect(self, rect: PlanRect) -> PlanRect:
        return self.local_rect_to_world(rect)


@dataclass(frozen=True)
class SeamPath:
    """The plate's split Seam as ``(y0, y1, x)`` bands, front to back (mm).

    Coordinates are **plate-local** -- the plate's own centred frame, the same
    one the keyboard's geometry model and the ``cutouts`` argument use, so the
    path does not move when the plate is placed in the chassis. ``RowSeam``
    from :mod:`keyboard.geometry.seam` is the source; any object exposing a
    ``bands`` tuple of that shape (or a bare band sequence) is accepted, which
    keeps this module clear of the keyboard package.

    The Seam's ``x`` is where the split runs inside a row band; the jogs between
    bands are at the row boundaries. A station sits *outside* the plate in Y (in
    the lip), so the ends are read as the first and last bands
    (:attr:`x_low_y`, :attr:`x_high_y`). Those two names say which edge of the
    plate-local frame they mean -- the keyboard's own ``+Y`` is its front (the
    spacebar row), and only the frame says whether that is the chassis' front.
    """

    bands: tuple[tuple[float, float, float], ...]

    def __post_init__(self) -> None:
        if not self.bands:
            raise ValueError("the Seam needs at least one band")
        previous = None
        for y0, y1, _ in self.bands:
            if y1 <= y0:
                raise ValueError(f"Seam band is inside out: y {y0:.2f}..{y1:.2f}")
            if previous is not None and y0 > previous + _EPS:
                raise ValueError(
                    f"Seam band starts at y={y0:.2f}, after the previous one "
                    f"ended at y={previous:.2f} (the path must be continuous)"
                )
            previous = y1

    @classmethod
    def from_seam(cls, seam, depth: float) -> "SeamPath":
        """Normalise a Seam for a plate ``depth`` mm deep.

        Accepts a ``RowSeam`` (or anything with a ``bands`` tuple) and a bare
        sequence of ``(y0, y1, x)`` bands. The keyboard's Seam stops at the key
        rows' extent; the plate is deeper, so the first and last bands are
        stretched to the plate's own edges -- the split runs to the edge,
        exactly as ``RowSeam.segments`` does.
        """
        bands_in = getattr(seam, "bands", seam)
        bands = [list(band) for band in bands_in]
        if not bands:
            raise ValueError("the Seam needs at least one band")
        for band in bands:
            if len(band) != 3:
                raise ValueError(f"a Seam band is (y0, y1, x), not {band!r}")
        bands[0][0] = min(bands[0][0], -depth / 2.0)
        bands[-1][1] = max(bands[-1][1], depth / 2.0)
        return cls(tuple((float(y0), float(y1), float(x)) for y0, y1, x in bands))

    @property
    def x_low_y(self) -> float:
        """Where the Seam leaves the plate's low-Y edge (in this frame's mm)."""
        return self.bands[0][2]

    @property
    def x_high_y(self) -> float:
        """Where the Seam leaves the plate's high-Y edge (in this frame's mm)."""
        return self.bands[-1][2]

    def to_world(self, frame: PlateFrame) -> "SeamPath":
        """This Seam converted into the chassis plan through ``frame``.

        The Seam is a set of vertical runs (constant x, a Y band each), so it
        converts band by band; a 180 deg turn reverses their order and mirrors
        their x. A 90/270 deg frame would make the runs horizontal, which this
        path cannot represent -- it raises rather than guessing.
        """
        if frame.rotation not in (0.0, 180.0):
            raise ValueError(
                "the plate Seam is a set of vertical bands; a "
                f"{frame.rotation:g} deg plate frame would make it horizontal"
            )
        bands = []
        for y0, y1, x in self.bands:
            a = frame.local_to_world(x, y0)
            b = frame.local_to_world(x, y1)
            bands.append((min(a[1], b[1]), max(a[1], b[1]), a[0]))
        bands.sort(key=lambda band: band[0])
        return SeamPath(tuple(bands))

    def x_at(self, y: float) -> float:
        """The Seam's X at plate-local ``y`` (clamped to the end bands)."""
        if y < self.bands[0][0] - _EPS:
            return self.x_low_y
        for y0, y1, x in self.bands:
            if y0 - _EPS <= y <= y1 + _EPS:
                return x
        return self.x_high_y

    def section_at(self, x: float, y: float) -> int:
        """``-1`` left of the Seam at ``y``, ``+1`` right of it (plate-local)."""
        return -1 if x < self.x_at(y) else 1


@dataclass(frozen=True)
class Ear:
    """A filleted tab extending the plate outboard of the Well ring (mm).

    ``rect`` is plate-local and includes the inboard ``overlap`` the union
    needs; ``world_rect`` is the same tab in the chassis plan (the frame the
    Deck reads). The tab reaches past the ring's outer face, which is the
    plate's own edge, by ``rect``'s own outboard extent.
    """

    rect: PlanRect
    world_rect: PlanRect
    overlap: float
    fillet: float | None
    thickness: float


@dataclass(frozen=True)
class WellMount:
    """One M2 insert station under the Well's front or rear lip (mm).

    ``world_xy`` is the station in the chassis plan (the frame the Deck's boss
    is built in); ``plate_xy`` is the same point in the plate's own centred
    frame (the frame the plate's clearance hole is drilled in). The two are one
    point through the frame -- exposing both is what stops the Deck and the
    plate disagreeing. ``side`` is the Section the station belongs to, decided
    by the Seam in the plate's own frame (not by the sign of its X: the
    at-Seam pair straddles a Seam well off the centreline, and the 180 deg
    placement turns that frame over). ``boss_z0``/``boss_z1`` is the boss's
    vertical span: it stands on the plate's top face and merges into the ring's
    outer face. ``reasons`` lists every check that failed; ``adjustments``
    records a station that had to move (and why) -- a station is never moved or
    dropped silently.
    """

    station: str
    side: int
    world_xy: tuple[float, float]
    plate_xy: tuple[float, float]
    boss_diameter: float
    insert_hole_diameter: float
    insert_depth: float
    boss_z0: float
    boss_z1: float
    clearance_hole_diameter: float
    ear: Ear | None
    reasons: tuple[str, ...]
    adjustments: tuple[str, ...] = ()

    @property
    def x(self) -> float:
        """The station's X in the chassis plan (mm)."""
        return self.world_xy[0]

    @property
    def y(self) -> float:
        """The station's Y in the chassis plan (mm)."""
        return self.world_xy[1]

    @property
    def local_x(self) -> float:
        """The clearance hole's X in the plate's own frame (mm)."""
        return self.plate_xy[0]

    @property
    def local_y(self) -> float:
        """The clearance hole's Y in the plate's own frame (mm)."""
        return self.plate_xy[1]

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
        """True for a station in the lip on the chassis plan's -Y side."""
        return self.y < 0.0

    @property
    def plan_rect(self) -> PlanRect:
        """The boss's plan footprint (its disc's bounding square, world)."""
        return PlanRect.from_circle(self.x, self.y, self.boss_diameter)

    @property
    def local_rect(self) -> PlanRect:
        """The boss's plan footprint in the plate's own frame (its bbox)."""
        return PlanRect.from_circle(
            self.local_x, self.local_y, self.boss_diameter
        )

    @property
    def local_bore_rect(self) -> PlanRect:
        """The plate's M2 clearance bore in the plate's own frame (its bbox)."""
        return PlanRect.from_circle(
            self.local_x, self.local_y, self.clearance_hole_diameter
        )

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
        text = (
            f"  {self.name:22s} world=({self.x:8.2f}, {self.y:8.2f}) "
            f"plate=({self.local_x:8.2f}, {self.local_y:8.2f}) "
            f"boss Ø{self.boss_diameter:.2f} {ear} [{state}]"
        )
        for note in self.adjustments:
            text += f"\n      walked: {note}"
        return text


@dataclass(frozen=True)
class PlateNotch:
    """A rectangle the chassis forces the plate to give up (mm).

    ``rect`` is plate-local and ``world_rect`` the same rectangle in the chassis
    plan; ``source`` names the chassis feature that produced it; ``depth`` is
    how far it bites into the sheet from the nearest plate edge, ``intrusion``
    how far the feature itself reaches past the ring's outer face -- the reach
    that must not pierce the ring.
    """

    rect: PlanRect
    world_rect: PlanRect
    source: str
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
    screw_name: str
    screw_length: int
    screw_grip: float
    screw_engagement: float
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
    ear_fillet: float | None
    lip_required: float
    seam_far: float
    seam_clearance: float
    seam_path: SeamPath
    seam_world: SeamPath
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
    def section_counts(self) -> dict[str, int]:
        """Stations per plate Section, as the Seam assigns them."""
        return {
            section: len(mounts) for section, mounts in self.section_mounts.items()
        }

    @property
    def seam_front(self) -> float:
        """Plan X where the plate Seam leaves the plate's world front edge."""
        return self.seam_world.x_low_y

    @property
    def seam_rear(self) -> float:
        """Plan X where the plate Seam leaves the plate's world rear edge."""
        return self.seam_world.x_high_y

    @property
    def seam_local_front(self) -> float:
        """Plate-local X where the Seam leaves the plate's front edge.

        The keyboard's own ``+Y`` is its front (the spacebar row); the plate is
        placed rotated, so that edge is the high-Y end of the plate-local Seam.
        """
        return self.seam_path.x_high_y

    @property
    def seam_local_rear(self) -> float:
        """Plate-local X where the Seam leaves the plate's rear edge (low Y)."""
        return self.seam_path.x_low_y

    @property
    def front_lip_slack(self) -> float:
        """Material the front lip has left beyond what the boss needs (mm)."""
        return self.front_lip - self.lip_required

    @property
    def cutout_rect(self) -> PlanRect:
        """The Well Cutout in plan: the plate inset by the ring on every side."""
        rect = self.frame.rect
        return PlanRect(
            rect.x0 + self.ring,
            rect.y0 + self.ring,
            rect.x1 - self.ring,
            rect.y1 - self.ring,
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
            f"plate mounts: {len(self.mounts)} x {self.screw_name} "
            f"(boss Ø{self.boss_diameter:.2f}, "
            f"insert Ø{self.insert_hole_diameter:.2f} x {self.insert_depth:.1f} "
            f"deep, z {first.boss_z0:.2f}-{first.boss_z1:.2f}; "
            f"screw crosses {self.screw_grip:.2f} mm of plate and engages "
            f"{self.screw_engagement:.2f} mm of the insert) on a "
            f"{self.plate_width:.2f} x {self.plate_depth:.2f} x "
            f"{self.plate_thickness:.1f} plate (ring {self.ring:.2f}, "
            f"front lip {self.front_lip:.2f}, rear lip {self.rear_lip:.2f})",
            f"  plate frame: centre ({self.frame.cx:.2f}, {self.frame.cy:.2f}), "
            f"{self.frame.rotation:g} deg in the chassis plan "
            f"(the keyboard's placement)",
            f"  seam (world): {len(self.seam_world.bands)} band(s) front x="
            f"{self.seam_front:.2f} rear x={self.seam_rear:.2f}; "
            f"seam (plate): front x={self.seam_local_front:.2f} "
            f"rear x={self.seam_local_rear:.2f}; at-Seam stations "
            f"{self.seam_clearance:.2f} off their segment "
            f"(step {self.seam_far:.2f} + ear {self.ear_half_width:.2f} + "
            f"min feature)",
        ]
        lines.extend(mount.summary() for mount in self.mounts)
        counts = self.section_counts
        lines.append(
            f"  sections: left {counts['left']}, right {counts['right']} "
            f"(the Seam decides membership, in the plate's frame)"
        )
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
    """The Tray columns / Deck bosses of the chassis band joint (ADR-0012).

    ``insert_bore`` marks them as chassis insert bosses: the well boss is Deck
    material and may fuse with one, so only the two heat-set bores have to keep
    printable material between them (the plate's *ear* still clears the boss).
    """
    return tuple(
        Obstacle(
            name=f"chassis-joint:{station.kind}@{station.x:.2f},{station.y:.2f}",
            rect=PlanRect.from_circle(station.x, station.y, station.boss),
            z0=joint.band_z0,
            z1=joint.parting_z + joint.boss_height,
            circle=(station.x, station.y, station.boss / 2.0),
            insert_bore=joint.insert_hole,
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


def _seam_far(config) -> float:
    """The stepped Section Seam's lateral jog, as build clearance (mm).

    Every Sectioned part is printed against a stepped Seam (ADR-0003) whose
    jog is configured once; the at-Seam stations keep that jog as slack on top
    of their ear and the printable minimum, so a station never lands in a jog.
    The plate's *split* is its own row-jogging path, not this Seam -- that path
    reaches the stations through :class:`SeamPath` and their own clearance
    check; this is the Section-level allowance shared by every printed part.
    """
    split = config.slide.split
    part = split.get("chassis")
    if part is None:
        return 0.0
    return max(abs(v) for v in part.seams()[0].x_range)


def _blocked_interval(
    obstacle: Obstacle,
    y: float,
    half: float,
    clearance: float,
) -> tuple[float, float] | None:
    """The X range where a tab centred at ``(x, y)`` would touch ``obstacle``.

    The tab is ``2 * half`` wide and ``2 * half`` deep (a square), the obstacle
    is a disc when it carries ``circle`` and its rectangle otherwise. The
    returned interval is where the tab's *centre* may not be: it is empty
    (``None``) when the tab's Y band cannot reach the obstacle at all. Both
    cases are exact -- a disc's chord is used, not its bounding square.
    """
    if obstacle.circle is not None:
        cx, cy, radius = obstacle.circle
        reach = radius + clearance
        # Distance from the disc's centre to the tab's Y band.
        dy = max(0.0, cy - (y + half), (y - half) - cy)
        if dy >= reach - _EPS:
            return None
        half_chord = math.sqrt(max(0.0, reach * reach - dy * dy))
        return (
            cx - half_chord - half,
            cx + half_chord + half,
        )
    rect = obstacle.rect
    if y + half <= rect.y0 - clearance + _EPS or y - half >= rect.y1 + clearance - _EPS:
        return None
    return (
        rect.x0 - clearance - half,
        rect.x1 + clearance + half,
    )


def _walk_x(
    x: float,
    direction: float,
    y: float,
    obstacles,
    half: float,
    clearance: float,
) -> tuple[float, tuple[str, ...]]:
    """Walk ``x`` in ``direction`` until a ``2 * half`` tab at ``y`` is clear.

    A tab that overlaps an obstacle is moved to that obstacle's blocking
    interval in the walk's direction -- the nearest clear position on that
    side, never a jump over a feature. Returns the cleared X and the name of
    every obstacle it had to dodge, so a moved station can report why.
    """
    dodged: list[str] = []
    for _ in range(len(obstacles) + 2):
        hit = None
        for obstacle in obstacles:
            interval = _blocked_interval(obstacle, y, half, clearance)
            if interval is None:
                continue
            lo, hi = interval
            if lo + _EPS < x < hi - _EPS:
                hit = (obstacle, interval)
                break
        if hit is None:
            return x, tuple(dodged)
        obstacle, (lo, hi) = hit
        x = hi if direction > 0.0 else lo
        if obstacle.name not in dodged:
            dodged.append(obstacle.name)
    return x, tuple(dodged)


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


def plate_cutouts(model) -> tuple[PlanRect, ...]:
    """The plate's switch and stabilizer openings as plate-local rectangles.

    ``model`` is the keyboard's geometry model, duck-typed: anything exposing
    ``switch_cutouts``/``stabilizer_cutouts`` lists of cutouts whose ``x``/``y``
    offset a polygon of ``(vx, vy)`` vertices. This is the one conversion from
    the keyboard's cutout polygons to the plan rectangles :func:`well_mounts`
    checks, so the pipeline and the validation pass the same openings.
    """
    rects: list[PlanRect] = []
    cutouts = tuple(getattr(model, "switch_cutouts", ())) + tuple(
        getattr(model, "stabilizer_cutouts", ())
    )
    for cut in cutouts:
        xs = [cut.x + vx for vx, _ in cut.vertices]
        ys = [cut.y + vy for _, vy in cut.vertices]
        rects.append(PlanRect(min(xs), min(ys), max(xs), max(ys)))
    return tuple(rects)


def _resolve_frame(budget, well, frame, placement) -> PlateFrame:
    """The plate frame from the caller, checked against the Well it bears on.

    The budget sizes the plate and derives where its Well must sit (the front
    lip, the ring and the plate's depth from the chassis front); the layout
    places the keyboard, which is the same plate. Passing the placement (or a
    frame built from it) is how the 180 deg turn reaches this module -- the
    frame is never assumed, and a frame that is not over the Well is an error,
    not a silently shifted ring.
    """
    width = well.plate_width
    depth = well.plate_depth
    if frame is None:
        if placement is None:
            raise ValueError(
                "well_mounts needs the plate frame: the keyboard (and its "
                "plate) is placed rotated in the chassis, so pass the "
                "keyboard's placement=<Placement> (or frame=<PlateFrame>); a "
                "zero rotation is not assumed"
            )
        frame = PlateFrame.from_placement(placement, width=width, depth=depth)
    if (
        abs(frame.width - width) > _FRAME_TOL
        or abs(frame.depth - depth) > _FRAME_TOL
    ):
        raise ValueError(
            "the plate frame's size disagrees with the Well's plate: "
            f"{frame.width:.3f} x {frame.depth:.3f} vs {width:.3f} x {depth:.3f}"
        )

    wall = well.ring
    front_wall = -budget.chassis_height / 2.0 + wall
    rear_wall = budget.chassis_height / 2.0 - wall
    front_lip = frame.y0 - front_wall
    rear_lip = rear_wall - frame.y1
    if (
        abs(front_lip - well.front_lip) > _FRAME_TOL
        or abs(rear_lip - well.rear_lip) > _FRAME_TOL
        or abs(frame.cx) > _FRAME_TOL
    ):
        raise ValueError(
            "the plate frame is not over the Well the budget derived: the "
            f"frame at x={frame.cx:.3f}, y={frame.cy:.3f} leaves lips "
            f"{front_lip:.3f}/{rear_lip:.3f} mm, the Well needs the frame on "
            f"the chassis centreplane (x=0) with {well.front_lip:.3f}/"
            f"{well.rear_lip:.3f} mm"
        )
    return frame


def well_mounts(
    config,
    budget,
    *,
    seam=None,
    cutouts=(),
    obstacles=(),
    frame: PlateFrame | None = None,
    placement=None,
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
    seam : RowSeam-like, optional
        The plate's split Seam -- ``keyboard.geometry.seam.plate_seam()``'s
        ``RowSeam`` or any object with the same ``bands`` tuple
        (``(y0, y1, x)``, plate-local). It is converted into the chassis plan
        through the frame before the at-Seam stations are derived, so the
        notches land on the world front lip and each pair straddles the world
        Seam end. Defaults to ``budget.well.seam``, which is how the Deck's
        adapter gets the same path without knowing the keyboard; a Seam is
        never assumed, because the straight ``x = 0`` cut this pattern used to
        assume is exactly the bug this argument exists to prevent.
    cutouts : sequence of PlanRect
        The plate's own openings (switch/stabilizer cutouts), plate-local. They
        are checked against the ears and kept out of the connectivity raster.
    obstacles : sequence of Obstacle
        Extra chassis features to keep clear of, in plan coordinates.
    frame : PlateFrame, optional
        The plate in the chassis plan: its centre, size and Z rotation. This is
        the one place the keyboard's rotation enters; build it with
        :meth:`PlateFrame.from_placement` so the layout is the source.
    placement : Placement-like, optional
        The keyboard's placement, used to build ``frame`` when it is not given
        (``frame`` wins). One of the two is required -- the plate is placed
        rotated, so a default would be the point-reflection bug this module
        had.
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
    # The screw's head seats on the plate's underside and its shank crosses the
    # plate into the insert above: the grip is the plate thickness, and the
    # stock length is derived (never chosen) exactly like the chassis joints.
    screw_grip = plate_thickness
    screw = deck_screw(screw_name, screw_grip)

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
    ear_overlap = ear_half - station_out
    corner_radius = _plate_corner_radius(config)
    ear_fillet = min(corner_radius, ear_half) if corner_radius > 0.0 else None
    # The Well's own derivation of what a merged boss needs in a lip is the
    # single source; re-deriving it here would let the two drift apart.
    lip_required = well.boss_lip_required

    width = well.plate_width
    depth = well.plate_depth
    frame = _resolve_frame(budget, well, frame, placement)
    plate_rect = frame.rect
    plate_half = width / 2.0
    ring_front, ring_rear = plate_rect.y0, plate_rect.y1

    # The Seam runs between the Sections; no station, bore or ear may sit in it.
    # Each at-Seam station keeps one clearance off the segment where its end of
    # the Seam meets the plate's edge: the configured jog allowance (so the pair
    # is never pinched by a step) plus the ear and the printable minimum.
    # The path comes from the caller, or from the Well (the Deck's adapter has
    # no keyboard model, and both halves must place the same stations).
    if seam is None:
        seam = getattr(well, "seam", None)
    if seam is None:
        raise ValueError(
            "well_mounts needs the plate's Seam: pass seam=<RowSeam>, or let "
            "the Well carry it (compute_slide_budget does)"
        )
    seam_path = SeamPath.from_seam(seam, depth)
    # The Seam is plate-local (the keyboard model's frame); the stations are
    # derived in the chassis plan, so convert it once through the same frame.
    seam_world = seam_path.to_world(frame)
    seam_far = _seam_far(config)
    seam_clearance = seam_far + ear_half + minimum

    # -- everything the plate must clear --------------------------------
    chassis = _band_station_obstacles(joint) + bearing_seat_obstacles(config, budget)
    chassis += tuple(obstacles)
    sheet_obstacles = [ob for ob in chassis if ob.overlaps_z(plate_bottom, plate_top)]
    boss_obstacles = [
        ob for ob in chassis if ob.overlaps_z(plate_top, plate_top + boss_height)
    ]

    # -- the stations' X -------------------------------------------------
    # The outer stations share one X so the pattern is symmetric front/rear;
    # it is the tightest of the two lips, walked inboard past anything in their
    # lip band. The clearance walk uses the wider of the boss and the ear: the
    # boss may be the one that reaches a band column first.
    station_half = max(boss_diameter / 2.0, ear_half)

    def outer_limit(station_y: float) -> tuple[float, tuple[str, ...]]:
        return _walk_x(
            plate_half - station_half,
            -1.0,
            station_y,
            sheet_obstacles,
            station_half,
            clearance,
        )

    front_y = ring_front - station_out
    rear_y = ring_rear + station_out
    (front_outer, _), (rear_outer, _) = (
        outer_limit(front_y),
        outer_limit(rear_y),
    )
    outer_x = min(front_outer, rear_outer)

    # Each at-Seam station straddles the segment where its end of the Seam meets
    # the plate's edge, `seam_clearance` from it on its own Section's side (the
    # world Seam ends -- the plate is placed rotated). The outer stations are
    # `None`: they mirror about the centreplane, inboard of the band columns.
    placements = (
        ("front-outer", None, front_y),
        ("front-seam", seam_world.x_low_y, front_y),
        ("rear-seam", seam_world.x_high_y, rear_y),
        ("rear-outer", None, rear_y),
    )

    # -- the mounts ------------------------------------------------------
    mounts: list[WellMount] = []
    for world_side in (-1, 1):
        for station, seam_x, y in placements:
            reasons: list[str] = []
            adjustments: list[str] = []
            if seam_x is None:
                sx = world_side * outer_x
            else:
                nominal = seam_x + world_side * seam_clearance
                # A station the chassis forces inboard is walked *toward* its
                # Seam end (never silently moved, never rebalanced by hand):
                # the nearest clear position is what clamps the Seam end.
                sx, dodged = _walk_x(
                    nominal,
                    1.0 if seam_x > nominal else -1.0,
                    y,
                    sheet_obstacles,
                    ear_half,
                    clearance,
                )
                if dodged:
                    adjustments.append(
                        f"{abs(sx - nominal):.2f} mm toward the Seam "
                        f"(from the nominal {nominal:.2f} at "
                        f"{seam_clearance:.2f} mm off it) to clear "
                        + ", ".join(dodged)
                    )
            forward = -1.0 if station.startswith("front") else 1.0
            lip = well.front_lip if forward < 0 else well.rear_lip
            ring_face = ring_front if forward < 0 else ring_rear

            # Which Section the station lands in: the Seam decides, in the
            # plate's own frame (the 180 deg turn swaps the world's sides). A
            # pair that lands on one Section is reported below, never quietly
            # moved to restore the count.
            local_x, local_y = frame.world_to_local(sx, y)
            seam_line = seam_path.x_at(local_y)
            section = -1 if local_x < seam_line else 1

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

            # The Seam must not cut the plate's own geometry at the station: the
            # ear and the clearance bore stay on their Section's side of the
            # segment by the printable minimum. (The boss is Deck material above
            # the plate -- the plate's Seam does not cut it -- so it is not
            # checked against the split; its *bore* is what the screw follows.)
            ear_rect = PlanRect.from_centre(sx, y, 2.0 * ear_half, 2.0 * ear_half)
            boss_rect = PlanRect.from_circle(sx, y, boss_diameter)
            ear_local = frame.world_rect_to_local(ear_rect)
            bore_local = frame.world_rect_to_local(
                PlanRect.from_circle(sx, y, hole)
            )
            for label, rect in (("ear", ear_local), ("bore", bore_local)):
                gap = (
                    seam_line - rect.x1 if section < 0 else rect.x0 - seam_line
                )
                if gap < minimum - _EPS:
                    reasons.append(
                        f"seam: the {label} sits {gap:.2f} mm from the Seam at "
                        f"x={seam_line:.2f} (needs {minimum:.2f} mm clear, "
                        f"plate frame)"
                    )

            # The ear has to stay inside the plate's X envelope and overlap the
            # plate by a printable ligature.
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

            # Nothing may share volume with the boss (it is Deck material). A
            # chassis *insert* boss is the one exception: it is Deck material
            # too, so the two may fuse -- only their heat-set bores have to keep
            # printable material between them ...
            for obstacle in boss_obstacles:
                if obstacle.insert_bore is not None:
                    distance = math.hypot(
                        sx - obstacle.rect.cx, y - obstacle.rect.cy
                    )
                    bore_gap = distance - (obstacle.insert_bore + hole) / 2.0
                    if bore_gap < minimum - _EPS:
                        reasons.append(
                            f"bore: {bore_gap:.2f} mm to the {obstacle.name} "
                            f"insert bore (needs {minimum:.2f} mm of material)"
                        )
                elif boss_rect.overlaps(obstacle.rect, clearance):
                    reasons.append(
                        f"clash: boss vs {obstacle.name} "
                        f"(z {obstacle.z0:.2f}-{obstacle.z1:.2f})"
                    )
            # ... nor sit under the plate where the ear has to be. The ear is a
            # square tab, so test it against the feature's real footprint (a
            # column's disc, not its bounding square) exactly as the walk does.
            for obstacle in sheet_obstacles:
                interval = _blocked_interval(obstacle, y, ear_half, clearance)
                if interval is not None and interval[0] + _EPS < sx < interval[1] - _EPS:
                    reasons.append(f"clash: ear vs {obstacle.name}")
            for index, cut in enumerate(cutouts):
                if ear_local.overlaps(cut):
                    reasons.append(f"cutout: ear vs cutout-{index}")

            mounts.append(
                WellMount(
                    station=station,
                    side=section,
                    world_xy=(sx, y),
                    plate_xy=(local_x, local_y),
                    boss_diameter=boss_diameter,
                    insert_hole_diameter=hole,
                    insert_depth=insert.depth,
                    boss_z0=plate_top,
                    boss_z1=plate_top + boss_height,
                    clearance_hole_diameter=clearance_hole,
                    ear=Ear(
                        rect=ear_local,
                        world_rect=ear_rect,
                        overlap=ear_overlap,
                        fillet=ear_fillet,
                        thickness=plate_thickness,
                    ),
                    reasons=tuple(reasons),
                    adjustments=tuple(adjustments),
                )
            )

    # -- each pair clamps one Section on each side of its Seam end ----------
    # A Seam that jogs over a station (or a walk that ran through the Seam)
    # would put both members of a pair in one Section: the pattern no longer
    # clamps the Seam there, so say so on both stations.
    for station in STATIONS:
        pair = [m for m in mounts if m.station == station]
        if len(pair) != 2 or pair[0].section == pair[1].section:
            message = (
                f"section: the {station} pair lands in the same Section -- the "
                "Seam does not separate it"
            )
            for index, mount in enumerate(mounts):
                if mount.station == station:
                    mounts[index] = replace(
                        mount, reasons=mount.reasons + (message,)
                    )

    # -- the notches the sheet has to give up ----------------------------
    notches: list[PlateNotch] = []
    for obstacle in sheet_obstacles:
        bite = _footprint_bite(obstacle, plate_rect, minimum)
        if bite is None:
            continue
        local_bite = frame.world_rect_to_local(bite)
        under_an_ear = any(
            mount.ear is not None and mount.ear.rect.overlaps(local_bite, clearance)
            for mount in mounts
        )
        if under_an_ear:
            # An ear is the whole point of the tab: losing it is a station
            # failure (reported above), never something to notch away.
            continue
        world = bite.expanded(clearance)
        local = frame.world_rect_to_local(world)
        notches.append(
            PlateNotch(
                rect=local,
                world_rect=world,
                source=obstacle.name,
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
    # The Well sized the lip for its own bore; if this module sizes a different
    # bore for the same station, one of the two is wrong -- say so loudly.
    if abs(lip_required - (bore_margin + hole + boss_margin)) > 1e-9:
        failures.append(
            f"lip: the Well requires {lip_required:.2f} mm of lip for its bore, "
            f"this pattern needs {bore_margin + hole + boss_margin:.2f} mm"
        )
    for notch in notches:
        if notch.intrusion >= wall - minimum + _EPS:
            failures.append(
                f"{notch.source}: reaches {notch.intrusion:.2f} mm past the ring's "
                f"outer face, leaving less than the {minimum:.2f} mm printable "
                f"feature of the {wall:.2f} mm Well ring"
            )
    if not connected:
        failures.append("structural: the plate sheet is severed by the notches")

    # -- two stations must stay two stations -----------------------------
    # A boss holds one insert: two stations closer than one boss would merge
    # into a single lump of Deck material around two bores. That can only happen
    # when the Seam moves a station onto its neighbour, so it is reported.
    spacing = boss_diameter
    for index, first in enumerate(mounts):
        for second in mounts[index + 1 :]:
            distance = math.hypot(first.x - second.x, first.y - second.y)
            if distance < spacing - _EPS:
                failures.append(
                    f"spacing: {first.name} and {second.name} are only "
                    f"{distance:.2f} mm apart, a boss needs {spacing:.2f} mm"
                )

    # -- four stations per Section, as the Seam divides the plate ---------
    for section in ("left", "right"):
        members = [m for m in mounts if m.section == section]
        if len(members) != len(STATIONS):
            failures.append(
                f"section: the {section} Section gets {len(members)} stations, "
                f"the pattern needs {len(STATIONS)} -- "
                + ", ".join(m.name for m in members)
            )

    return WellMounts(
        frame=frame,
        mounts=tuple(mounts),
        notches=tuple(notches),
        failures=tuple(failures),
        sheet_connected=connected,
        screw=screw_name,
        screw_name=screw.name,
        screw_length=screw.length,
        screw_grip=screw.grip,
        screw_engagement=screw.engagement,
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
        ear_fillet=ear_fillet,
        lip_required=lip_required,
        seam_far=seam_far,
        seam_clearance=seam_clearance,
        seam_path=seam_path,
        seam_world=seam_world,
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
    "SeamPath",
    "WellMount",
    "WellMounts",
    "bearing_seat_obstacles",
    "plate_cutouts",
    "well_mounts",
]
