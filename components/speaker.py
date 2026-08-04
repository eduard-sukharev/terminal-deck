"""Small mono speaker for the debug beeper / alert audio.

Optional component (``speaker.present`` in ``config/hardware.yaml``).
Dimensions from the ``speaker`` section.
"""

from __future__ import annotations

from typing import Any

from components.base import BoundingBox, Component, Hole


class Speaker(Component):
    """Round mono speaker."""

    name = "Speaker"

    def __init__(self, hardware: dict[str, Any] | None = None) -> None:
        data = (hardware or {}).get("speaker", {})
        self.present = bool(data.get("present", True))
        self.diameter = float(data.get("diameter", 20.0))
        self.height = float(data.get("height", 6.0))

    def size(self) -> BoundingBox:
        if not self.present:
            return BoundingBox(0.1, 0.1, 0.1)
        return BoundingBox(self.diameter, self.diameter, self.height)

    def mounting_holes(self) -> list[Hole]:
        # TODO: measure mounting ear positions.
        return [
            Hole(-self.diameter / 4, -self.diameter / 4, 2.0),
            Hole(self.diameter / 4, -self.diameter / 4, 2.0),
            Hole(self.diameter / 4, self.diameter / 4, 2.0),
            Hole(-self.diameter / 4, self.diameter / 4, 2.0),
        ]
