"""Internal battery cell.

The sealed deck carries its own power source; the only external connectivity
is the rear USB hub. Dimensions from ``config/hardware.yaml`` (``battery``
section). Until a cell is chosen, the outline is an assumed box carrying a
``TODO: measure`` marker; the keepout reserves the compartment space.
"""

from __future__ import annotations

from typing import Any

from components.base import BoundingBox, Component, Keepout


class Battery(Component):
    """Internal lithium cell (box outline)."""

    name = "Battery"

    def __init__(self, hardware: dict[str, Any] | None = None) -> None:
        data = (hardware or {}).get("battery", {})
        self.width = float(data.get("width", 60.0))
        self.depth = float(data.get("depth", 35.0))
        self.height = float(data.get("height", 8.0))
        self.clearance = float(data.get("clearance", 2.0))

    def size(self) -> BoundingBox:
        return BoundingBox(self.width, self.depth, self.height)

    def keepout(self) -> Keepout:
        # The compartment reserves the cell outline plus a wiring margin.
        c = self.clearance
        return Keepout(self.width + 2 * c, self.depth + 2 * c, self.height + c)

    def build(self):
        """Generate the cell solid: a plain box, bottom-aligned at the origin."""
        from utilities import cq_helpers

        cq_helpers.require_cq()
        box = cq_helpers.box_centered(self.width, self.depth, self.height)
        return cq_helpers.translate(box, 0.0, 0.0, self.height / 2.0)
