"""Fastener library.

Single source of truth for screws and heat-set inserts used by the build.

Every value is either a standard dimension or a measured value documented in
the docstring. No magic numbers. Screw sizes are keyed by name in the
:data:`SCREWS` library:

M2 / M2.5 / M3
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Screw:
    """A machine screw used to join case parts.

    Attributes
    ----------
    size : str
        Thread designation, e.g. "M2.5".
    pilot_hole : float
        Drilled/hole diameter for tapping or self-tapping use (mm).
    clearance : float
        Clearance-hole diameter for the shaft (mm).
    head_diameter : float
        Head outer diameter (mm).
    head_depth : float
        Head height / depth (mm).
    length : float
        Typical shaft length used in this build (mm).
    """

    size: str
    pilot_hole: float
    clearance: float
    head_diameter: float
    head_depth: float
    length: float


@dataclass(frozen=True)
class HeatInsert:
    """A brass heat-set insert pressed into a printed boss.

    Attributes
    ----------
    size : str
        Thread designation the insert accepts, e.g. "M2.5".
    outside_diameter : float
        Insert outer diameter (mm).
    depth : float
        Insert length / installed depth (mm).
    hole_clearance : float
        Oversize added to the printed hole diameter relative to the insert
        outside diameter (mm). Config value ``clearance.insert``.
    """

    size: str
    outside_diameter: float
    depth: float
    hole_clearance: float

    @property
    def printed_hole_diameter(self) -> float:
        """Printed boss hole diameter: outside diameter minus clearance (mm)."""
        return self.outside_diameter - self.hole_clearance


@dataclass(frozen=True)
class NutTrap:
    """A hexagonal pocket that captures a nut.

    Attributes
    ----------
    across_flats : float
        Nut width across the flats (mm).
    height : float
        Nut height / pocket depth (mm).
    clearance : float
        Added to the pocket width for a slip fit (mm).
    """

    across_flats: float
    height: float
    clearance: float


@dataclass(frozen=True)
class WasherRecess:
    """A shallow round pocket for a washer under a screw head.

    Attributes
    ----------
    diameter : float
        Recess inner diameter (mm).
    depth : float
        Recess depth (mm).
    """

    diameter: float
    depth: float


@dataclass(frozen=True)
class Countersink:
    """A 90-degree countersink for a flush flat-head machine screw.

    Attributes
    ----------
    diameter : float
        Cone diameter at the surface (mm); slightly larger than the head.
    depth : float
        Axial depth of the cone (mm), i.e. how much material the head occupies.
    """

    diameter: float
    depth: float


# --- Screw library ------------------------------------------------------
# Standard ISO 1207 / metric hardware dimensions.
SCREWS: dict[str, Screw] = {
    "M2": Screw(
        size="M2",
        pilot_hole=1.6,
        clearance=2.2,
        head_diameter=3.8,
        head_depth=2.0,
        length=6.0,
    ),
    "M2.5": Screw(
        size="M2.5",
        pilot_hole=2.0,
        clearance=2.7,
        head_diameter=4.6,
        head_depth=2.5,
        length=8.0,
    ),
    "M3": Screw(
        size="M3",
        pilot_hole=2.4,
        clearance=3.2,
        head_diameter=5.6,
        head_depth=3.0,
        length=10.0,
    ),
    "M4": Screw(
        size="M4",
        pilot_hole=3.3,
        clearance=4.5,
        head_diameter=7.0,
        head_depth=4.0,
        length=8.0,
    ),
}


#: Stock screw lengths per thread size (mm), ISO 4762 / 7380 preferred lengths.
STANDARD_LENGTHS: dict[str, tuple[int, ...]] = {
    "M2": (4, 5, 6, 8, 10, 12, 16),
    "M2.5": (5, 6, 8, 10, 12, 16, 20),
    "M3": (5, 6, 8, 10, 12, 16, 18, 20, 25, 30),
    "M4": (6, 8, 10, 12, 16, 20, 25, 30),
}


#: Nyloc nuts (ISO 10511): across flats and height, with a slip-fit clearance.
NUT_TRAPS: dict[str, NutTrap] = {
    "M3": NutTrap(across_flats=5.5, height=4.0, clearance=0.2),
}

#: Flat washers (ISO 7089): outer diameter and thickness.
WASHERS: dict[str, WasherRecess] = {
    "M3": WasherRecess(diameter=7.0, depth=0.5),
}


#: Flat-head (ISO 10642) countersinks: surface diameter and cone depth, with a
#: 0.2 mm fit allowance on the diameter.
COUNTERSINKS: dict[str, Countersink] = {
    "M2": Countersink(diameter=4.0, depth=0.9),
    "M2.5": Countersink(diameter=5.2, depth=1.3),
    "M3": Countersink(diameter=6.2, depth=1.5),
    "M4": Countersink(diameter=8.4, depth=1.9),
}


def nut_trap(size: str) -> NutTrap:
    """The nyloc nut pocket for ``size``, e.g. ``"M3"``."""
    return NUT_TRAPS[size]


def washer(size: str) -> WasherRecess:
    """The flat washer for ``size`` (``diameter`` outer, ``depth`` thickness)."""
    return WASHERS[size]


def countersink(size: str) -> Countersink:
    """The flush-head countersink for ``size`` (``diameter``, ``depth``)."""
    return COUNTERSINKS[size]


def screw(size: str) -> Screw:
    """Return a :class:`Screw` by its size key, e.g. ``"M2.5"``.

    Raises
    ------
    KeyError
        If the size is not in the library.
    """
    return SCREWS[size]


# --- Heat-insert library ---------------------------------------------------
# Values are standard brass heat-set insert dimensions (M2.5 shown).
HEAT_INSERTS: dict[str, HeatInsert] = {
    "M2": HeatInsert(size="M2", outside_diameter=3.2, depth=3.0, hole_clearance=0.2),
    "M2.5": HeatInsert(
        size="M2.5", outside_diameter=4.0, depth=4.0, hole_clearance=0.2
    ),
    "M3": HeatInsert(size="M3", outside_diameter=4.6, depth=4.0, hole_clearance=0.2),
    "M4": HeatInsert(size="M4", outside_diameter=5.6, depth=4.0, hole_clearance=0.2),  # short
}


def heat_insert(size: str) -> HeatInsert:
    """Return a :class:`HeatInsert` by its size key, e.g. ``"M2.5"``."""
    return HEAT_INSERTS[size]
