"""Fastener library.

Single source of truth for screws, their heads and the heat-set inserts used
by the build.

Every value is either a standard dimension or a measured value documented in
the docstring. No magic numbers. Screw sizes are keyed by name in the
:data:`SCREWS` library (M2 / M2.5 / M3 / M4); each size's heads are keyed by
kind in :data:`HEADS`:

* ``pan`` -- **the default**: ISO 7045 / DIN 7985 pan head with a Phillips
  cross recess, seated in a cylindrical counterbore (``docs/design_spec.md``).
  This is the head every new joint is designed around: an ordinary screw that
  is easy to buy and to drive;
* ``cap`` -- ISO 4762 socket cap / ISO 1207 slotted cheese head silhouette
  (the Rod clamp bores and the Well mounts are sized against it, ADR-0014);
* ``button`` -- ISO 7380-1 button head, a hex-socket head with a domed top:
  the ordinary head the two band joints seat in a recess (ADR-0018).

**No countersunk (flat) heads.** The project does not use them unless a
decision record says so: a 90-degree cone is a fragile printed ceiling, and a
flush pan head in a counterbore does the same job. The band joints' keyhole
recess (ADR-0018) and the Tray's driver-access cones (ADR-0021) are the
documented exceptions, and neither is a countersink in this sense.
"""

from __future__ import annotations

import math
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
    length : float
        Typical shaft length used in this build (mm).
    """

    size: str
    pilot_hole: float
    clearance: float
    length: float


@dataclass(frozen=True)
class Head:
    """A screw head: its outer diameter and height (mm).

    ``kind`` names the standard it was taken from (see :data:`HEADS`).
    """

    kind: str
    diameter: float
    depth: float


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
class SquareNut:
    """A square nut (DIN 562) carried by a printed washer puck.

    Attributes
    ----------
    size : str
        Thread designation.
    across_flats : float
        Width across the flats (mm); it is also the nut's height in plan.
    height : float
        Nut thickness (mm).
    clearance : float
        Added to the pocket width for a slip fit (mm).
    """

    size: str
    across_flats: float
    height: float
    clearance: float

    @property
    def pocket(self) -> float:
        """The square pocket's side that seats the nut (mm)."""
        return self.across_flats + self.clearance


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
class HeadRecess:
    """A counterbored pocket for an ordinary (non-flush) screw head.

    The head seats on a flat annulus ``depth`` below the outer face and the
    pocket lifts back to that face on one side in a ``ramp_run`` long ramp at
    ``ramp_angle`` degrees, so the pocket prints without support and a driver
    reaches the head (ADR-0018). In plan the pocket is a stadium:
    ``pocket_diameter`` across, ``pocket_diameter + ramp_run`` long, the ramp
    pointing away from the nearest wall.

    Attributes
    ----------
    size : str
        Thread designation the recess is sized for.
    head : Head
        The head that seats in it.
    pocket_diameter : float
        Pocket width across the screw axis (mm).
    depth : float
        Pocket depth, outer face to the head's seat (mm).
    seat : float
        Width of the annular seat the head bears on (mm).
    ramp_run : float
        Plan length of the lift-out ramp (mm).
    ramp_angle : float
        Ramp angle from the outer face (degrees); the print overhang limit.
    """

    size: str
    head: Head
    pocket_diameter: float
    depth: float
    seat: float
    ramp_run: float
    ramp_angle: float

    @property
    def pocket_radius(self) -> float:
        """Pocket half-width across the screw axis (mm)."""
        return self.pocket_diameter / 2.0

    @property
    def length(self) -> float:
        """Pocket length along the ramp (mm)."""
        return self.pocket_diameter + self.ramp_run


# --- Screw library ------------------------------------------------------
# Standard metric thread dimensions (ISO 724 clearance holes / ISO 4762 / 7380
# stock lengths).
SCREWS: dict[str, Screw] = {
    "M2": Screw(size="M2", pilot_hole=1.6, clearance=2.2, length=6.0),
    "M2.5": Screw(size="M2.5", pilot_hole=2.0, clearance=2.7, length=8.0),
    "M3": Screw(size="M3", pilot_hole=2.4, clearance=3.2, length=10.0),
    "M4": Screw(size="M4", pilot_hole=3.3, clearance=4.5, length=8.0),
}


