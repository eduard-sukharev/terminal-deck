"""Configuration loading.

Loads the YAML configuration files under ``config/`` into validated
dataclasses. Every build dimension originates from these files, a measured
component, or calculated geometry — configuration is the source of truth.

Load order
----------
:func:`load_config` merges ``default.yaml`` with the requested topic files
(``display``, ``keyboard``, ``hardware``, ``slide``). Topic files override
defaults for their own section.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

# Default location of the configuration directory relative to this file.
CONFIG_DIR: Path = Path(__file__).resolve().parent.parent / "config"

_TOPIC_FILES: dict[str, str] = {
    "display": "display.yaml",
    "keyboard": "keyboard.yaml",
    "hardware": "hardware.yaml",
    "slide": "slide.yaml",
}

#: Top-level config sections that make up the ``hardware`` topic. Topic files
#: declare these as top-level keys (e.g. ``sbc:`` in ``hardware.yaml``), so the
#: merged dict is filtered by section name. ``driver_board`` lives in
#: ``display.yaml`` but is hardware-adjacent and read as ``config.hardware``.
_HARDWARE_SECTIONS: frozenset[str] = frozenset({
    "sbc",
    "power",
    "storage",
    "io",
    "usb_breakout",
    "heat_inserts",
    "battery",
    "driver_board",
})


@dataclass(frozen=True)
class Wall:
    """Wall thickness, the single parameter everything derives from."""

    thickness: float


@dataclass(frozen=True)
class Corners:
    """45 degree chamfer on the case's visible outer corners (mm).

    The case is chamfer-first (``docs/design_spec.md`` § Edge Treatment):
    outside faces are chopped, never rounded. Fillets are reserved for hidden
    inside joints in :mod:`geometry.edge_treatment`.
    """

    chamfer: float

    def __post_init__(self) -> None:
        if self.chamfer < 0:
            raise ValueError("corners.chamfer must be >= 0")


@dataclass(frozen=True)
class Draft:
    """Draft on the screen lid's X side walls (degrees from vertical).

    The Tray's side walls are **vertical** (ADR-0019): the accessory rail bolts
    to a flat, square face, and a drafted wall would put the rail on a slope.
    The lid keeps its taper -- it widens from its face panel down to the back
    panel, so the two halves are widest where they meet. The front/rear end
    walls stay vertical because the guide span and the rod end clamps are
    pinned to the 140 mm face-height budget; the Tray's end walls leave the
    table with the base taper instead (``chassis_joint.taper_angle``).
    """

    lid: float = 7.0

    def __post_init__(self) -> None:
        if not 0.0 <= self.lid < 45.0:
            raise ValueError("draft.lid must be in [0, 45) degrees")


@dataclass(frozen=True)
class Clearance:
    shell: float
    insert: float
    screw: float
    #: Radial gap around an ordinary screw head in its recess, and how far the
    #: head's top face stays below the part's outer face (ADR-0018).
    head: float = 0.2


@dataclass(frozen=True)
class Display:
    width: float
    height: float
    thickness: float
    diagonal: float = 0.0  # inches, informational
    active_width: float = 0.0  # active area, informational
    active_height: float = 0.0  # active area, informational
    flex: "Flex | None" = None  # panel FPC ribbon


@dataclass(frozen=True)
class Flex:
    width: float  # ribbon width, measured
    thickness: float  # ribbon thickness (TODO: measure)
    stack: float  # flat ribbon stack the FPC guard channel captures (TODO: measure)
    edge_protrusion: float = 0.75  # ribbon stub proud of the panel edge (mm)


@dataclass(frozen=True)
class Bezel:
    inset: float
    recess: float = 0.0


#: The keycap wobble allowance each side of the Well Cutout (mm, ADR-0014):
#: one source for the config default and the parsed ``keyboard.plate.wobble``.
DEFAULT_PLATE_WOBBLE: float = 0.6


@dataclass(frozen=True)
class Keyboard:
    columns: int = 12
    rows: int = 4
    pitch: float = 19.05
    layout: str = "default"
    layout_source: str = ""
    switch_family: str = "mx_alps"
    stabilizer_family: str = "cherry"
    plate: dict[str, float] | None = None
    mounting: dict[str, Any] | None = None
    keycap: dict[str, Any] | None = None
    controller: dict[str, object] | None = None
    #: Keycap wobble allowance each side of the Well Cutout (mm, ADR-0014):
    #: a keycap rocking under switch play must never strike a Well wall.
    #: Single source: ``keyboard.plate.wobble``.
    plate_wobble: float = DEFAULT_PLATE_WOBBLE
    #: Switch plate thickness (mm): ``keyboard.plate.thickness``. The Well's
    #: depth and the plate's Z are measured from it, so it is exposed here
    #: instead of being read out of the raw plate dict by every consumer.
    plate_thickness: float = 1.5

    def __post_init__(self) -> None:
        if self.plate_wobble < 0:
            raise ValueError("keyboard.plate.wobble must be >= 0")
        if self.plate_thickness <= 0:
            raise ValueError("keyboard.plate.thickness must be positive")


@dataclass(frozen=True)
class Screws:
    body: str
    standoff: str
    deck: str = "M3"  # Deck screws, driven from below into heat-set inserts


@dataclass(frozen=True)
class Material:
    name: str
    layer_height: float
    minimum_feature: float
    min_bed_face_area: float = 100.0  # smallest flat bed face a Section may print on (mm^2)


@dataclass(frozen=True)
class Seam:
    """One Seam line between two adjacent Sections (ADR 0015).

    A Seam is a plan path, not a single X: a sequence of straight runs with
    one X per Y band, joined by jogs. ``bands`` holds ``(y0, y1, x)`` per run,
    front to back (increasing Y). Two consecutive runs either share their Y
    boundary (a square step) or are separated by a gap the path crosses
    diagonally -- the gap makes a 45 degree jog when its Y length equals its
    X travel, which is what :class:`Split`'s ``trapezoid`` style builds.

    The first and last bands are stretched to the part's own Y extent by
    :meth:`segments` and :meth:`polyline`, so a Seam is written for the shell's
    depth and still cuts a part that is a hair deeper. Nothing here assumes the
    Seam is near the centreline: each Section is a real piece with its own
    fastening, and the two Seams of a screwed pair are deliberately staggered.
    """

    bands: tuple[tuple[float, float, float], ...]

    @classmethod
    def straight(cls, x: float = 0.0) -> "Seam":
        """A Seam that runs straight along Y at ``x``, whatever the depth."""
        return cls(((0.0, 1.0, x),))

    @classmethod
    def stepped(
        cls, x: float, step: float, steps: int, depth: float
    ) -> "Seam":
        """A square-stepped Seam across a part ``depth`` mm deep.

        ``steps`` runs alternate between ``x`` and ``x + step``; the jogs are
        at right angles (ADR 0003's older shape, kept for tests and for parts
        that do not need the trapezoid).
        """
        if steps < 1:
            raise ValueError("a stepped Seam needs steps >= 1")
        seg = depth / steps
        return cls(tuple(
            (-depth / 2.0 + i * seg, -depth / 2.0 + (i + 1) * seg,
             x + (step if i % 2 else 0.0))
            for i in range(steps)
        ))

    def __post_init__(self) -> None:
        if not self.bands:
            raise ValueError("a Seam needs at least one band")
        previous = None
        for y0, y1, _ in self.bands:
            if y1 <= y0:
                raise ValueError(f"Seam band is inside out: y {y0:.2f}..{y1:.2f}")
            if previous is not None and y0 < previous - 1e-9:
                raise ValueError(
                    f"Seam band starts at y={y0:.2f}, before the previous one "
                    f"ended at {previous:.2f} (the path must run front to back)"
                )
            previous = y1

    def segments(self, depth: float) -> list[tuple[float, float, float]]:
        """``(y0, y1, x)`` per straight run, stretched to ``depth``.

        The stretch only moves the outer ends: the jog positions are what the
        Seam is for and never move with the depth.
        """
        bands = [list(band) for band in self.bands]
        bands[0][0] = min(bands[0][0], -depth / 2.0)
        bands[-1][1] = max(bands[-1][1], depth / 2.0)
        return [tuple((float(a), float(b), float(c))) for a, b, c in bands]

    def polyline(self, depth: float) -> list[tuple[float, float]]:
        """The plan path as ``(x, y)`` corners, front to back.

        Each straight run contributes its two ends; the segment between one
        run's end and the next run's start is the jog itself.
        """
        points: list[tuple[float, float]] = []
        for y0, y1, x in self.segments(depth):
            for point in ((x, y0), (x, y1)):
                if not points or point != points[-1]:
                    points.append(point)
        return points

    def x_at(self, y: float) -> float:
        """The Seam's X at ``y``, interpolating across a diagonal jog."""
        bands = self.bands
        if y <= bands[0][1]:
            return bands[0][2]
        for y0, y1, x in bands:
            if y0 <= y <= y1:
                return x
        for (_, ya, xa), (yb, _, xb) in zip(bands, bands[1:]):
            if ya <= y <= yb:
                return xa + (xb - xa) * (y - ya) / (yb - ya)
        return bands[-1][2]

    @property
    def x_range(self) -> tuple[float, float]:
        """X interval the Seam sweeps across."""
        xs = [x for _, _, x in self.bands]
        return (min(xs), max(xs))


