"""40% keyboard assembly: switch plate + RP2040 controller.

The physical keyboard is the Cherry-MX-compatible switch plate with a
Waveshare RP2040-Zero controller running QMK/Vial. Plate geometry comes
from the :mod:`keyboard` package (KLE layout → geometry model); this
component is the cyberdeck adapter that produces the CadQuery solid.
"""

from __future__ import annotations

from typing import Any

from components.base import BoundingBox, Component, Connector, Hole
from components.keyboard_plate import KeyboardPlate
from components.rp2040_zero import Rp2040Zero
from utilities.constants import CONNECTOR_USB_C, DIR_POS_X


class Rp2040Keyboard(Component):
    """40% keyboard: switch plate + RP2040-Zero controller."""

    name = "40% Keyboard (RP2040)"

    def __init__(self, keyboard: dict[str, Any] | None = None) -> None:
        data = keyboard or {}
        self._plate = KeyboardPlate(data)
        self._switch_family = str(data.get("switch_family", "mx_alps"))
        self._stab_family = str(data.get("stabilizer_family", "cherry"))
        plate_cfg = data.get("plate", {}) or {}
        self._plate_thickness = float(plate_cfg.get("thickness", 1.5))
        self._plate_inset = float(plate_cfg.get("edge_margin", 6.0))
        self._pitch = float(data.get("pitch", 19.05))
        self.controller = Rp2040Zero(data.get("controller", {}))

    def size(self) -> BoundingBox:
        box = self._plate.size()
        height = box.height + 10.0  # switch + cap allowance
        return BoundingBox(box.width, box.depth, height)

    def mounting_holes(self) -> list[Hole]:
        return self._plate.mounting_holes()

    def connectors(self) -> list[Connector]:
        box = self._plate.size()
        return [
            Connector(
                type=CONNECTOR_USB_C,
                x=box.width / 2,
                y=0.0,
                z=self._plate_thickness + 2.0,
                direction=DIR_POS_X,
                width=8.5,
                height=2.6,
                depth=4.0,
            )
        ]

    @property
    def switch_grid(self) -> list[tuple[float, float]]:
        return self._plate.switch_positions

    def build(self):
        """Generate the keyboard solid: switch plate plus switch housings.

        The RP2040-Zero controller solid is omitted — its mounting under the
        plate is part of the pending staggered-40% keyboard rework (TODO). The
        build stays within the nominal :meth:`size` footprint.
        """
        from keyboard.registry import get_switch
        from utilities import cq_helpers

        cq_helpers.require_cq()

        plate = self._plate.build()
        body = plate

        # Switch housings rise above the plate at each switch grid position.
        switch_cls = get_switch(self._switch_family)
        switch = switch_cls()
        verts = list(switch.cutout_vertices())
        switch_depth = 3.0
        for x, y in self.switch_grid:
            housing = cq_helpers.extrude_polygon(
                verts, switch_depth, x, y,
                self._plate_thickness + switch_depth / 2.0,
            )
            body = body.union(housing)

        return body
