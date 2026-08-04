"""HDMI driver board for the 8.8" display.

Converts HDMI to the panel's FPC signal. Physically offset from the display
center (never assumed centered) via :meth:`reference_origin`. Dimensions from
``config/display.yaml`` (``driver_board`` section).

Board frame: origin at board center, +X along the 55 mm length, +Y along the
45.5 mm width, +Z upward, z=0 at the PCB bottom.

Measured (user, calipers, mm; board edges are the reference):
* PCB: 55.0 x 45.5 x 1.3; total height 4.6 (tallest sockets 3.3 above PCB)
* Mini-HDMI socket: facing east at the east edge, protrudes 1.0 past the edge;
  metal casing 8 x 11.3 (opening 3.3 x 11.3); south edge of metal casing 5.8
  from the south PCB edge
* USB Type-C power socket: facing east at the east edge, protrudes 1.0 past
  the edge; casing 7.5 x 9 (opening 3.3 x 9); north edge of metal casing 8.5
  from the north PCB edge
* FPC slot: 6 x 29.5, facing west; west side aligned with the west side of the
  PCB; south side 3.0 from the south PCB edge
* mounting: three M3 holes at the north-west, north-east and south-east
  corners, 3.0 mm inset, 3.0 mm diameter

Mounting: the driver board sits back-to-back directly behind the LCD panel in
the lid (``layout_default.py``). All three connectors are *internal*: the FPC
slot mates the folded panel ribbon, and the mini-HDMI + USB-C power sockets
take cables routed through the hinge wire tunnel to the SBC in the base. No
shell cutouts are generated for them.
"""

from __future__ import annotations

from typing import Any

from components.base import BoundingBox, Component, Connector, Hole
from utilities.constants import CONNECTOR_HDMI, CONNECTOR_POWER, DIR_NEG_X, DIR_POS_X


class HdmiDriver(Component):
    """HDMI-to-panel driver board."""

    name = "HDMI Driver Board"

    def __init__(self, display: dict[str, Any] | None = None) -> None:
        data = (display or {}).get("driver_board", {})
        self.width = float(data.get("width", 55.0))
        self.depth = float(data.get("depth", 45.5))
        self.height = float(data.get("height", 4.6))
        self.pcb_thickness = float(data.get("pcb_thickness", 1.3))
        self.offset_x = float(data.get("offset_x", 100.0))
        self.offset_y = float(data.get("offset_y", 5.0))

    def size(self) -> BoundingBox:
        return BoundingBox(self.width, self.depth, self.height)

    def mounting_holes(self) -> list[Hole]:
        # Three M3 holes at the NW/NE/SE corners, 3.0 mm inset, 3.0 mm dia.
        inset = 3.0
        half_w, half_d = self.width / 2, self.depth / 2
        return [
            Hole(-half_w + inset, half_d - inset, 3.0),
            Hole(half_w - inset, half_d - inset, 3.0),
            Hole(half_w - inset, -half_d + inset, 3.0),
        ]

    def connectors(self) -> list[Connector]:
        # Edge-to-center conversion, e.g. Mini-HDMI casing south side 5.8 from
        # the south edge (y=-22.75): y = -22.75 + 5.8 + 11.3/2 = -11.3; casing
        # protrudes 1.0 past the east edge (x=+27.5) and is 8.0 deep:
        # x = +27.5 + 1.0 - 8.0/2 = +24.5. z = PCB + opening height / 2.
        pcb = self.pcb_thickness
        return [
            # Mini-HDMI input — internal: mini-HDMI cable routed through the
            # hinge wire tunnel from the SBC, no shell cutout.
            Connector(
                type=CONNECTOR_HDMI,
                x=24.5,
                y=-11.3,
                z=pcb + 3.3 / 2,
                direction=DIR_POS_X,
                width=11.3,
                height=3.3,
                depth=8.0,
                internal=True,
            ),
            # USB Type-C power — north side 8.5 from north edge. Internal:
            # power cable routed with the mini-HDMI through the hinge.
            Connector(
                type=CONNECTOR_POWER,
                x=24.75,
                y=9.75,
                z=pcb + 3.3 / 2,
                direction=DIR_POS_X,
                width=9.0,
                height=3.3,
                depth=7.5,
                internal=True,
            ),
            # FPC slot to the panel — west side flush with west edge,
            # south side 3.0 from south edge. Internal: mates the folded
            # panel ribbon, no shell cutout.
            Connector(
                type="FPC",
                x=-24.5,
                y=-5.0,
                z=pcb + 1.0 / 2,
                direction=DIR_NEG_X,
                width=29.5,
                height=1.0,  # TODO: measure FPC slot opening height (1.0 assumed)
                depth=6.0,
                internal=True,
            ),
        ]

    def reference_origin(self) -> tuple[float, float, float]:
        # Driver board offset from the display center: along X to sit beside
        # the panel, along Y to line its FPC slot up with the panel's FPC.
        return (self.offset_x, self.offset_y, 0.0)

    def build(self):
        """Generate the driver board solid: PCB, socket blocks, mounting holes."""
        from utilities import cq_helpers

        cq_helpers.require_cq()
        pcb = cq_helpers.box_centered(self.width, self.depth, self.pcb_thickness)
        pcb = cq_helpers.translate(pcb, 0.0, 0.0, self.pcb_thickness / 2.0)

        # Socket blocks sit on top of the PCB at the connector positions.
        sockets = [
            (24.5, -11.3, 8.0, 11.3, 3.3),   # mini-HDMI (east)
            (24.75, 9.75, 7.5, 9.0, 3.3),    # USB-C power (east)
            (-24.5, -5.0, 6.0, 29.5, 1.0),   # FPC slot (west, flush on PCB)
        ]
        body = pcb
        for x, y, w, d, h in sockets:
            block = cq_helpers.box_centered(w, d, h)
            block = cq_helpers.translate(block, x, y, self.pcb_thickness + h / 2.0)
            body = body.union(block)

        for hole in self.mounting_holes():
            bore = cq_helpers.cylinder_centered(hole.diameter, self.height + 1.0)
            bore = cq_helpers.translate(bore, hole.x, hole.y, self.height / 2.0)
            body = body.cut(bore)
        return body
