"""Data models for the keyboard geometry generator.

:class:`KeyboardMetadata` is the public contract consumed by the cyberdeck
enclosure generator. :class:`KeyboardGeometryModel` is the intermediate
representation produced by :func:`keyboard.generate` and consumed by the
:class:`~components.keyboard_plate.KeyboardPlate` adapter.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class KeyboardMetadata:
    """Structured metadata about the generated keyboard plate.

    The enclosure generator reads this without re-measuring CAD geometry.
    """

    width: float
    height: float
    plate_thickness: float
    switch_centers: list[tuple[float, float]] = field(default_factory=list)
    mounting_points: list[tuple[float, float]] = field(default_factory=list)
    bounding_box: tuple[float, float, float] = (0.0, 0.0, 0.0)


@dataclass(frozen=True)
class Cutout:
    """One cutout in the plate: a polygon at a world position."""

    vertices: list[tuple[float, float]]
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0


@dataclass(frozen=True)
class MountingHole:
    """One mounting hole in the plate."""

    x: float
    y: float
    diameter: float


@dataclass(frozen=True)
class KeyboardGeometryModel:
    """Complete intermediate representation of the keyboard plate.

    Pure 2D/2.5D data — no CadQuery objects. The cyberdeck adapter
    (:class:`~components.keyboard_plate.KeyboardPlate`) extrudes these
    polygons into CadQuery solids.
    """

    plate_outline: list[tuple[float, float]]
    switch_cutouts: list[Cutout] = field(default_factory=list)
    stabilizer_cutouts: list[Cutout] = field(default_factory=list)
    mounting_holes: list[MountingHole] = field(default_factory=list)
    metadata: KeyboardMetadata | None = None
