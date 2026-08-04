"""USB breakout board.

Small breakout adding extra USB-A ports. Dimensions from
``config/hardware.yaml`` (``usb_breakout`` section).
"""

from __future__ import annotations

from typing import Any

from components.base import BoundingBox, Component, Connector, Hole
from utilities.constants import CONNECTOR_USB_A, DIR_POS_Y


class UsbBreakout(Component):
    """USB-A breakout board."""

    name = "USB Breakout"

    def __init__(self, hardware: dict[str, Any] | None = None) -> None:
        data = (hardware or {}).get("usb_breakout", {})
        self.width = float(data.get("width", 20.0))
        self.depth = float(data.get("depth", 15.0))
        self.height = float(data.get("height", 8.0))
        self.holes = int(data.get("holes", 2))

    def size(self) -> BoundingBox:
        return BoundingBox(self.width, self.depth, self.height)

    def mounting_holes(self) -> list[Hole]:
        inset = 2.5
        count = max(self.holes, 2)
        holes: list[Hole] = []
        for i in range(count):
            x = -self.width / 2 + inset + i * (self.width - 2 * inset) / (count - 1)
            holes.append(Hole(x, 0.0, 2.0))
        return holes

    def connectors(self) -> list[Connector]:
        return [
            Connector(
                type=CONNECTOR_USB_A,
                x=0.0,
                y=self.depth / 2,
                z=self.height / 2,
                direction=DIR_POS_Y,
                width=13.0,
                height=8.0,
                depth=12.0,
            )
        ]

    def build(self):
        """Generate the breakout solid: PCB box plus the USB-A socket block."""
        from utilities import cq_helpers

        cq_helpers.require_cq()
        board = cq_helpers.box_centered(self.width, self.depth, self.height)
        board = cq_helpers.translate(board, 0.0, 0.0, self.height / 2.0)
        socket = cq_helpers.box_centered(13.0, 12.0, 8.0)
        socket = cq_helpers.translate(socket, 0.0, self.depth / 2 + 6.0, self.height / 2.0)
        return board.union(socket)
