"""8.8" ultrawide display module (1920x480 LCD + glass).

Verified against the HannStar HSD088IPW1-A00 panel and measured by hand.

Measured (user, calipers, mm):
* module outline: 231.0 x 64.5 x 6.5 (active area 218.88 x 54.72, datasheet)
* FPC ribbon: 38.5 mm wide, centered on a short edge (13 mm margin each side)
* mounting holes: NONE — the panel is held by the lid bezel

Orientation: the panel ships with its ribbon on a short edge ("bottom" in the
vendor's default portrait 480x1920 framing). This build mounts it landscape
(1920 wide, 231.0 mm across). The ribbon exits the east (+X) short edge, then
folds back immediately behind the panel — so the mating connector behind the
panel faces west, toward the driver board's west FPC slot. The driver board
mounts back-to-back behind the LCD (see ``components/hdmi_driver.py``). The FPC
connection is internal (no shell cutout).

The glass recess and bezel live in the lid (``case/lid.py``); this module
describes the physical panel and its FPC.
"""

from __future__ import annotations

from typing import Any

from components.base import BoundingBox, Component, Connector, Hole
from utilities.constants import DIR_POS_X


class Display88(Component):
    """8.8" 1920x480 ultrawide LCD panel module."""

    name = "Display 8.8\" 1920x480"

    def __init__(self, display: dict[str, Any] | None = None) -> None:
        data = display or {}
        self.width = float(data.get("width", 231.0))
        self.height = float(data.get("height", 64.5))
        self.thickness = float(data.get("thickness", 6.5))
        self.active_width = float(data.get("active_width", 218.88))
        self.active_height = float(data.get("active_height", 54.72))
        flex = data.get("flex", {})
        self._flex_width = float(flex.get("width", 38.5))
        self._flex_thickness = float(flex.get("thickness", 1.0))
        self._flex_fold = float(flex.get("fold", 6.0))

    def size(self) -> BoundingBox:
        return BoundingBox(self.width, self.height, self.thickness)

    def mounting_holes(self) -> list[Hole]:
        # The panel has no mounting holes — it is held by the lid bezel.
        return []

    def connectors(self) -> list[Connector]:
        # The ribbon exits the east short edge in this (landscape) mounting and
        # folds back behind the panel; the connection to the driver board is
        # internal (no shell cutout).
        return [
            Connector(
                type="FPC",
                x=self.width / 2,
                y=0.0,
                z=self.thickness / 2,
                direction=DIR_POS_X,
                width=self._flex_width,
                height=self._flex_thickness,
                depth=self._flex_fold,
                internal=True,
            )
        ]

    def build(self):
        """Generate the panel solid (module outline only; glass bezel lives in
        the lid).

        The solid is bottom-aligned at the local origin (z from 0 to
        ``thickness``), matching every other component and the data-layer
        convention that ``Placement.z`` is the component bottom.
        """
        from utilities import cq_helpers

        cq_helpers.require_cq()
        box = cq_helpers.box_centered(self.width, self.height, self.thickness)
        return cq_helpers.translate(box, 0.0, 0.0, self.thickness / 2.0)
