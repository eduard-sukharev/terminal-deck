"""Data models for the keyboard geometry generator.

:class:`KeyboardMetadata` is the public contract consumed by the cyberdeck
enclosure generator. :class:`KeyboardGeometryModel` is the intermediate
representation produced by :func:`keyboard.generate` and consumed by the
:class:`~components.keyboard_plate.KeyboardPlate` adapter.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from keyboard.geometry.seam import RowSeam


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
    #: The Well Cutout ``(x0, y0, x1, y1)`` the plate is derived from (mm).
    cutout: tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)
    #: Switch-free border per side ``(left, right, bottom, top)`` (mm): plate
    #: edge to the outermost switch/stabilizer cutout edge.
    edge_margins: tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)
    #: The keycap row bands ``(y0, y1, x0, x1)`` the plate was stepped from
    #: (plate-local mm), front to back. One band for a rectangular layout.
    row_bands: tuple[tuple[float, float, float, float], ...] = ()
    #: The Well Cutout's stepped outline (plate-local mm), corner-treated.
    cutout_outline: tuple[tuple[float, float], ...] = ()
    #: The plate's plain stepped outline *without* the ears/notches, corner-
    #: treated (its outer corners rounded at ``corner_radius``), plate-local mm.
    plate_outline: tuple[tuple[float, float], ...] = ()
    #: The plate's stepped outline with its corners left **square**, the shape
    #: the Well ring is built from: the ring's structural body must keep the
    #: corner columns' walls square, so the corner rounding stays on the plate's
    #: own outline only (plate-local mm).
    plate_base_outline: tuple[tuple[float, float], ...] = ()
    #: The plate's row bands ``(y0, y1, x0, x1)`` = its Cutout bands + one wall
    #: per side (plate-local mm), the per-band source for the Well's lips.
    plate_bands: tuple[tuple[float, float, float, float], ...] = ()

    @property
    def edge_margin(self) -> float:
        """The narrowest switch-free border (mm) — the plate's bearing rim."""
        return min(self.edge_margins)


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

    Pure 2D/2.5D data — no CAD objects. The cyberdeck adapter
    (:class:`~components.keyboard_plate.KeyboardPlate`) extrudes these
    polygons into solids.
    """

    plate_outline: list[tuple[float, float]]
    switch_cutouts: list[Cutout] = field(default_factory=list)
    stabilizer_cutouts: list[Cutout] = field(default_factory=list)
    mounting_holes: list[MountingHole] = field(default_factory=list)
    metadata: KeyboardMetadata | None = None
    #: Where the plate splits into its two printable Sections: the row-jogging
    #: Seam between key columns (ADR-0003, ADR-0014), never a straight cut
    #: through switch cutouts.
    seam: RowSeam | None = None
    #: The two Section outlines ``(left, right)`` in plate-local mm, clipped
    #: from ``plate_outline`` along :attr:`seam`.
    section_outlines: list[list[tuple[float, float]]] = field(default_factory=list)
