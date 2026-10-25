"""Configuration loading.

Loads the YAML configuration files under ``config/`` into validated
dataclasses. Every build dimension originates from these files, a measured
component, or calculated geometry — configuration is the source of truth.

Load order
----------
:func:`load_config` merges ``default.yaml`` with the requested topic files
(``display``, ``keyboard``, ``hardware``). Topic files override defaults for
their own section.
"""

from __future__ import annotations

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
    "usb_c_plug",
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
    radius: float
    edge_radius: float
    cutout_chamfer: float = 0.5  # lead-in bevel on connector cutout openings


@dataclass(frozen=True)
class Clearance:
    shell: float
    insert: float
    screw: float


@dataclass(frozen=True)
class Deck:
    """Base top deck geometry.

    Attributes
    ----------
    slope : float
        Typing slope in degrees. The deck plane tilts about X so the rear
        (-Y, hinge side) rises while the front edge stays at the flat-case
        deck level, wedging the base. ``0.0`` reproduces the flat deck.
    """

    slope: float = 0.0


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
    fold: float  # folded-ribbon allowance behind panel (TODO: measure)
    edge_protrusion: float = 0.75  # ribbon stub proud of the panel edge (mm)


@dataclass(frozen=True)
class Bezel:
    inset: float
    thickness: float
    seam_screw_offset: float = 10.0  # X distance of the screws beside the centre Seam (mm)
    corner_inset: float = 3.0        # corner screws' distance from the interior wall faces (mm)
    boss_sleeve: float = 1.2         # wall of the insert boss around the insert bore (mm)


@dataclass(frozen=True)
class Glass:
    recess_depth: float


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


@dataclass(frozen=True)
class Hinge:
    """Printed friction hinge (ADR 0004). Lengths in mm along the hinge axis.

    From each end of the span inward: an end cheek, a Lid knuckle, then the
    Base knuckle; ``washer_stack`` separates the rubbing faces. An M3 bolt
    (``friction_bolt``) runs cheek -> Lid knuckle -> Base knuckle land into a
    captive nyloc nut; its head sits under a removable service cap.
    """

    diameter: float               # knuckle outer diameter (>= wire_tunnel + 2 * wall)
    wire_tunnel: float            # display cable tunnel bore through the Base knuckle
    lid_knuckle: float = 20.0     # length of each Lid corner knuckle
    washer_stack: float = 1.2     # steel + spring washer between rubbing faces
    land: float = 8.0             # solid bolt-bearing length at each Base knuckle end
    end_cheek: float = 5.0        # thickness of each outer Base end cheek
    saddle: float = 6.0           # Deck saddle block depth behind the Base knuckle's flat
    fit: float = 0.2              # gap between the Base knuckle and its Deck pocket
    cap_thickness: float = 2.0    # removable service cap head thickness
    cap_plug: float = 4.0         # service cap plug depth into the head recess
    end_inset: float = 9.0        # hinge span inset from each case side
    friction_bolt: str = "M3"     # bolt size (fastener library)
    swing_clearance: float = 0.5  # gap between a swinging knuckle's circle and a fixed part
    side_overrun: float = 1.0     # how far a notch or bore runs past the case side
    head_recess_margin: float = 0.5  # head recess depth beyond the bolt head
    cap_margin: float = 2.0       # service cap diameter inset from the knuckle diameter


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
    """One Seam line between two adjacent Sections (ADR 0003).

    ``x`` is the Seam's base X position; ``step`` the signed jog size (toward
    +X when positive) and ``steps`` the number of segments along Y (``step ==
    0`` is a straight cut).
    """

    x: float = 0.0
    step: float = 0.0
    steps: int = 1

    def __post_init__(self) -> None:
        if self.steps < 1:
            raise ValueError("seam steps must be >= 1")

    def segments(self, depth: float) -> list[tuple[float, float, float]]:
        """``(y0, y1, x)`` per segment, front-to-back across ``depth``."""
        seg = depth / self.steps
        return [
            (-depth / 2 + i * seg, -depth / 2 + (i + 1) * seg,
             self.x + (self.step if i % 2 else 0.0))
            for i in range(self.steps)
        ]

    @property
    def x_range(self) -> tuple[float, float]:
        """X interval the stepped Seam sweeps across."""
        far = self.x + (self.step if self.steps > 1 else 0.0)
        return (min(self.x, far), max(self.x, far))


#: Section names, left to right, by Section count.
SECTION_NAMES: dict[int, tuple[str, ...]] = {
    2: ("left", "right"),
    3: ("left", "center", "right"),
}


