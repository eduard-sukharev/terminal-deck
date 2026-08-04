"""Keyboard switch plate.

A separate CAD file from the enclosure, exporting:

* the plate
* switch cutouts
* mounting holes
* stabilizer cutouts

The plate is independent of the enclosure — it can be cut on FR4 or printed
alone. Geometry is *calculated* from ``config/keyboard.yaml`` (columns, rows,
pitch, plate inset, plate thickness), never estimated.
"""

from __future__ import annotations

from typing import Any

from components.base import BoundingBox, Component, Hole


class KeyboardPlate(Component):
    """Cherry-MX switch plate for the 40% layout."""

    name = "Keyboard Plate"

    def __init__(self, keyboard: dict[str, Any] | None = None) -> None:
        data = keyboard or {}
        self.columns = int(data.get("columns", 12))
        self.rows = int(data.get("rows", 4))
        self.pitch = float(data.get("pitch", 19.05))
        plate = data.get("plate", {})
        self.thickness = float(plate.get("thickness", 1.5))
        self.inset = float(plate.get("inset", 3.0))
        self._switch_cutout_type = str(plate.get("switch_cutout", "mx"))
        self._stab_cutout_type = str(plate.get("stabilizer_cutout", "mx-basic"))
        stabilizers = data.get("stabilizers", {})
        self._stab_present = bool(stabilizers.get("present", True))
        self._stab_offset_y = float(stabilizers.get("offset_y", -1.4))
        self._stab_keys: dict[str, dict] = stabilizers.get("keys", {})

    def size(self) -> BoundingBox:
        return BoundingBox(
            self.columns * self.pitch + 2 * self.inset,
            self.rows * self.pitch + 2 * self.inset,
            self.thickness,
        )

    def mounting_holes(self) -> list[Hole]:
        # TODO: place real plate mounting holes near the plate corners.
        inset = self.inset + 2.0
        box = self.size()
        return [
            Hole(-box.width / 2 + inset, -box.depth / 2 + inset, 2.0),
            Hole(box.width / 2 - inset, -box.depth / 2 + inset, 2.0),
            Hole(box.width / 2 - inset, box.depth / 2 - inset, 2.0),
            Hole(-box.width / 2 + inset, box.depth / 2 - inset, 2.0),
        ]

    @property
    def switch_positions(self) -> list[tuple[float, float]]:
        """(x, y) centers of every MX switch, plate frame (mm)."""
        half_w = (self.columns - 1) * self.pitch / 2
        half_d = (self.rows - 1) * self.pitch / 2
        return [
            (-half_w + col * self.pitch, -half_d + row * self.pitch)
            for row in range(self.rows)
            for col in range(self.columns)
        ]

    @property
    def stabilizer_positions(self) -> list[tuple[float, float]]:
        """(x, y) of stabilizer cutout centers (plate frame, mm).

        Reads the ``stabilizers.keys`` config to determine which grid
        positions have stabilizers and computes left/right slot positions
        from the key width.
        """
        from geometry.stabilizer_cutout import stabilizer_offset, stabilizer_pair

        if not self._stab_present or not self._stab_keys:
            return []

        positions: list[tuple[float, float]] = []
        half_w = (self.columns - 1) * self.pitch / 2
        half_d = (self.rows - 1) * self.pitch / 2

        for grid_id, key_cfg in self._stab_keys.items():
            try:
                row_str, col_str = grid_id.split("_")
                row, col = int(row_str), int(col_str)
            except (ValueError, IndexError):
                continue
            if row >= self.rows or col >= self.columns:
                continue

            sw_x = -half_w + col * self.pitch
            sw_y = -half_d + row * self.pitch
            width = float(key_cfg.get("width", 2.0))
            if "offset" in key_cfg:
                offset = float(key_cfg["offset"])
            else:
                offset = stabilizer_offset(width, self.pitch)

            left, right = stabilizer_pair(sw_x, sw_y, offset, self._stab_offset_y)
            positions.append((left.x, left.y))
            positions.append((right.x, right.y))

        return positions

    def build(self):
        """Cut the switch plate: plate, switch cutouts, stabilizers, mounting holes."""
        from geometry.stabilizer_cutout import build_stabilizer_cutout
        from geometry.switch_cutout import build_cutout
        from utilities import cq_helpers

        cq_helpers.require_cq()
        box = self.size()
        plate = cq_helpers.box_centered(box.width, box.depth, self.thickness)
        plate = cq_helpers.translate(plate, 0.0, 0.0, self.thickness / 2.0)

        # Switch cutouts — dispatches to registry by type.
        for x, y in self.switch_positions:
            cut = build_cutout(
                self.thickness + 1.0, x, y,
                cutout_type=self._switch_cutout_type,
            )
            if cut is not None:
                plate = plate.cut(cut)

        # Stabilizer cutouts — same dispatch.
        if self._stab_present and self._stab_keys:
            for x, y in self.stabilizer_positions:
                cut = build_stabilizer_cutout(
                    self.thickness + 1.0, x, y,
                    cutout_type=self._stab_cutout_type,
                )
                if cut is not None:
                    plate = plate.cut(cut)

        for hole in self.mounting_holes():
            bore = cq_helpers.cylinder_centered(hole.diameter, self.thickness + 1.0)
            bore = cq_helpers.translate(bore, hole.x, hole.y, 0.0)
            plate = plate.cut(bore)
        return plate
