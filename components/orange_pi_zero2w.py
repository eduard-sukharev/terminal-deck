"""Orange Pi Zero 2W single-board computer (Allwinner H618).

Board frame: origin at board center, +X along the 65 mm length, +Y along the
30 mm width, +Z upward, z=0 at the PCB bottom.

Measured (user, calipers, mm; distances are board-center coordinates after
converting from the reported edge measurements):
* PCB: 65.0 x 30.0 x 1.4; 4 mounting holes 3.0 mm @ 3.5 mm inset
* Stack height 6.7 total: tallest top-side part (USB-C) 3.3 + PCB 1.4 +
  tallest bottom-side part (SOP-8 SPI flash) 2.0. With optional 7 mm radiators
  on the SoC/memory the top-side height becomes 8.8 and the total 12.1
  (``sbc.height`` in ``config/hardware.yaml``).

Connectors (user measurements, as provided — board edges are the reference):
* Mini-HDMI: bottom (south), facing south; west side of metal casing 6.7 from
  west PCB edge; casing 11.5 x 7.6 x 3.3 (opening 11.5 x 3.3); protrudes 1.0
  past the south PCB edge
* USB-C #1 (power, OTG): bottom (south), facing south; east side of metal
  casing 6.5 from east PCB edge; casing 9 x 8 x 3.5 (opening 9 x 3.5);
  protrudes 1.0 past the south PCB edge
* USB-C #2 (power): bottom (south), facing south; east side of metal casing
  19.0 from east PCB edge; casing 9 x 8 x 3.5 (opening 9 x 3.5); protrudes
  1.0 past the south PCB edge
* MicroSD slot: left (west), facing west; north side of metal casing 17.2 from
  north PCB edge; casing 11.4 x 11.4 x 1.4 (opening 11.4 x 1.4); sits flush
  with the west PCB edge
"""

from __future__ import annotations

from typing import Any

from components.base import BoundingBox, Component, Connector, Hole
from utilities.constants import (
    CONNECTOR_HDMI,
    CONNECTOR_MICROSD,
    CONNECTOR_POWER,
    CONNECTOR_USB_C,
    DIR_NEG_X,
    DIR_NEG_Y,
)