@dataclass(frozen=True)
class Split:
    """How one part is divided into Sections (ADR 0003).

    Two Sections have one Seam at ``x``. Three Sections have two Seams at
    ``-|x|`` and ``+|x|``; on stepped Seams the left one jogs left and the
    right one right (away from the centerline), so the pair mirrors about it:
    a step left on one is a step right on the other. ``style`` is ``"straight"`` (one
    segment, no jog) or ``"stepped"`` (``steps`` segments of jog ``step``).
    """

    sections: int = 2
    x: float = 0.0
    style: str = "straight"
    step: float = 0.0
    steps: int = 1

    def __post_init__(self) -> None:
        if self.sections not in SECTION_NAMES:
            raise ValueError(f"split sections must be 2 or 3, got {self.sections}")
        if self.style == "straight":
            if self.step != 0.0 or self.steps != 1:
                raise ValueError("a straight split takes no step/steps")
        elif self.style == "stepped":
            if self.step <= 0.0 or self.steps < 2:
                raise ValueError("a stepped split needs step > 0 and steps >= 2")
        else:
            raise ValueError(f"split style must be 'straight' or 'stepped', got {self.style!r}")

    @property
    def section_names(self) -> tuple[str, ...]:
        return SECTION_NAMES[self.sections]

    def seams(self) -> list[Seam]:
        """The Seams, left to right (one fewer than the Sections)."""
        if self.sections == 2:
            return [Seam(self.x, self.step, self.steps)]
        edge = abs(self.x)
        return [
            Seam(-edge, -self.step, self.steps),
            Seam(edge, self.step, self.steps),
        ]


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
    Section's bed-face outer edge against elephant's foot.
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
    """Glued filament pin through every Seam lug (ADR 0006).

    A length of ``diameter`` filament is pushed through a through-bore of
    ``diameter + fit`` that runs along X across the Seam, glued, and trimmed
    flush. ``engagement`` is the bore length on each side of the Seam and
    ``sleeve`` the lug wall around the bore.
    """

    diameter: float = 1.75
    fit: float = 0.15
    engagement: float = 5.0
    sleeve: float = 1.0

    def __post_init__(self) -> None:
        if min(self.diameter, self.engagement, self.sleeve) <= 0 or self.fit < 0:
            raise ValueError("seam_pin needs positive diameter/engagement/sleeve and fit >= 0")


@dataclass(frozen=True)
class Feet:
    """Round rubber-foot recesses in the Tray floor.

    Positions are inset from the case corners and independent of bosses.
    """

    diameter: float = 15.0
    depth: float = 1.0
    inset_x: float = 15.0
    inset_y: float = 15.0


@dataclass(frozen=True)
class Well:
    """Rim around the keyboard opening in the Deck.

    The rim top sits ``switch_margin`` below the switch tops, so it protects
    the keys without adding closed thickness. Rim width is the wall thickness.
    """

    switch_margin: float = 1.0

    def __post_init__(self) -> None:
        if self.switch_margin < 0:
            raise ValueError("well.switch_margin must be >= 0 (rim may not reach the switch tops)")


@dataclass(frozen=True)
class Config:
    """Fully-resolved build configuration."""

    wall: Wall
    corners: Corners
    clearance: Clearance
    deck: Deck
    display: Display
    bezel: Bezel
    glass: Glass
    keyboard: Keyboard
    hinge: Hinge
    screws: Screws
    material: Material
    hardware: dict[str, Any] = field(default_factory=dict)
    split: dict[str, Split] = field(default_factory=dict)
    parting: Parting = field(default_factory=Parting)
    merged_boss: MergedBoss = field(default_factory=MergedBoss)
    edges: Edges = field(default_factory=Edges)
    seam_pin: SeamPin = field(default_factory=SeamPin)
    feet: Feet = field(default_factory=Feet)
    well: Well = field(default_factory=Well)
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
    # Optional: a recipe/config predating the sloped deck has no `deck:`
    # section and gets slope 0.0, i.e. the original flat geometry.
    deck = raw.get("deck") if isinstance(raw.get("deck"), dict) else {}
    display = _as_dict(raw, "display")
    bezel = _as_dict(raw, "bezel")
    glass = _as_dict(raw, "glass")
    keyboard = _as_dict(raw, "keyboard")
    hinge = _as_dict(raw, "hinge")
    screws = _as_dict(raw, "screws")
    material = _as_dict(raw, "material")

    # Hardware sections are top-level keys in the topic files (``sbc:``,
    # ``driver_board:``, ...). Collect them into ``config.hardware``.
    hardware = {
        key: value
        for key, value in raw.items()
        if key in _HARDWARE_SECTIONS and isinstance(value, dict)
    }

    flex = display.pop("flex", None)
    config = Config(
        wall=Wall(**{k: float(v) for k, v in wall.items()}),
        corners=Corners(**{k: float(v) for k, v in corners.items()}),
        clearance=Clearance(**{k: float(v) for k, v in clearance.items()}),
        deck=Deck(**{k: float(v) for k, v in deck.items()}),
        display=Display(
            **{k: float(v) for k, v in display.items()},
            flex=Flex(**{k: float(v) for k, v in flex.items()}) if isinstance(flex, dict) else None,
        ),
        bezel=Bezel(**{k: float(v) for k, v in bezel.items()}),
        glass=Glass(**{k: float(v) for k, v in glass.items()}),
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
        ),
        hinge=Hinge(**{
            k: (str(v) if k == "friction_bolt" else float(v)) for k, v in hinge.items()
        }),
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
        split={
            part: Split(
                sections=int(v.get("sections", 2)), x=float(v.get("x", 0.0)),
                style=str(v.get("style", "straight")),
                step=float(v.get("step", 0.0)), steps=int(v.get("steps", 1)),
            )
            for part, v in (raw.get("split") or {}).items()
        },
        parting=Parting(**{k: float(v) for k, v in (raw.get("parting") or {}).items()}),
        merged_boss=MergedBoss(**{k: float(v) for k, v in (raw.get("merged_boss") or {}).items()}),
        edges=Edges(**{k: float(v) for k, v in (raw.get("edges") or {}).items()}),
        seam_pin=SeamPin(**{k: float(v) for k, v in (raw.get("seam_pin") or {}).items()}),
        feet=Feet(**{k: float(v) for k, v in (raw.get("feet") or {}).items()}),
        well=Well(**{k: float(v) for k, v in (raw.get("well") or {}).items()}),
        topics=topics,
    )
    return config


def load_config(
    default_path: Path | str | None = None,
    topics: tuple[str, ...] = ("display", "keyboard", "hardware"),
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
