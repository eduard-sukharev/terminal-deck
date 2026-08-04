"""Keyboard switch plate — cyberdeck adapter for the keyboard geometry model.

This is the cyberdeck-side adapter that converts the pure-data
:class:`~keyboard.metadata.KeyboardGeometryModel` into a CadQuery solid
via :mod:`utilities.cq_helpers`.

The plate is independent of the enclosure — it can be cut on FR4 or printed
alone.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from components.base import BoundingBox, Component, Hole
from keyboard import generate_from_file, parse_layout
from keyboard.layout.kle_parser import load_kle


class KeyboardPlate(Component):
    """Cherry-MX switch plate for the 40% layout.

    Reads a KLE layout file and plate configuration, generates the geometry
    model, and builds the CadQuery solid via cq_helpers.
    """

    name = "Keyboard Plate"

    def __init__(self, keyboard: dict[str, Any] | None = None) -> None:
        data = keyboard or {}
        self._layout_source = str(data.get("layout_source", ""))
        self._switch_family = str(data.get("switch_family", "mx_alps"))
        self._stab_family = str(data.get("stabilizer_family", "cherry"))
        plate = data.get("plate", {}) or {}
        self._plate_thickness = float(plate.get("thickness", 1.5))
        self._edge_margin = float(plate.get("edge_margin", 6.0))
        self._corner_radius = float(plate.get("corner_radius", 8.0))
        mounting = data.get("mounting", {}) or {}
        self._screw_diameter = 2.0
        self._screw_edge_offset = float(mounting.get("edge_offset", 5.0))
        self._pitch = float(data.get("pitch", 19.05))

        self._model = None
        self._layout = None

    def _ensure_model(self):
        if self._model is not None:
            return
        if self._layout_source and Path(self._layout_source).is_file():
            self._model = generate_from_file(
                self._layout_source,
                switch_family=self._switch_family,
                stabilizer_family=self._stab_family,
                plate_thickness=self._plate_thickness,
                edge_margin=self._edge_margin,
                corner_radius=self._corner_radius,
                screw_diameter=self._screw_diameter,
                screw_edge_offset=self._screw_edge_offset,
                pitch=self._pitch,
            )
        else:
            rows = load_kle(Path(__file__).resolve().parent.parent / "keyboard" / "layouts" / "jd40.json")
            keys = [key for row in rows for key in row]
            from keyboard import KeyboardLayout
            layout = KeyboardLayout(keys=keys, pitch=self._pitch)
            from keyboard import generate
            self._model = generate(
                layout,
                switch_family=self._switch_family,
                stabilizer_family=self._stab_family,
                plate_thickness=self._plate_thickness,
                edge_margin=self._edge_margin,
                corner_radius=self._corner_radius,
                screw_diameter=self._screw_diameter,
                screw_edge_offset=self._screw_edge_offset,
            )

    def size(self) -> BoundingBox:
        self._ensure_model()
        m = self._model.metadata
        return BoundingBox(m.width, m.height, m.plate_thickness)

    def mounting_holes(self) -> list[Hole]:
        self._ensure_model()
        return [
            Hole(h.x, h.y, h.diameter)
            for h in self._model.mounting_holes
        ]

    @property
    def switch_positions(self) -> list[tuple[float, float]]:
        self._ensure_model()
        return list(self._model.metadata.switch_centers)

    def build(self):
        """Build the plate solid from the geometry model."""
        from utilities import cq_helpers

        cq_helpers.require_cq()
        self._ensure_model()

        plate = cq_helpers.extrude_polygon(
            self._model.plate_outline,
            self._plate_thickness,
            z=self._plate_thickness / 2.0,
        )

        for cut in self._model.switch_cutouts:
            solid = cq_helpers.extrude_polygon(
                cut.vertices, self._plate_thickness + 1.0, cut.x, cut.y,
            )
            plate = plate.cut(solid)

        for cut in self._model.stabilizer_cutouts:
            solid = cq_helpers.extrude_polygon(
                cut.vertices, self._plate_thickness + 1.0, cut.x, cut.y,
            )
            plate = plate.cut(solid)

        for hole in self._model.mounting_holes:
            bore = cq_helpers.cylinder_centered(hole.diameter, self._plate_thickness + 1.0)
            bore = cq_helpers.translate(bore, hole.x, hole.y, 0.0)
            plate = plate.cut(bore)

        return plate
