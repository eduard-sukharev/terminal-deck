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
}


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
}


def heat_insert(size: str) -> HeatInsert:
    """Return a :class:`HeatInsert` by its size key, e.g. ``"M2.5"``."""
    return HEAT_INSERTS[size]