#: Section names, left to right, by Section count.
SECTION_NAMES: dict[int, tuple[str, ...]] = {
    2: ("left", "right"),
    3: ("left", "center", "right"),
}


@dataclass(frozen=True)
class Split:
    """How one part is divided into Sections (ADR 0015).

    Two Sections have one Seam; three have two, mirrored about the centreline
    (the left one jogs left, the right one right, away from the centreline).

    ``style`` is the Seam's shape in plan:

    * ``"straight"`` -- one run at ``x``;
    * ``"stepped"`` -- ``steps`` runs along Y, alternating between ``x`` and
      ``x + step``; every jog is square;
    * ``"trapezoid"`` -- a run at ``x`` across the middle, stepping out to
      ``ends_x`` at each end wall, the jogs running at ``jog`` degrees (45 by
      default). This is the shape that lets two Seams of a screwed pair stay
      apart along their whole length: the parts interlock instead of meeting
      along one line.

    :meth:`seams` needs the part's Y depth (and, for a trapezoid, the end
    wall thickness) because a trapezoid's jog positions depend on where the
    end walls are.
    """

    sections: int = 2
    x: float = 0.0
    style: str = "straight"
    step: float = 0.0
    steps: int = 1
    ends_x: float | None = None
    jog: float = 45.0

    def __post_init__(self) -> None:
        if self.sections not in SECTION_NAMES:
            raise ValueError(f"split sections must be 2 or 3, got {self.sections}")
        if self.style == "straight":
            if self.step != 0.0 or self.steps != 1 or self.ends_x is not None:
                raise ValueError("a straight split takes no step/steps/ends_x")
        elif self.style == "stepped":
            if self.step <= 0.0 or self.steps < 2:
                raise ValueError("a stepped split needs step > 0 and steps >= 2")
            if self.ends_x is not None:
                raise ValueError("a stepped split takes no ends_x")
        elif self.style == "trapezoid":
            if self.ends_x is None:
                raise ValueError("a trapezoid split needs ends_x")
            if abs(self.ends_x - self.x) < 1e-9:
                raise ValueError("a trapezoid split needs ends_x different from x")
            if not 0.0 < self.jog < 90.0:
                raise ValueError("a trapezoid split needs 0 < jog < 90 degrees")
            if self.step != 0.0 or self.steps != 1:
                raise ValueError("a trapezoid split takes no step/steps")
        else:
            raise ValueError(
                f"split style must be 'straight', 'stepped' or 'trapezoid', "
                f"got {self.style!r}"
            )

    @property
    def section_names(self) -> tuple[str, ...]:
        return SECTION_NAMES[self.sections]

    @property
    def x_range(self) -> tuple[float, float]:
        """X interval the Seam path sweeps across (independent of depth)."""
        if self.sections == 2:
            xs = [self.x]
            if self.style == "trapezoid":
                xs.append(self.ends_x)
            elif self.style == "stepped":
                xs.append(self.x + self.step)
            return (min(xs), max(xs))
        edge = abs(self.x)
        if self.style == "trapezoid":
            far = abs(self.ends_x)
        elif self.style == "stepped":
            far = edge + self.step
        else:
            far = edge
        return (-far, far)

    def seams(
        self, depth: float | None = None, wall: float = 0.0
    ) -> list[Seam]:
        """The Seams, left to right (one fewer than the Sections).

        ``depth`` is the part's Y extent; ``wall`` the end wall thickness that
        a trapezoid's diagonal starts at.
        """
        if self.sections == 2:
            return [self._seam(self.x, self.ends_x, depth, wall)]
        edge = abs(self.x)
        if self.style == "trapezoid":
            far = abs(self.ends_x)
        elif self.style == "stepped":
            far = edge + self.step
        else:
            far = edge
        # Mirror the path about the centreline: the left Seam jogs left, the
        # right one right, so the middle Section is the widest one.
        return [
            self._seam(-edge, -far if self.ends_x is not None else None, depth, wall),
            self._seam(edge, far if self.ends_x is not None else None, depth, wall),
        ]

    def _seam(
        self,
        x: float,
        ends_x: float | None,
        depth: float | None,
        wall: float,
    ) -> Seam:
        """Build the Seam path for one of the runs (``x`` is this Seam's own)."""
        if self.style == "straight":
            return Seam.straight(x)
        if depth is None or depth <= 0.0:
            raise ValueError(f"a {self.style} Seam needs the part's depth")
        half = depth / 2.0
        if self.style == "stepped":
            # Three Sections mirror about the centreline: the left Seam jogs
            # left, the right one right. A two-Section Seam always takes +step.
            signed = -self.step if (self.sections == 3 and x < 0.0) else self.step
            return Seam.stepped(x, signed, self.steps, depth)
        # Five segments front to back -- end run, 45 degree jog, middle run,
        # 45 degree jog, end run -- with the three straight runs in the ratio
        # 1.5 : 3 : 1.5. The jogs are not square steps: each is a diagonal the
        # path crosses over a gap, so its Y span equals its X travel (45 deg).
        run = abs(ends_x - x) / math.tan(math.radians(self.jog))
        straight = depth - 2.0 * run      # Y left for the three straight runs
        if straight <= 0.0:
            raise ValueError(
                f"trapezoid Seam jogs eat the whole depth: ends_x {ends_x:g}, "
                f"x {x:g}, jog {self.jog:g} deg needs {run:.2f} mm per end"
            )
        end_run = max(1.5 * straight / 6.0, wall)
        middle = straight - 2.0 * end_run
        if middle <= 0.0:
            raise ValueError(
                f"trapezoid Seam leaves no middle run: ends_x {ends_x:g}, x {x:g}, "
                f"jog {self.jog:g} deg leaves {straight:.2f} mm for the runs"
            )
        # Gaps between the bands are the jogs; x_at interpolates across them.
        return Seam((
            (-half, -half + end_run, ends_x),
            (-half + end_run + run, half - end_run - run, x),
            (half - end_run, half, ends_x),
        ))