#: Head silhouettes per screw size (diameter, height) in mm.
#: ``pan`` is ISO 7045 / DIN 7985 (the default, Phillips drive); ``cap`` is
#: ISO 4762 / ISO 1207; ``button`` is the ISO 7380-1 domed hex-socket head.
HEADS: dict[str, dict[str, Head]] = {
    "M2": {
        "pan": Head("pan", 4.0, 1.6),
        "cap": Head("cap", 3.8, 2.0),
        "button": Head("button", 3.5, 1.3),
    },
    "M2.5": {
        "pan": Head("pan", 5.0, 2.1),
        "cap": Head("cap", 4.6, 2.5),
        "button": Head("button", 4.5, 1.5),
    },
    "M3": {
        "pan": Head("pan", 5.6, 2.4),
        "cap": Head("cap", 5.6, 3.0),
        "button": Head("button", 5.7, 1.65),
    },
    "M4": {
        "pan": Head("pan", 7.0, 3.1),
        "cap": Head("cap", 7.0, 4.0),
        "button": Head("button", 7.6, 2.2),
    },
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

#: Square nuts (DIN 562): across flats and height, with a slip-fit clearance.
#: The accessory rail's stations capture one in a printed washer puck
#: (ADR-0020): 7.0 mm is the DIN 562 M4 dimension, 2.2 mm its thickness.
SQUARE_NUTS: dict[str, SquareNut] = {
    "M4": SquareNut(size="M4", across_flats=7.0, height=2.2, clearance=0.2),
}

#: Flat washers (ISO 7089): outer diameter and thickness.
WASHERS: dict[str, WasherRecess] = {
    "M3": WasherRecess(diameter=7.0, depth=0.5),
}


def nut_trap(size: str) -> NutTrap:
    """The nyloc nut pocket for ``size``, e.g. ``"M3"``."""
    return NUT_TRAPS[size]


def square_nut(size: str) -> SquareNut:
    """The DIN 562 square nut ``size`` captures in a washer puck (ADR-0020)."""
    return SQUARE_NUTS[size]


def washer(size: str) -> WasherRecess:
    """The flat washer for ``size`` (``diameter`` outer, ``depth`` thickness)."""
    return WASHERS[size]


def head(size: str, kind: str = "pan") -> Head:
    """Return the ``kind`` head of ``size``, e.g. ``head("M3", "button")``.

    The default is the ordinary Phillips ``pan`` head (``docs/design_spec.md``).

    Raises
    ------
    KeyError
        If the size or the head kind is not in the library.
    """
    return HEADS[size][kind]


def head_recess(
    size: str,
    kind: str = "button",
    *,
    fit: float = 0.2,
    depth_margin: float = 0.2,
    ramp_angle: float = 45.0,
) -> HeadRecess:
    """Size the counterbored recess that seats the ``kind`` head of ``size``.

    ``fit`` is the radial gap between the head and the pocket wall, so the
    head drops in; ``depth_margin`` is how far the head's top face stays below
    the outer face. The ramp lifts the pocket's ceiling back to the outer face
    at ``ramp_angle`` degrees -- the print overhang limit, so the pocket needs
    no support and the driver reaches the head.

    Raises ``ValueError`` when the fit would close the seat ring, i.e. when
    the head would leave no material for it to bear on.
    """
    screw = SCREWS[size]
    bolt = HEADS[size][kind]
    pocket = bolt.diameter + 2.0 * fit
    seat = (pocket - screw.clearance) / 2.0
    if seat <= 0.0:
        raise ValueError(
            f"the {kind} {size} head needs a Ø{pocket:.2f} pocket but the "
            f"clearance hole is already Ø{screw.clearance:.2f}"
        )
    depth = bolt.depth + depth_margin
    return HeadRecess(
        size=size,
        head=bolt,
        pocket_diameter=pocket,
        depth=depth,
        seat=seat,
        ramp_run=depth / math.tan(math.radians(ramp_angle)),
        ramp_angle=ramp_angle,
    )


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
    # The long M3 insert (Ruthex-style "M3 long", 5 mm class): the same 4.6 mm
    # body, 5 mm deep, so a joint that bolts through a thick part can bury it
    # and still keep a full thread engagement (ADR-0033).
    "M3-long": HeatInsert(
        size="M3-long", outside_diameter=4.6, depth=5.0, hole_clearance=0.2
    ),
    "M4": HeatInsert(size="M4", outside_diameter=5.6, depth=4.0, hole_clearance=0.2),  # short
}


def heat_insert(size: str) -> HeatInsert:
    """Return a :class:`HeatInsert` by its size key, e.g. ``"M2.5"``."""
    return HEAT_INSERTS[size]
