"""Heat-set insert component.

Thin wrapper over the fastener library (:mod:`utilities.fasteners`) exposing
the insert through the Component API so the boss generator and validation can
treat it uniformly. The physical insert is not modeled as solid CAD — the boss
generator uses ``size()`` and ``printed_hole_diameter`` to cut the socket.
"""

from __future__ import annotations

from typing import Any

from components.base import BoundingBox, Component
from utilities.fasteners import HeatInsert, heat_insert


class HeatSetInsert(Component):
    """A brass heat-set insert sized by thread designation."""

    name = "Heat-Set Insert"

    def __init__(self, size: str = "M2.5", config: Any | None = None) -> None:
        """Create an insert.

        Parameters
        ----------
        size : str
            Thread designation the insert accepts ("M2", "M2.5", "M3").
        config : optional
            Build configuration; ``clearance.insert`` overrides the library
            hole clearance when provided.
        """
        self._insert: HeatInsert = heat_insert(size)
        if config is not None and hasattr(config, "clearance"):
            self._insert = HeatInsert(
                size=self._insert.size,
                outside_diameter=self._insert.outside_diameter,
                depth=self._insert.depth,
                hole_clearance=float(config.clearance.insert),
            )

    def size(self) -> BoundingBox:
        return BoundingBox(
            self._insert.outside_diameter,
            self._insert.outside_diameter,
            self._insert.depth,
        )

    @property
    def printed_hole_diameter(self) -> float:
        """Diameter of the boss hole to print for this insert (mm)."""
        return self._insert.printed_hole_diameter