@dataclass(frozen=True)
class Parting:
    """Where the Deck meets the Tray (ADR 0003).

    The Parting plane sits at ``front_wall_fraction`` of the front wall
    height, clamped to ``[min, max]`` mm, so it adapts to the keyboard stack
    but never degenerates in extreme configs.
    """

    front_wall_fraction: float = 0.5
    min: float = 10.0
    max: float = 20.0

    def __post_init__(self) -> None:
        if not 0.0 < self.front_wall_fraction < 1.0:
            raise ValueError("parting.front_wall_fraction must be between 0 and 1")
        if not 0.0 < self.min <= self.max:
            raise ValueError("parting needs 0 < min <= max")


@dataclass(frozen=True)
class ChassisJoint:
    """The chassis Tray <-> Deck band joint (ADR-0012).

    The chassis splits at the Parting plane. The ``band`` is split evenly
    around it: the Tray is prismatic from its base to the plane (ADR-0019
    removed its X draft) and the Deck is prismatic all the way to the closed
    face. Twelve M3 screws are driven from below into heat-set inserts in the
    Deck's band, each head seated in a keyhole recess in the Tray's floor
    (ADR-0018: ``head`` is the head kind the recess is sized for,
    ``clearance.head`` the fit).

    ``station_inset`` and ``side_inset`` are both measured from a *vertical*
    wall's outer face now: the X walls no longer pull the floor skin inward, so
    a station's margin is a plain plan distance. ``taper_angle`` /
    ``taper_runout`` size the base taper on the vertical front/rear walls
    (ADR-0019): the taper runs from the table up to the band's bottom as a
    draft (the cavity follows, so the wall keeps its thickness) and dies into
    a pad at every station, so no head recess loses its ring and no column
    stands proud of the tapered face.
    """

    band: float = 6.0
    boss: float = 10.0
    boss_margin: float = 1.5
    station_inset: float = 6.5
    side_inset: float = 4.5
    screw: str = "M3"
    head: str = "button"
    taper_angle: float = 15.0
    taper_runout: float = 3.0

    def __post_init__(self) -> None:
        if self.band <= 0 or self.boss <= 0:
            raise ValueError("chassis_joint band and boss must be positive")
        if self.boss_margin <= 0:
            raise ValueError("chassis_joint.boss_margin must be positive")
        if self.station_inset <= 0 or self.side_inset <= 0:
            raise ValueError("chassis_joint insets must be positive")
        if not 0.0 <= self.taper_angle < 45.0:
            raise ValueError("chassis_joint.taper_angle must be in [0, 45) degrees")
        if self.taper_runout <= 0.0:
            raise ValueError("chassis_joint.taper_runout must be positive")


