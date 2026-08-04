"""40% keyboard assembly: switch plate + RP2040 controller.

The physical keyboard is the Cherry-MX-compatible switch plate with a
Waveshare RP2040-Zero controller running QMK/Vial. Plate geometry comes
from the :mod:`keyboard` package (KLE layout → geometry model); this
component is the cyberdeck adapter that produces the CadQuery solid.

The plate is raised on standoffs so the controller fits beneath it; the
controller's USB-C is internal and connects to the SBC with a cable inside
the housing — no external keyboard connector.
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

        controller_cfg = data.get("controller", {}) or {}
        self.controller = Rp2040Zero(controller_cfg)
        self._controller_x = float(controller_cfg.get("x", 0.0))
        self._controller_y = float(controller_cfg.get("y", 0.0))
        z_clearance = float(controller_cfg.get("z_clearance", 2.0))
        self._plate_raise = self.controller.height + z_clearance

    def size(self) -> BoundingBox:
        box = self._plate.size()
        height = self._plate_raise + box.height + 10.0  # switch + cap allowance
        return BoundingBox(box.width, box.depth, height)

    def occupied_volumes(self) -> list[tuple[float, float, float, BoundingBox]]:
        """Solid sub-volumes: the raised plate block and the controller block.

        The plate sits on standoffs at ``_plate_raise``; the space beneath it is
        hollow (occupied only by the controller), so a component buried under
        the plate does not collide with the keyboard.
        """
        plate_box = self._plate.size()
        plate_height = self.size().height - self._plate_raise
        controller_box = self.controller.size()
        return [
            (0.0, 0.0, self._plate_raise, BoundingBox(plate_box.width, plate_box.depth, plate_height)),
            (self._controller_x, self._controller_y, 0.0, controller_box),
        ]

    def mounting_holes(self) -> list[Hole]:
        # The plate mounts on four standoff bosses (height = plate raise). The
        # controller rests flat on the base floor beneath the plate and is held
        # by the plate assembly — its own corner holes stay on the Rp2040Zero
        # component for serviceability but generate no case bosses.
        return [
            Hole(h.x, h.y, h.diameter, height=self._plate_raise)
            for h in self._plate.mounting_holes()
        ]

    def mounting_screw(self) -> str:
        """The plate's standoff screw size (from keyboard.mounting.screw)."""
        return self._plate.mounting_screw()

    def connectors(self) -> list[Connector]:
        # The controller's USB-C is internal — it cables to the SBC inside the
        # case, so no shell cutout is generated for it.
        conn = self.controller.connectors()[0]
        return [
            Connector(
                type=CONNECTOR_USB_C,
                x=self._controller_x + conn.x,
                y=self._controller_y + conn.y,
                z=conn.z,
                direction=DIR_POS_X,
                width=conn.width,
                height=conn.height,
                depth=conn.depth,
                internal=True,
            )
        ]

    @property
    def switch_grid(self) -> list[tuple[float, float]]:
        return self._plate.switch_positions

    def validate(self) -> list[str]:
        """Run the keyboard plate geometry validation checks."""
        return self._plate.validate()

    def build(self):
        """Generate the keyboard solid: raised plate, switch housings, controller.

        The plate and switch housings sit on standoffs at ``_plate_raise``;
        the RP2040-Zero controller rests on the mounting plane beneath them.
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

        # Raise the plate assembly onto its standoffs.
        body = cq_helpers.translate(body, 0.0, 0.0, self._plate_raise)

        # Controller beneath the plate, on the mounting plane.
        controller = self.controller.build()
        controller = cq_helpers.translate(
            controller, self._controller_x, self._controller_y, 0.0
        )
        return body.union(controller)
