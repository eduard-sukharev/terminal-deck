"""Waveshare RP2040-Zero microcontroller board (keyboard controller).

Dimensions sourced from the Waveshare RP2040-Zero product page / wiki:

* Board: 23.5 x 18 mm, PCB ~1.0 mm thick, ~8 mm tall with components
* USB-C connector (native USB 1.1)
* Four corner mounting holes, ~2.0 mm diameter
* Castellated pads at 2.54 mm pitch

This is the QMK/Vial controller for the 40% keyboard. Board frame: origin at
board center, +X along the 23.5 mm length, +Y along the 18 mm width, +Z
upward.
"""

from __future__ import annotations

from typing import Any

from components.base import BoundingBox, Component, Connector, Hole
from utilities.constants import CONNECTOR_USB_C, DIR_POS_X


class Rp2040Zero(Component):
    """Waveshare RP2040-Zero microcontroller board."""

    name = "RP2040-Zero"

    def __init__(self, controller: dict[str, Any] | None = None) -> None:
        data = controller or {}
        self.width = float(data.get("width", 23.5))
        self.depth = float(data.get("depth", 18.0))
        self.height = float(data.get("height", 8.0))
        self.hole_diameter = float(data.get("hole_diameter", 2.0))

    def size(self) -> BoundingBox:
        return BoundingBox(self.width, self.depth, self.height)

    def mounting_holes(self) -> list[Hole]:
        # Four corner mounting holes, ~2.0 mm, inset from the board edges.
        inset = 2.0
        half_w, half_d = self.width / 2, self.depth / 2
        return [
            Hole(-half_w + inset, -half_d + inset, self.hole_diameter),
            Hole(half_w - inset, -half_d + inset, self.hole_diameter),
            Hole(half_w - inset, half_d - inset, self.hole_diameter),
            Hole(-half_w + inset, half_d - inset, self.hole_diameter),
        ]

    def connectors(self) -> list[Connector]:
        # USB-C on the short edge (+X).
        return [
            Connector(
                type=CONNECTOR_USB_C,
                x=self.width / 2,
                y=0.0,
                z=self.height / 2,
                direction=DIR_POS_X,
                width=8.5,
                height=2.6,
                depth=4.0,
            )
        ]

    def build(self):
        """Build a bounding solid: board volume plus the USB-C connector block.

        The board sits with its bottom on the mounting plane (z=0); the
        connector protrudes from the +X edge.
        """
        from utilities import cq_helpers

        cq_helpers.require_cq()

        board = cq_helpers.box_centered(self.width, self.depth, self.height)
        board = cq_helpers.translate(board, 0.0, 0.0, self.height / 2.0)

        conn = self.connectors()[0]
        block = cq_helpers.box_centered(conn.depth, conn.width, conn.height)
        block = cq_helpers.translate(
            block, self.width / 2 + conn.depth / 2, 0.0, conn.z
        )
        return board.union(block)