@dataclass(frozen=True)
class MergedBoss:
    """When a boss is fused into the wall beside it (ADR 0003).

    A boss, column, standoff or lug whose outer surface is closer than
    ``threshold_factor * wall`` to a wall face is a Merged boss. Its bore may
    then sit as close as ``bore_margin`` mm to the wall's inner face, so at
    least ``wall + bore_margin`` mm remains between bore and outer skin.
    """

    threshold_factor: float = 2.0
    bore_margin: float = 0.5

    def __post_init__(self) -> None:
        if self.threshold_factor <= 0 or self.bore_margin < 0:
            raise ValueError("merged_boss needs threshold_factor > 0 and bore_margin >= 0")


@dataclass(frozen=True)
class Edges:
    """Edge treatment of concave joints and bed faces (ADR 0003).

    ``chamfer_factor`` scales ``wall.thickness`` into the stress-relief size
    of a concave joint; ``bed_chamfer`` (mm) is the 45 degree chamfer on each
    Section's bed-face outer edge against elephant's foot. Chamfers are the
    default everywhere (including every outside face); the vertical concave
    joints are the only fillets, hidden inside the assembly.
    """

    chamfer_factor: float = 0.5
    bed_chamfer: float = 0.5
    #: How much larger (mm) the convex corner of a Seam step is rounded than
    #: the concave fillet of the notch it fits into, so the two nest.
    seam_convex_extra: float = 0.5

    def __post_init__(self) -> None:
        if self.chamfer_factor < 0 or self.bed_chamfer < 0 or self.seam_convex_extra < 0:
            raise ValueError("edges sizes must be >= 0")


@dataclass(frozen=True)
class SeamPin:
    """A glued filament pin across a Section Seam (ADR 0006).

    Two parallel printed fins straddle the Seam and leave a ``gap``-wide slot
    between them. A length of ``pin`` filament is glued into the slot while the
    part is assembled, so the pin registers the two Sections and holds them
    until the screws that cross the Seam are in.

    The fins are ``fin`` thick, ``height`` tall above the substrate they grow
    from (a floor or a ceiling), and ``length`` long across the Seam --
    ``engagement`` into each Section. The wall thickness is constant; the outer
    base takes a 45 degree ``chamfer`` that flares outward into the substrate.
    The two faces that make the slot stay flat and square, because they locate
    the pin.
    """

    pin: float = 1.75
    gap: float = 2.0
    fin: float = 1.4
    height: float = 2.0
    length: float = 10.0
    chamfer: float = 1.0

    def __post_init__(self) -> None:
        if min(self.pin, self.gap, self.fin, self.height, self.length) <= 0.0:
            raise ValueError("seam_pin dimensions must be positive")
        if self.gap <= self.pin:
            raise ValueError(
                "seam_pin needs a gap wider than the pin, or there is no room "
                "for glue"
            )
        if self.chamfer < 0.0 or self.chamfer >= self.height:
            raise ValueError(
                "seam_pin chamfer must be >= 0 and smaller than the fin height"
            )

    @property
    def engagement(self) -> float:
        """How far one fin reaches into each Section (mm)."""
        return self.length / 2.0

    @property
    def glue_gap(self) -> float:
        """Side-to-side room for glue between the pin and the fins (mm)."""
        return self.gap - self.pin

    @property
    def pocket_width(self) -> float:
        """Depth of the whole pocket across the Seam: two fins plus the slot."""
        return 2.0 * self.fin + self.gap


@dataclass(frozen=True)
class SlideBearing:
    """The purchased LM...LUU linear bushing (one per guide rod).

    ``per_rod`` is part of the face-height budget: a second bearing per rod
    puts the guide span beyond the 140 mm limit. The short LM6UU (19 mm) leaves
    room for the two printed Rod clamps at the rod ends; the long LM6LUU
    (35 mm) does not fit together with them.
    """

    model: str = "LM6UU"
    bore: float = 6.0
    outer_diameter: float = 12.0
    length: float = 19.0
    per_rod: int = 1

    def __post_init__(self) -> None:
        if min(self.bore, self.outer_diameter, self.length) <= 0:
            raise ValueError("slide.bearing dimensions must be positive")
        if self.per_rod < 1:
            raise ValueError("slide.bearing.per_rod must be >= 1")


@dataclass(frozen=True)
class SlideRod:
    """A steel guide rod clamped to the screen lid's back panel."""

    diameter: float = 6.0
    end_support: float = 3.0  # lid material beyond the rod's usable span
    side_margin: float = 2.5  # how far the stance sits inside its tightest bound

    def __post_init__(self) -> None:
        if self.diameter <= 0 or self.end_support < 0:
            raise ValueError("slide.rod needs diameter > 0 and end_support >= 0")
        if self.side_margin < 0:
            raise ValueError("slide.rod.side_margin must be >= 0")


@dataclass(frozen=True)
class FpcGuard:
    """The printed grille plate that guards the display's FPC ribbon.

    The plate is tape-bonded to the display's back with ``total`` thickness:
    a grille floor of ``total - recess`` and a ``recess``-deep channel on the
    display-facing side that captures the flat ribbon (``display.flex.stack``).
    The channel is open at both ends, so the ribbon can leave it toward the
    driver board. ``margin`` is the plan margin the plate keeps beyond the
    ribbon and the slot band the moving Bearing-clamp head sweeps;
    ``sag_allowance`` is the documented deflection allowance between the head's
    crown and the plate's underside.
    """

    total: float = 1.6
    recess: float = 0.6
    margin: float = 5.0
    sag_allowance: float = 0.5
    grille_slot: float = 2.0
    fit: float = 0.4  # clearance to the driver's FPC connector body

    def __post_init__(self) -> None:
        if self.total <= 0 or self.grille_slot <= 0:
            raise ValueError("slide.fpc_guard total/grille_slot must be positive")
        if not 0.0 < self.recess < self.total:
            raise ValueError(
                "slide.fpc_guard.recess must be positive and under total "
                f"(recess {self.recess}, total {self.total})"
            )
        if self.margin < 0 or self.sag_allowance < 0 or self.fit < 0:
            raise ValueError("slide.fpc_guard margins must be >= 0")

    @property
    def floor(self) -> float:
        """The grille floor left between the channel and the plate's underside."""
        return self.total - self.recess


