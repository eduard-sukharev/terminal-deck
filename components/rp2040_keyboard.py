"""40% keyboard assembly: switch plate + RP2040 controller.

The physical keyboard is the Cherry-MX-compatible switch plate with a
Waveshare RP2040-Zero controller running QMK/Vial. Plate size is *calculated
geometry*: ``columns * pitch + plate inset``. See ``config/keyboard.yaml``.
"""

from __future__ import annotations

from typing import Any

from components.base import BoundingBox, Component, Connector, Hole
from components.rp2040_zero import Rp2040Zero
from utilities.constants import CONNECTOR_USB_C, DIR_POS_X


class Rp2040Keyboard(Component):
    """40% keyboard: switch plate + RP2040-Zero controller."""

    name = "40% Keyboard (RP2040)"

    def __init__(self, keyboard: dict[str, Any] | None = None) -> None:
        data = keyboard or {}
        self.columns = int(data.get("columns", 12))
        self.rows = int(data.get("rows", 4))
        self.pitch = float(data.get("pitch", 19.05))
        plate = data.get("plate", {})
        self.plate_thickness = float(plate.get("thickness", 1.5))
        self.plate_inset = float(plate.get("inset", 3.0))
        self._switch_cutout_type = str(plate.get("switch_cutout", "mx"))
        self._stab_cutout_type = str(plate.get("stabilizer_cutout", "mx-basic"))
        stabilizers = data.get("stabilizers", {})
        self._stab_present = bool(stabilizers.get("present", True))
        self._stab_offset_y = float(stabilizers.get("offset_y", -1.4))
        self._stab_keys: dict[str, dict] = stabilizers.get("keys", {})
        # The keyboard controller (RP2040-Zero) mounted under the plate.
        self.controller = Rp2040Zero(data.get("controller", {}))

    def size(self) -> BoundingBox:
        # Calculated geometry, never estimated.
        width = self.columns * self.pitch + 2 * self.plate_inset
        depth = self.rows * self.pitch + 2 * self.plate_inset
        height = self.plate_thickness + 10.0  # switch + cap allowance
        return BoundingBox(width, depth, height)

    def mounting_holes(self) -> list[Hole]:
        # TODO: place real plate mounting holes at switch-adjacent positions.
        inset = self.plate_inset + 2.0
        return [
            Hole(-self.size().width / 2 + inset, -self.size().depth / 2 + inset, 2.0),
            Hole(self.size().width / 2 - inset, -self.size().depth / 2 + inset, 2.0),
            Hole(self.size().width / 2 - inset, self.size().depth / 2 - inset, 2.0),
            Hole(-self.size().width / 2 + inset, self.size().depth / 2 - inset, 2.0),
        ]

    def connectors(self) -> list[Connector]:
        return [
            Connector(
                type=CONNECTOR_USB_C,
                x=self.size().width / 2,
                y=0.0,
                z=self.plate_thickness + 2.0,
                direction=DIR_POS_X,
                width=8.5,
                height=2.6,
                depth=4.0,
            )
        ]

    @property
    def switch_grid(self) -> list[tuple[float, float]]:
        """Center coordinates of every switch on the plate (mm, plate frame)."""
        half_width = (self.columns - 1) * self.pitch / 2
        half_depth = (self.rows - 1) * self.pitch / 2
        return [
            (x, y)
            for row in range(self.rows)
            for col in range(self.columns)
            for x, y in [
                (
                    -half_width + col * self.pitch,
                    -half_depth + row * self.pitch,
                )
            ]
        ]

    def build(self):
        """Generate the keyboard solid: switch plate plus switch housings.

        The RP2040-Zero controller solid is omitted — its mounting under the
        plate is part of the pending staggered-40% keyboard rework (TODO). The
        build stays within the nominal :meth:`size` footprint.
        """
        from geometry.stabilizer_cutout import build_stabilizer_cutout
        from geometry.switch_cutout import build_cutout
        from utilities import cq_helpers

        cq_helpers.require_cq()
        box = self.size()
        plate = cq_helpers.box_centered(box.width, box.depth, self.plate_thickness)
        plate = cq_helpers.translate(plate, 0.0, 0.0, self.plate_thickness / 2.0)

        # Switch housings — dispatches to registry by type.
        body = plate
        switch_depth = 3.0  # housing depth above the plate (switch + cap allowance)
        for x, y in self.switch_grid:
            housing = build_cutout(
                switch_depth, x, y, self.plate_thickness + switch_depth / 2.0,
                cutout_type=self._switch_cutout_type,
            )
            if housing is not None:
                body = body.union(housing)

        # Stabilizer cutouts — same dispatch.
        stab_positions = self._stabilizer_placements()
        if stab_positions:
            for x, y in stab_positions:
                cut = build_stabilizer_cutout(
                    self.plate_thickness + 1.0, x, y,
                    cutout_type=self._stab_cutout_type,
                )
                if cut is not None:
                    body = body.cut(cut)

        return body

    def _stabilizer_placements(self) -> list[tuple[float, float]]:
        """Compute stabilizer slot positions from config (delegates to KeyboardPlate)."""
        from components.keyboard_plate import KeyboardPlate

        kp = KeyboardPlate({
            "columns": self.columns,
            "rows": self.rows,
            "pitch": self.pitch,
            "plate": {
                "thickness": self.plate_thickness,
                "inset": self.plate_inset,
                "switch_cutout": self._switch_cutout_type,
                "stabilizer_cutout": self._stab_cutout_type,
            },
            "stabilizers": {
                "present": self._stab_present,
                "offset_y": self._stab_offset_y,
                "keys": self._stab_keys,
            },
        })
        return kp.stabilizer_positions
