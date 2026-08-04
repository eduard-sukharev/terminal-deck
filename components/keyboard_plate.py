"""Keyboard switch plate — cyberdeck adapter for the keyboard geometry model.

This is the cyberdeck-side adapter that converts the pure-data
:class:`~keyboard.metadata.KeyboardGeometryModel` into a CadQuery solid
via :mod:`utilities.cq_helpers`.

The plate is independent of the enclosure — it can be cut on FR4 or printed
alone.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from components.base import BoundingBox, Component, Hole
from keyboard import generate, parse_layout
from utilities import fasteners


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
        self._screw_size = str(mounting.get("screw", "M2"))
        self._screw_diameter = fasteners.screw(self._screw_size).clearance
        self._screw_edge_offset = float(mounting.get("edge_offset", 5.0))
        self._pitch = float(data.get("pitch", 19.05))

        self._model = None
        self._layout = None

    def _ensure_model(self):
        if self._model is not None:
            return
        if not (self._layout_source and Path(self._layout_source).is_file()):
            raise ValueError(
                f"Keyboard layout file not found: {self._layout_source!r} — "
                "set keyboard.layout_source in the config to a KLE JSON file"
            )
        with open(self._layout_source, "r", encoding="utf-8") as handle:
            raw = json.load(handle)
        self._layout = parse_layout(raw, self._pitch)
        self._model = generate(
            self._layout,
            switch_family=self._switch_family,
            stabilizer_family=self._stab_family,
            plate_thickness=self._plate_thickness,
            edge_margin=self._edge_margin,
            corner_radius=self._corner_radius,
            screw_diameter=self._screw_diameter,
            screw_edge_offset=self._screw_edge_offset,
        )

    def validate(self) -> list[str]:
        """Run the keyboard geometry validation checks.

        Returns
        -------
        list[str]
            Error messages; an empty list means the plate model is valid.
        """
        from keyboard import validate as validate_keyboard

        self._ensure_model()
        return validate_keyboard(
            self._layout,
            self._model,
            self._switch_family,
            self._stab_family,
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

    def mounting_screw(self) -> str:
        """Screw library key for the plate mounting holes (from config)."""
        return self._screw_size

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
