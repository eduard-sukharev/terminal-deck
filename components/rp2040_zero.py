"""Waveshare RP2040-Zero microcontroller board (keyboard controller).

Dimensions sourced from the Waveshare RP2040-Zero product page / wiki:

* Board: 18 x 23.5 mm, PCB 1.0 mm thick
* RP2040 chip: 7.0 x 7.0 x 1.0 mm on the underside
* USB-C connector: 9.0 x 7.5 x 3.3 mm on the top side, protruding 1.4 mm
  past the shorter (18 mm) edge
* Four corner mounting holes, ~2.0 mm diameter
* Castellated pads at 2.54 mm pitch

This is the QMK/Vial controller for the 40% keyboard. Board frame: origin at
board center, +X along the 18 mm length, +Y along the 23.5 mm width, +Z
upward. The board bottom (PCB underside) sits on the mounting plane (z=0);
the chip hangs below it and the connector rises above the top.
"""

from __future__ import annotations

from typing import Any

from components.base import BoundingBox, Component, Connector, Hole
from utilities.constants import CONNECTOR_USB_C, DIR_POS_X


class Rp2040Zero(Component):
    """Waveshare RP2040-Zero microcontroller board."""

    name = "RP2040-Zero"

    #: PCB thickness (mm).
    pcb_thickness = 1.0
    #: RP2040 chip footprint on the underside (mm).
    chip_size = 7.0
    chip_thickness = 1.0
    #: USB-C connector extents (mm): width along the edge, protrusion depth,
    #: height above the PCB top.
    conn_width = 9.0
    conn_depth = 7.5
    conn_height = 3.3
    #: How far the connector protrudes past the shorter (18 mm) edge (mm).
    conn_protrusion = 1.4

    def __init__(self, controller: dict[str, Any] | None = None) -> None:
        data = controller or {}
        self.width = float(data.get("width", 18.0))
        self.depth = float(data.get("depth", 23.5))
        self.height = float(data.get("height", 5.3))
        self.hole_diameter = float(data.get("hole_diameter", 2.0))

    def size(self) -> BoundingBox:
        return BoundingBox(self.width, self.depth, self.height)

    def mounting_holes(self) -> list[Hole]:
        # Four corner mounting holes, ~2.0 mm, inset from the board edges.
        inset = 2.0
        half_w, half_d = self.width / 2, self.depth / 2
        h = self.boss_height()
        return [
            Hole(-half_w + inset, -half_d + inset, self.hole_diameter, height=h),
            Hole(half_w - inset, -half_d + inset, self.hole_diameter, height=h),
            Hole(half_w - inset, half_d - inset, self.hole_diameter, height=h),
            Hole(-half_w + inset, half_d - inset, self.hole_diameter, height=h),
        ]

    def connectors(self) -> list[Connector]:
        # USB-C on the short edge (+X), protruding 1.4 mm past it. The
        # connector sits on the PCB top; its centre is offset so that
        # ``conn_protrusion`` of its depth hangs past the +X edge.
        # Internal: the board is buried under the keyboard and cables to the
        # SBC inside the case, so it gets no shell cutout.
        pcb_top = self.pcb_thickness
        conn_centre_x = self.width / 2 + self.conn_protrusion - self.conn_depth / 2
        return [
            Connector(
                type=CONNECTOR_USB_C,
                x=conn_centre_x,
                y=0.0,
                z=pcb_top + self.conn_height / 2,
                direction=DIR_POS_X,
                width=self.conn_width,
                height=self.conn_height,
                depth=self.conn_depth,
                internal=True,
            )
        ]

    def build(self):
        """Build a bounding solid: PCB, underside chip, and USB-C connector.

        The PCB bottom sits on the mounting plane (z=0); the chip hangs below
        it (z from -chip_thickness to 0) and the connector rises above the PCB
        top, protruding 1.4 mm past the +X edge.
        """
        from utilities import cq_helpers

        cq_helpers.require_cq()

        # PCB: bottom on the mounting plane (z=0).
        board = cq_helpers.box_centered(self.width, self.depth, self.pcb_thickness)
        board = cq_helpers.translate(board, 0.0, 0.0, self.pcb_thickness / 2.0)

        # RP2040 chip on the underside, centred on the board.
        chip = cq_helpers.box_centered(self.chip_size, self.chip_size, self.chip_thickness)
        chip = cq_helpers.translate(chip, 0.0, 0.0, -self.chip_thickness / 2.0)

        conn = self.connectors()[0]
        block = cq_helpers.box_centered(conn.depth, conn.width, conn.height)
        block = cq_helpers.translate(block, conn.x, 0.0, conn.z)

        return board.union(chip).union(block)