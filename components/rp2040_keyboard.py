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
    """40% keyboard: switch plate + XDA keycaps + RP2040-Zero controller.

    Switch housings are not rendered — only the plate cutouts and keycaps
    are visible.  Keycaps are lofted from an 18.5 mm square base to a
    15.0 mm stadium (rounded-rectangle) top, 9.0 mm tall (XDA profile).
    """

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

        keycap_cfg = data.get("keycap", {}) or {}
        self._keycap_profile = str(keycap_cfg.get("profile", "xda"))
        self._keycap_enabled = bool(keycap_cfg.get("enabled", True))

    def set_plate_raise(self, height: float) -> None:
        """Override the plate standoff height (mm).

        The layout calls this when components buried under the raised plate
        (e.g. the SBC) require more clearance than the controller alone.
        """
        self._plate_raise = height

    @property
    def switch_bottom_protrusion(self) -> float:
        """Deepest point of the switch bodies below the plate bottom (mm).

        The simplified switch pins hang 3.5 mm below the plate bottom surface.
        Components buried under the plate must clear this protrusion.
        """
        return 3.5

    def size(self) -> BoundingBox:
        box = self._plate.size()
        from components.keycap_set import CAP_PLATE_GAP
        from keyboard.registry import get_keycap
        profile = get_keycap(self._keycap_profile)()
        cap_height = profile.height()
        height = self._plate_raise + self._plate_thickness + CAP_PLATE_GAP + cap_height
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

    def validate(self) -> tuple[int, list[str]]:
        """Run the keyboard plate geometry validation checks.

        Returns
        -------
        tuple[int, list[str]]
            ``(checks_run, errors)`` — number of checks executed and any error
            messages. An empty ``errors`` list means the plate model is valid.
        """
        return self._plate.validate()

    def build(self):
        """Generate the keyboard solid: raised plate, switch bodies, keycaps, controller.

        The plate sits on standoffs at ``_plate_raise`` with simplified switch
        bodies protruding through the cutouts and keycaps lofted above them.
        The RP2040-Zero controller rests on the mounting plane beneath the plate.
        """
        from components.keycap_set import KeycapSet
        from utilities import cq_helpers

        cq_helpers.require_cq()

        plate = self._plate.build()

        # Simplified switch body at each grid position (local coords).
        # Cube (13 mm) has its **bottom** 5 mm below the plate top surface,
        # so it passes up through the plate cutout and pokes into the keycap.
        # A 4 mm diameter cylinder pokes 3.5 mm below the cube bottom.
        switch_body_size = 13.0
        switch_pin_diameter = 4.0
        switch_pin_height = 3.5
        cube_bottom_offset = 5.0  # cube bottom below plate top surface
        cube_center_z = self._plate_thickness - cube_bottom_offset + switch_body_size / 2.0
        pin_center_z = self._plate_thickness - cube_bottom_offset - switch_pin_height / 2.0
        switch_shapes: list[Any] = []
        for x, y in self.switch_grid:
            cube = cq_helpers.box_centered(switch_body_size, switch_body_size, switch_body_size)
            cube = cq_helpers.translate(cube, x, y, cube_center_z)
            switch_shapes.append(cube)
            pin = cq_helpers.cylinder_centered(switch_pin_diameter, switch_pin_height)
            pin = cq_helpers.translate(pin, x, y, pin_center_z)
            switch_shapes.append(pin)
        body = plate.union(cq_helpers.make_compound(switch_shapes))

        # Raise the plate assembly onto its standoffs.
        body = cq_helpers.translate(body, 0.0, 0.0, self._plate_raise)

        # Keycaps lofted above the plate (compound, fused in one op).
        self._plate._ensure_model()
        keys = list(self._plate._layout.keys)
        centroid = self._plate._layout._centroid()
        caps = KeycapSet(
            self.switch_grid, keys,
            profile_name=self._keycap_profile,
            plate_raise=self._plate_raise,
            plate_thickness=self._plate_thickness,
            pitch=self._pitch,
            layout_centroid=centroid,
            enabled=self._keycap_enabled,
        )
        body = body.union(caps.build())

        # Controller beneath the plate, on the mounting plane.
        controller = self.controller.build()
        controller = cq_helpers.translate(
            controller, self._controller_x, self._controller_y, 0.0
        )
        return body.union(controller)