@dataclass(frozen=True)
class RodClamp:
    """A printed clamp holding one end of a Guide rod to the lid back panel.

    Two per rod, one at each end, screwed into the back panel across the rod.
    ``height`` is measured above the back panel's inner face; the rod sits in a
    half-bore on the clamp's underside and in the slot through the panel. The
    screws sit outboard of the slot, in solid panel.
    """

    length: float = 9.0  # grip length along the rod
    height: float = 10.0  # block height above the back panel's inner face
    width: float = 22.0  # block width across the rod (screws outside the slot)
    clearance: float = 0.5  # axial gap between the bearing's extreme and the clamp
    screw: str = "M2"
    screw_span: float = 17.0  # centre distance of the two screws across the rod
    set_screw: str = "M2"  # locks the rod axially in the clamp

    def __post_init__(self) -> None:
        if min(self.length, self.height, self.width, self.screw_span) <= 0:
            raise ValueError("slide.rod_clamp dimensions must be positive")
        if self.clearance < 0:
            raise ValueError("slide.rod_clamp.clearance must be >= 0")


@dataclass(frozen=True)
class BearingClamp:
    """A printed clamp holding a Linear bearing, straddling the lid back panel.

    The body sits inside the lid, above the back panel; the neck passes through
    the back-panel slot and the 1 mm joint gap into a pocket in the chassis
    deck. The head is a cylinder coaxial with the bearing, as wide as the neck
    (no flange): the rod passing through the bearing retains the lid. The clamp
    slides along the slot as the lid moves; its foot is seated in the deck
    pocket with its top face flush with the Deck top, so the neck spans the
    back panel and the joint gap. The foot is longer than the bearing, so the
    two screws land outboard of it. ``corner_chamfer`` breaks the foot's
    vertical corners (the pocket matches); ``top_chamfer`` breaks the exposed
    top perimeter of the foot (matched by the pocket mouth). The cylindrical
    head's rims stay as formed: an arc chamfer is a different, fragile
    operation and a round rim is already print-friendly.
    """

    length: float = 14.0  # grip length along the bearing (the bearing is 35)
    foot_length: float = 30.0  # longer than the bearing: screws land outboard
    foot_thickness: float = 4.0
    seat_wall: float = 2.6  # material around the chassis seat pocket
    seat_floor: float = 2.0
    seat_fit: float = 0.4  # clearance each side of the foot in the pocket
    screw: str = "M2.5"
    screw_span_y: float = 24.0  # wider than the bearing: tips miss the bore
    corner_chamfer: float = 5.0  # vertical corner relief on the foot and pocket
    top_chamfer: float = 0.5  # foot's top perimeter and the pocket mouth

    def __post_init__(self) -> None:
        if min(
            self.length,
            self.foot_length,
            self.foot_thickness,
            self.seat_wall,
            self.seat_floor,
            self.screw_span_y,
        ) <= 0:
            raise ValueError("slide.bearing_clamp dimensions must be positive")
        if self.seat_fit < 0:
            raise ValueError("slide.bearing_clamp.seat_fit must be >= 0")
        if self.corner_chamfer < 0:
            raise ValueError("slide.bearing_clamp chamfers must be >= 0")
        if self.top_chamfer < 0:
            raise ValueError("slide.bearing_clamp.top_chamfer must be >= 0")
        if self.corner_chamfer >= self.foot_length / 2.0:
            raise ValueError(
                "slide.bearing_clamp.corner_chamfer must be under half the "
                "foot length"
            )


@dataclass(frozen=True)
class SlideChain:
    """Drag chain behind the screen, running along the slide axis."""

    pitch: float = 10.0
    width: float = 12.0
    link_height: float = 6.0
    bend_radius: float = 30.0  # must meet the cable's minimum bend radius

    def __post_init__(self) -> None:
        if min(self.pitch, self.width, self.link_height, self.bend_radius) <= 0:
            raise ValueError("slide.chain dimensions must be positive")


@dataclass(frozen=True)
class SlideRail:
    """The accessory rail on the Tray's vertical X walls (ADR-0020).

    Two M4 stations per side, each a local pad with a square pocket for a
    printed washer puck that captures a DIN 562 square nut. The rail itself is
    printed from the same stations: ``width`` is the MIL-STD-1913 rail width
    across the wall (21.2 mm, wider than the Tray's wall, so it overhangs --
    the device stands on its lower edges), ``height`` its thickness off the
    wall, ``pitch`` the slot pitch of the profile that comes later, and
    ``station_spacing`` the distance between the two stations of a side (it
    must be a whole number of pitches, which also lands both stations on the
    profile's bridge centres). ``fit`` is the slip fit of the printed puck in
    its pad pocket; the nut's own fit comes from the fastener library.
    """

    interface: str = "picatinny"
    stations: int = 2
    station_spacing: float = 60.0
    width: float = 21.2
    height: float = 5.0
    pitch: float = 10.0
    screw: str = "M4"
    head: str = "button"
    nut: str = "M4"
    fit: float = 0.2

    def __post_init__(self) -> None:
        if self.stations < 2 or self.stations % 2:
            raise ValueError(
                "slide.rail.stations must be an even number >= 2 (the "
                "stations are mirrored fore and aft of the wall's centre)"
            )
        if min(self.station_spacing, self.width, self.height, self.pitch) <= 0:
            raise ValueError("slide.rail sizes must be positive")
        if self.fit < 0:
            raise ValueError("slide.rail.fit must be >= 0")


@dataclass(frozen=True)
class SlideJoint:
    """The Bezel <-> Back band joint of the screen lid (ADR-0011).

    The lid splits at the Back panel's inner face. The Bezel carries a
    prismatic band whose perimeter wall is locally thickened into posts at the
    ten stations (four corners, two per long side plus one on each long side's
    centreline -- the Section-Seam interlock, ADR-0015); the Back is a flat
    plate with a button-head screw at each station, driven from its outer face
    into the band's insert, its head seated in a keyhole recess (ADR-0018:
    ``head`` is the head kind, ``clearance.head`` the fit).
    """

    band: float = 6.0
    boss: float = 8.0
    boss_margin: float = 1.5
    corner_clearance: float = 0.5
    corner_length: float = 20.0
    station_inset: float = 5.0
    screw: str = "M3"
    head: str = "button"

    def __post_init__(self) -> None:
        if self.band <= 0 or self.boss <= 0:
            raise ValueError("slide.joint sizes must be positive")
        if self.boss_margin <= 0 or self.corner_clearance < 0:
            raise ValueError("slide.joint margins must be positive")
        if self.station_inset <= 0:
            raise ValueError("slide.joint.station_inset must be positive")