class OrangePiZero2W(Component):
    """Orange Pi Zero 2W SBC (Allwinner H618)."""

    name = "Orange Pi Zero 2W"

    def __init__(self, hardware: dict[str, Any] | None = None) -> None:
        sbc = (hardware or {}).get("sbc", {})
        self.width = float(sbc.get("width", 65.0))
        self.depth = float(sbc.get("depth", 30.0))
        self.height = float(sbc.get("height", 6.7))
        self.pcb_thickness = float(sbc.get("pcb_thickness", 1.4))
        self.hole_diameter = float(sbc.get("mounting_hole_diameter", 3.0))
        self.hole_inset = float(sbc.get("mounting_hole_inset", 3.5))

    def size(self) -> BoundingBox:
        return BoundingBox(self.width, self.depth, self.height)

    def mounting_holes(self) -> list[Hole]:
        # Four holes, 3.0 mm, centers 3.5 mm from the board edges. Converted
        # from board-corner coordinates to the component-center frame.
        inset = self.hole_inset
        half_w, half_d = self.width / 2, self.depth / 2
        return [
            Hole(-half_w + inset, -half_d + inset, self.hole_diameter),
            Hole(half_w - inset, -half_d + inset, self.hole_diameter),
            Hole(half_w - inset, half_d - inset, self.hole_diameter),
            Hole(-half_w + inset, half_d - inset, self.hole_diameter),
        ]

    def connectors(self) -> list[Connector]:
        # Edge-to-center conversion, e.g. Mini-HDMI casing west side 6.7 from
        # the west edge (x=-32.5): x = -32.5 + 6.7 + 11.5/2 = -20.05; casing
        # protrudes 1.0 past the south edge (y=-15) and is 7.6 deep:
        # y = -15 - 1.0 + 7.6/2 = -12.2. z = PCB + opening height / 2.
        pcb = self.pcb_thickness
        return [
            # Mini-HDMI — internal: the display signal cable routes through the
            # hinge wire tunnel to the driver board behind the LCD (no shell
            # cutout; nothing exposed per the build spec).
            Connector(
                type=CONNECTOR_HDMI,
                x=-20.05,
                y=-12.2,
                z=pcb + 3.3 / 2,
                direction=DIR_NEG_Y,
                width=11.5,
                height=3.3,
                depth=7.6,
                internal=True,
            ),
            # USB-C #1 (OTG) — east side 6.5 from east edge. Internal: host-side
            # connectivity goes through the rear USB hub, so this one stays
            # inside rather than spending a second rear-wall opening.
            Connector(
                type=CONNECTOR_USB_C,
                x=21.5,
                y=-12.0,
                z=pcb + 3.5 / 2,
                direction=DIR_NEG_Y,
                width=9.0,
                height=3.5,
                depth=8.0,
                internal=True,
            ),
            # USB-C #2 (power) — east side 19.0 from east edge. External: this
            # is the deck's only charge/supply inlet, so a sealed case with no
            # cutout here could never be recharged.
            Connector(
                type=CONNECTOR_POWER,
                x=9.0,
                y=-12.0,
                z=pcb + 3.5 / 2,
                direction=DIR_NEG_Y,
                width=9.0,
                height=3.5,
                depth=8.0,
                internal=False,
            ),
            # MicroSD — north side 17.2 from north edge, flush with west edge.
            # External: the card carries the OS, and reflashing it is the most
            # common field service task on this deck.
            Connector(
                type=CONNECTOR_MICROSD,
                x=-26.8,
                y=-7.9,
                z=pcb + 1.4 / 2,
                direction=DIR_NEG_X,
                width=11.4,
                height=1.4,
                depth=11.4,
                internal=False,
            ),
        ]

    def build(self):
        """Generate the SBC solid: PCB, SoC block, connector sockets, holes."""
        from utilities import cq_helpers

        cq_helpers.require_cq()
        pcb = cq_helpers.box_centered(self.width, self.depth, self.pcb_thickness)
        pcb = cq_helpers.translate(pcb, 0.0, 0.0, self.pcb_thickness / 2.0)

        # Bottom-side SOP-8 SPI flash (measured 2.0 mm tall, below the PCB).
        body = pcb
        flash = cq_helpers.box_centered(6.0, 4.0, 2.0)
        body = body.union(cq_helpers.translate(flash, 8.0, 6.0, 1.0))

        # Top-side SoC/memory block (sits under the tallest sockets at 3.3 mm).
        soc = cq_helpers.box_centered(10.0, 10.0, 3.3)
        body = body.union(cq_helpers.translate(soc, -8.0, 0.0, self.pcb_thickness + 1.65))

        # Connector socket blocks on the south/west edges.
        sockets = [
            (-20.05, -12.2, 11.5, 7.6, 3.3),  # mini-HDMI (south)
            (21.5, -12.0, 9.0, 8.0, 3.5),     # USB-C #1 (south)
            (9.0, -12.0, 9.0, 8.0, 3.5),      # USB-C #2 (south)
            (-26.8, -7.9, 11.4, 11.4, 1.4),   # microSD (west)
        ]
        for x, y, w, d, h in sockets:
            block = cq_helpers.box_centered(w, d, h)
            block = cq_helpers.translate(block, x, y, self.pcb_thickness + h / 2.0)
            body = body.union(block)

        for hole in self.mounting_holes():
            bore = cq_helpers.cylinder_centered(hole.diameter, self.height + 1.0)
            bore = cq_helpers.translate(bore, hole.x, hole.y, self.height / 2.0)
            body = body.cut(bore)
        return body
