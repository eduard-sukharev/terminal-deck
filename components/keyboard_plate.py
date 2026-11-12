"""Keyboard switch plate — cyberdeck adapter for the keyboard geometry model.

This is the cyberdeck-side adapter that converts the pure-data
:class:`~keyboard.metadata.KeyboardGeometryModel` into a solid
via :mod:`utilities.cad_helpers`.

The plate is **derived** from the Well (ADR-0014): the keyboard package sizes
it as the Well Cutout plus one wall thickness of border on each side, so it
bears on the Well walls' lower faces. There is no margin to tune, and the
plate carries no floor-standoff holes of its own — the enclosure injects the
Well-mount clearance holes via :meth:`set_mounting_holes`.

The plate is independent of the enclosure — it can be cut on FR4 or printed
alone.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from components.base import BoundingBox, Component, Hole
from keyboard import generate, parse_layout
from keyboard.metadata import MountingHole
from utilities import fasteners


class KeyboardPlate(Component):
    """Cherry-MX switch plate for the 40% layout.

    Reads a KLE layout file, the plate configuration, the Well wall thickness
    and the keycap profile, generates the geometry model, and builds the solid
    via cad_helpers.

    The plate's size, Cutout and switch-free border are derived by
    :func:`keyboard.generate` — ``keyboard.plate.edge_margin`` no longer exists.
    Mounting hole positions are injected by the constraint system via
    :meth:`set_mounting_holes`; with none injected the plate is a bare sheet.
    """

    name = "Keyboard Plate"

    def __init__(self, keyboard: dict[str, Any] | None = None) -> None:
        data = keyboard or {}
        self._layout_source = str(data.get("layout_source", ""))
        self._switch_family = str(data.get("switch_family", "mx_alps"))
        self._stab_family = str(data.get("stabilizer_family", "cherry"))
        plate = data.get("plate", {}) or {}
        self._plate_thickness = float(plate.get("thickness", 1.5))
        self._wobble = float(plate.get("wobble", 0.6))
        self._corner_radius = float(plate.get("corner_radius", 2.0))
        if "wall_thickness" not in data:
            raise ValueError(
                "KeyboardPlate needs 'wall_thickness' (the Well ring / plate "
                "border per side, config.wall.thickness) to size the plate"
            )
        self._wall = float(data["wall_thickness"])
        self._keycap_profile = str((data.get("keycap", {}) or {}).get("profile", "xda"))
        mounting = data.get("mounting", {}) or {}
        self._screw_size = str(mounting.get("screw", "M2"))
        self._screw_diameter = fasteners.screw(self._screw_size).clearance
        self._pitch = float(data.get("pitch", 19.05))

        self._model = None
        self._layout = None
        self._mounting_holes: list[MountingHole] = []

    def _ensure_model(self):
        if self._model is not None:
            return
        if not (self._layout_source and Path(self._layout_source).is_file()):
            raise ValueError(
                f"Keyboard layout file not found: {self._layout_source!r} — "
                "set keyboard.layout_source in the config to a KLE JSON file"
            )
        if self._layout is None:
            with open(self._layout_source, "r", encoding="utf-8") as handle:
                raw = json.load(handle)
            self._layout = parse_layout(raw, self._pitch)
        self._model = generate(
            self._layout,
            switch_family=self._switch_family,
            stabilizer_family=self._stab_family,
            plate_thickness=self._plate_thickness,
            wall=self._wall,
            keycap_profile=self._keycap_profile,
            wobble=self._wobble,
            corner_radius=self._corner_radius,
            mounting_holes=self._mounting_holes,
        )

    def validate(self) -> tuple[int, list[str]]:
        """Run the keyboard geometry validation checks.

        Returns
        -------
        tuple[int, list[str]]
            ``(checks_run, errors)`` — number of checks executed and any error
            messages. An empty ``errors`` list means the plate model is valid.
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

    @property
    def cutout(self) -> tuple[float, float, float, float]:
        """The Well Cutout ``(x0, y0, x1, y1)`` the plate is derived from (mm)."""
        self._ensure_model()
        return self._model.metadata.cutout

    @property
    def plate_outline(self) -> list[tuple[float, float]]:
        """The plate outline polygon (mm, plate-local)."""
        self._ensure_model()
        return list(self._model.plate_outline)

    @property
    def edge_margins(self) -> tuple[float, float, float, float]:
        """The derived switch-free border per side ``(left, right, bottom, top)``."""
        self._ensure_model()
        return self._model.metadata.edge_margins

    def set_mounting_holes(self, holes: list[tuple[float, float, float]]) -> None:
        """Set the mounting holes the plate carries (ADR-0014 Well mounts).

        The plate has no holes of its own: the enclosure derives them (the
        Well-mount stations) and injects them here, in plate-local mm.

        Parameters
        ----------
        holes : list[tuple[float, float, float]]
            List of ``(x, y, diameter)`` tuples in mm (plate-local frame).
        """
        self._mounting_holes = [
            MountingHole(float(x), float(y), float(d)) for x, y, d in holes
        ]
        self._model = None  # regenerate with the new holes

    def _get_mounting_holes(self) -> list[tuple[float, float, float]]:
        """Return ``(x, y, diameter)`` tuples the plate is cut with."""
        self._ensure_model()
        return [(h.x, h.y, h.diameter) for h in self._model.mounting_holes]

    def mounting_holes(self) -> list[Hole]:
        return [
            Hole(x, y, d, height=self._plate_thickness)
            for x, y, d in self._get_mounting_holes()
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
        from utilities import cad_helpers

        cad_helpers.require_cad()
        self._ensure_model()

        plate = cad_helpers.extrude_polygon(
            self._model.plate_outline,
            self._plate_thickness,
            z=self._plate_thickness / 2.0,
        )

        for cut in self._model.switch_cutouts:
            solid = cad_helpers.extrude_polygon(
                cut.vertices, self._plate_thickness + 1.0, cut.x, cut.y,
                z=self._plate_thickness / 2.0,
            )
            plate = cad_helpers.cut(plate, solid)

        for cut in self._model.stabilizer_cutouts:
            solid = cad_helpers.extrude_polygon(
                cut.vertices, self._plate_thickness + 1.0, cut.x, cut.y,
                z=self._plate_thickness / 2.0,
            )
            plate = cad_helpers.cut(plate, solid)

        for x, y, d in self._get_mounting_holes():
            bore = cad_helpers.cylinder_centered(d, self._plate_thickness + 1.0)
            bore = cad_helpers.translate(bore, x, y, self._plate_thickness / 2.0)
            plate = cad_helpers.cut(plate, bore)

        return plate