@dataclass(frozen=True)
class Slide:
    """Travel, guide and face-height budget of the slider (ADR-0009).

    The closed face height is HARD and is derived, not guessed:
    ``travel + one bearing + end support + lid bezel``. ``travel`` is the
    keyboard's front margin plus its depth plus clearance, because the lid's
    lower edge has to pass the keyboard's *upper* edge when open.

    The front margin (chassis outer front face -> keyboard plate front edge)
    is **not** configured: ADR-0014 derives it from that same face-height
    budget in :func:`components.slide.compute_slide_budget`, because the plate
    grew to bear on the Well ring and the margin is what absorbs the growth.
    """

    face_height_limit: float = 140.0
    travel_clearance: float = 5.0
    clamp_wall: float = 2.0
    top_bezel: float = 2.5
    lid_clearance: float = 1.0
    lid_back: float = 4.0
    lid_front: float = 2.0
    driver_gap: float = 0.5
    component_gap: float = 1.5
    rear_wall_margin: float = 8.0  # SBC clearance to the rear wall
    slot_clearance: float = 0.25  # each side between clamp neck and back-panel slot
    bearing: SlideBearing = field(default_factory=SlideBearing)
    rod: SlideRod = field(default_factory=SlideRod)
    fpc_guard: FpcGuard = field(default_factory=FpcGuard)
    rod_clamp: RodClamp = field(default_factory=RodClamp)
    bearing_clamp: BearingClamp = field(default_factory=BearingClamp)
    joint: SlideJoint = field(default_factory=SlideJoint)
    chain: SlideChain = field(default_factory=SlideChain)
    rail: SlideRail = field(default_factory=SlideRail)
    split: dict[str, Split] = field(default_factory=dict)
    #: Pin-pocket centres along each part's Seam (part-frame Y, mm). ADR-0006:
    #: the fins' substrate and the interior decide where they can go, so these
    #: are placements, like the recipe's ``fixed_position`` entries.
    seam_pin_sites: dict[str, tuple[float, ...]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.face_height_limit <= 0:
            raise ValueError("slide.face_height_limit must be positive")
        if self.travel_clearance < 0:
            raise ValueError("slide.travel_clearance must be >= 0")
        if self.clamp_wall <= 0 or self.top_bezel < 0:
            raise ValueError("slide.clamp_wall must be positive and top_bezel >= 0")
        if self.lid_clearance < 0 or self.lid_back <= 0 or self.lid_front <= 0:
            raise ValueError("slide lid walls must be positive and clearance >= 0")
        if min(self.driver_gap, self.component_gap) < 0:
            raise ValueError("slide gaps must be >= 0")
        if self.rear_wall_margin < 0:
            raise ValueError("slide.rear_wall_margin must be >= 0")
        if self.slot_clearance < 0:
            raise ValueError("slide.slot_clearance must be >= 0")
        for name, sites in self.seam_pin_sites.items():
            if len(set(sites)) != len(sites):
                raise ValueError(
                    f"slide.seam_pin_sites.{name} lists the same Y twice"
                )
            if any(not isinstance(y, float) for y in sites):
                raise ValueError(
                    f"slide.seam_pin_sites.{name} must be a list of Y values"
                )
        if self.rod.diameter > self.bearing.bore + 0.05:
            raise ValueError(
                "slide.rod.diameter must fit the bearing bore "
                f"({self.rod.diameter} > {self.bearing.bore})"
            )
        if self.bearing.outer_diameter <= self.bearing.bore:
            raise ValueError("slide.bearing outer diameter must exceed its bore")

    @property
    def rear_band_clamp(self) -> float:
        """Face-space strip behind the keyboard the guide hardware needs.

        The Bearing clamp sits at the rear end of the rod's travel envelope;
        its seat extends half a seat length further. Expressed without the
        keyboard depth so the layout recipe can use it directly.
        """
        stack = (
            self.bearing.per_rod * self.bearing.length
            + (self.bearing.per_rod - 1) * self.clamp_wall
        )
        seat_length = (
            self.bearing_clamp.foot_length
            + 2.0 * self.bearing_clamp.seat_fit
            + 2.0 * self.bearing_clamp.seat_wall
        )
        return (
            self.rod.end_support
            + self.travel_clearance
            + stack / 2.0
            + self.rod_clamp.length
            + self.rod_clamp.clearance
            + seat_length / 2.0
            + self.clamp_wall / 2.0
        )


@dataclass(frozen=True)
class Config:
    """Fully-resolved build configuration."""

    wall: Wall
    corners: Corners
    clearance: Clearance
    display: Display
    bezel: Bezel
    keyboard: Keyboard
    screws: Screws
    material: Material
    hardware: dict[str, Any] = field(default_factory=dict)
    draft: Draft = field(default_factory=Draft)
    parting: Parting = field(default_factory=Parting)
    chassis_joint: ChassisJoint = field(default_factory=ChassisJoint)
    merged_boss: MergedBoss = field(default_factory=MergedBoss)
    edges: Edges = field(default_factory=Edges)
    seam_pin: SeamPin = field(default_factory=SeamPin)
    slide: Slide = field(default_factory=Slide)
    topics: tuple[str, ...] = field(default_factory=tuple)

    @property
    def wall_thickness(self) -> float:
        """Convenience alias: the single wall-thickness parameter."""
        return self.wall.thickness


def _merge_dict(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    """Deep-merge ``overlay`` into ``base`` (overlay wins)."""
    result = dict(base)
    for key, value in overlay.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _merge_dict(result[key], value)
        else:
            result[key] = value
    return result


def _as_dict(data: dict[str, Any], section: str) -> dict[str, Any]:
    """Return the ``section`` dict from ``data``, requiring it to exist."""
    value = data.get(section)
    if not isinstance(value, dict):
        raise ValueError(f"Config section '{section}' must be a mapping")
    return value


def build_config(raw: dict[str, Any], topics: tuple[str, ...] = ()) -> Config:
    """Construct a :class:`Config` from already-merged YAML data."""
    wall = _as_dict(raw, "wall")
    corners = _as_dict(raw, "corners")
    clearance = _as_dict(raw, "clearance")
    display = _as_dict(raw, "display")
    bezel = _as_dict(raw, "bezel")
    keyboard = _as_dict(raw, "keyboard")
    screws = _as_dict(raw, "screws")
    material = _as_dict(raw, "material")

    slide_raw = raw.get("slide") if isinstance(raw.get("slide"), dict) else {}
    slide_bearing = slide_raw.get("bearing") or {}
    slide_rod = slide_raw.get("rod") or {}
    slide_rod_clamp = slide_raw.get("rod_clamp") or {}
    slide_bearing_clamp = slide_raw.get("bearing_clamp") or {}
    slide_chain = slide_raw.get("chain") or {}
    slide_rail = slide_raw.get("rail") or {}
    slide_joint = slide_raw.get("joint") or {}
    slide_fpc_guard = slide_raw.get("fpc_guard") or {}
    slide_split = {
        name: Split(
            sections=int(v.get("sections", 2)),
            x=float(v.get("x", 0.0)),
            style=str(v.get("style", "straight")),
            step=float(v.get("step", 0.0)),
            steps=int(v.get("steps", 1)),
            ends_x=None if v.get("ends_x") is None else float(v["ends_x"]),
            jog=float(v.get("jog", 45.0)),
        )
        for name, v in (slide_raw.get("split") or {}).items()
    }
    slide = Slide(
        face_height_limit=float(slide_raw.get("face_height_limit", 140.0)),
        travel_clearance=float(slide_raw.get("travel_clearance", 5.0)),
        clamp_wall=float(slide_raw.get("clamp_wall", 2.0)),
        top_bezel=float(slide_raw.get("top_bezel", 2.5)),
        lid_clearance=float(slide_raw.get("lid_clearance", 1.0)),
        lid_back=float(slide_raw.get("lid_back", 4.0)),
        lid_front=float(slide_raw.get("lid_front", 2.0)),
        driver_gap=float(slide_raw.get("driver_gap", 0.5)),
        component_gap=float(slide_raw.get("component_gap", 1.5)),
        rear_wall_margin=float(slide_raw.get("rear_wall_margin", 8.0)),
        slot_clearance=float(slide_raw.get("slot_clearance", 0.25)),
        bearing=SlideBearing(
            model=str(slide_bearing.get("model", "LM6UU")),
            bore=float(slide_bearing.get("bore", 6.0)),
            outer_diameter=float(slide_bearing.get("outer_diameter", 12.0)),
            length=float(slide_bearing.get("length", 19.0)),
            per_rod=int(slide_bearing.get("per_rod", 1)),
        ),
        rod=SlideRod(
            diameter=float(slide_rod.get("diameter", 6.0)),
            end_support=float(slide_rod.get("end_support", 3.0)),
            side_margin=float(slide_rod.get("side_margin", 2.5)),
        ),
        fpc_guard=FpcGuard(
            total=float(slide_fpc_guard.get("total", 1.6)),
            recess=float(slide_fpc_guard.get("recess", 0.6)),
            margin=float(slide_fpc_guard.get("margin", 5.0)),
            sag_allowance=float(slide_fpc_guard.get("sag_allowance", 0.5)),
            grille_slot=float(slide_fpc_guard.get("grille_slot", 2.0)),
            fit=float(slide_fpc_guard.get("fit", 0.4)),
        ),
        rod_clamp=RodClamp(
            length=float(slide_rod_clamp.get("length", 9.0)),
            height=float(slide_rod_clamp.get("height", 10.0)),
            width=float(slide_rod_clamp.get("width", 22.0)),
            clearance=float(slide_rod_clamp.get("clearance", 0.5)),
            screw=str(slide_rod_clamp.get("screw", "M2")),
            screw_span=float(slide_rod_clamp.get("screw_span", 17.0)),
            set_screw=str(slide_rod_clamp.get("set_screw", "M2")),
        ),
        bearing_clamp=BearingClamp(
            length=float(slide_bearing_clamp.get("length", 14.0)),
            foot_length=float(slide_bearing_clamp.get("foot_length", 30.0)),
            foot_thickness=float(slide_bearing_clamp.get("foot_thickness", 4.0)),
            seat_wall=float(slide_bearing_clamp.get("seat_wall", 2.6)),
            seat_floor=float(slide_bearing_clamp.get("seat_floor", 2.0)),
            seat_fit=float(slide_bearing_clamp.get("seat_fit", 0.4)),
            screw=str(slide_bearing_clamp.get("screw", "M2.5")),
            screw_span_y=float(slide_bearing_clamp.get("screw_span_y", 24.0)),
            corner_chamfer=float(slide_bearing_clamp.get("corner_chamfer", 5.0)),
            top_chamfer=float(slide_bearing_clamp.get("top_chamfer", 0.5)),
        ),
        joint=SlideJoint(
            band=float(slide_joint.get("band", 6.0)),
            boss=float(slide_joint.get("boss", 8.0)),
            boss_margin=float(slide_joint.get("boss_margin", 1.5)),
            corner_clearance=float(slide_joint.get("corner_clearance", 0.5)),
            corner_length=float(slide_joint.get("corner_length", 20.0)),
            station_inset=float(slide_joint.get("station_inset", 5.0)),
            screw=str(slide_joint.get("screw", "M3")),
            head=str(slide_joint.get("head", "button")),
        ),
        chain=SlideChain(
            pitch=float(slide_chain.get("pitch", 10.0)),
            width=float(slide_chain.get("width", 12.0)),
            link_height=float(slide_chain.get("link_height", 6.0)),
            bend_radius=float(slide_chain.get("bend_radius", 30.0)),
        ),
        rail=SlideRail(
            interface=str(slide_rail.get("interface", "picatinny")),
            stations=int(slide_rail.get("stations", 2)),
            station_spacing=float(slide_rail.get("station_spacing", 60.0)),
            width=float(slide_rail.get("width", 21.2)),
            height=float(slide_rail.get("height", 5.0)),
            pitch=float(slide_rail.get("pitch", 10.0)),
            screw=str(slide_rail.get("screw", "M4")),
            head=str(slide_rail.get("head", "button")),
            nut=str(slide_rail.get("nut", "M4")),
            fit=float(slide_rail.get("fit", 0.2)),
        ),
        split=slide_split,
        seam_pin_sites={
            name: tuple(float(y) for y in ys)
            for name, ys in (slide_raw.get("seam_pin_sites") or {}).items()
        },
    )
    wall_thickness = float(wall.get("thickness", 2.0))
    if min(slide.clamp_wall, slide.lid_back, slide.lid_front) < wall_thickness:
        raise ValueError(
            "slide walls (clamp_wall, lid_back, lid_front) must be at least "
            f"wall.thickness ({wall_thickness} mm)"
        )

    # Hardware sections are top-level keys in the topic files (``sbc:``,
    # ``driver_board:``, ...). Collect them into ``config.hardware``.
    hardware = {
        key: value
        for key, value in raw.items()
        if key in _HARDWARE_SECTIONS and isinstance(value, dict)
    }

    flex = display.pop("flex", None)
    chassis_joint_raw = raw.get("chassis_joint") or {}
    config = Config(
        wall=Wall(**{k: float(v) for k, v in wall.items()}),
        corners=Corners(**{k: float(v) for k, v in corners.items()}),
        clearance=Clearance(**{k: float(v) for k, v in clearance.items()}),
        display=Display(
            **{k: float(v) for k, v in display.items()},
            flex=Flex(**{k: float(v) for k, v in flex.items()}) if isinstance(flex, dict) else None,
        ),
        bezel=Bezel(**{k: float(v) for k, v in bezel.items()}),
        keyboard=Keyboard(
            columns=int(keyboard.get("columns", 12)),
            rows=int(keyboard.get("rows", 4)),
            pitch=float(keyboard.get("pitch", 19.05)),
            layout=str(keyboard.get("layout", "default")),
            layout_source=str(keyboard.get("layout_source", "")),
            switch_family=str(keyboard.get("switch", {}).get("family", "mx_alps")),
            stabilizer_family=str(keyboard.get("stabilizer", {}).get("family", "cherry")),
            plate=keyboard.get("plate"),
            mounting=keyboard.get("mounting"),
            keycap=keyboard.get("keycap"),
            controller=keyboard.get("controller"),
            plate_wobble=float(
                (keyboard.get("plate") or {}).get("wobble", DEFAULT_PLATE_WOBBLE)
            ),
            plate_thickness=float(
                (keyboard.get("plate") or {}).get("thickness", 1.5)
            ),
        ),
        screws=Screws(
            body=str(screws["body"]), standoff=str(screws["standoff"]),
            deck=str(screws.get("deck", "M3")),
        ),
        material=Material(
            name=str(material["name"]),
            layer_height=float(material["layer_height"]),
            minimum_feature=float(material["minimum_feature"]),
            min_bed_face_area=float(material.get("min_bed_face_area", 100.0)),
        ),
        hardware=hardware,
        draft=Draft(**{k: float(v) for k, v in (raw.get("draft") or {}).items()}),
        parting=Parting(**{k: float(v) for k, v in (raw.get("parting") or {}).items()}),
        chassis_joint=ChassisJoint(
            band=float(chassis_joint_raw.get("band", 6.0)),
            boss=float(chassis_joint_raw.get("boss", 10.0)),
            boss_margin=float(chassis_joint_raw.get("boss_margin", 1.5)),
            station_inset=float(chassis_joint_raw.get("station_inset", 6.5)),
            side_inset=float(chassis_joint_raw.get("side_inset", 4.5)),
            screw=str(chassis_joint_raw.get("screw", "M3")),
            head=str(chassis_joint_raw.get("head", "button")),
            taper_angle=float(chassis_joint_raw.get("taper_angle", 15.0)),
            taper_runout=float(chassis_joint_raw.get("taper_runout", 3.0)),
        ),
        merged_boss=MergedBoss(**{k: float(v) for k, v in (raw.get("merged_boss") or {}).items()}),
        edges=Edges(**{k: float(v) for k, v in (raw.get("edges") or {}).items()}),
        seam_pin=SeamPin(**{k: float(v) for k, v in (raw.get("seam_pin") or {}).items()}),
        slide=slide,
        topics=topics,
    )
    return config


def load_config(
    default_path: Path | str | None = None,
    topics: tuple[str, ...] = ("display", "keyboard", "hardware", "slide"),
) -> Config:
    """Load and merge configuration from disk.

    Parameters
    ----------
    default_path : Path or str, optional
        Path to the default YAML file. Defaults to ``config/default.yaml``.
    topics : tuple[str, ...]
        Topic files to merge on top of the default (see :data:`_TOPIC_FILES`).
        Empty tuple loads the default only.

    Returns
    -------
    Config
        The fully-resolved configuration.
    """
    default_path = Path(default_path or (CONFIG_DIR / "default.yaml")).resolve()

    with open(default_path, "r", encoding="utf-8") as handle:
        merged: dict[str, Any] = yaml.safe_load(handle) or {}

    for topic in topics:
        if topic not in _TOPIC_FILES:
            raise ValueError(f"Unknown configuration topic: {topic!r}")
        topic_path = CONFIG_DIR / _TOPIC_FILES[topic]
        if not topic_path.is_file():
            continue
        with open(topic_path, "r", encoding="utf-8") as handle:
            overlay = yaml.safe_load(handle) or {}
        merged = _merge_dict(merged, overlay)

    return build_config(merged, topics=topics)
