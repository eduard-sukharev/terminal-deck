"""Built-in stabilizer cutout types beyond the basic 7×15 mm slot.

Each type is a frozen dataclass with a ``vertices`` property, registered
with :func:`~geometry.cutout_registry.register_stabilizer_cutout`.
"""

from __future__ import annotations

from dataclasses import dataclass

from geometry.cutout_registry import register_stabilizer_cutout


@register_stabilizer_cutout("mx-tight")
@dataclass(frozen=True)
class StabilizerTightCutout:
    """Tighter stabilizer slot for reduced wobble: 6.5×14.5 mm."""
    width: float = 6.5
    height: float = 14.5

    @property
    def vertices(self) -> list[tuple[float, float]]:
        hw = self.width / 2.0
        hh = self.height / 2.0
        return [(-hw, -hh), (hw, -hh), (hw, hh), (-hw, hh)]


@register_stabilizer_cutout("mx-spec")
@dataclass(frozen=True)
class StabilizerSpecCutout:
    """Exact Cherry MX spec stabilizer slot with chamfered inner corners.

    Uses an 8-vertex polygon with corner chamfers rather than a plain
    rectangle, matching the official Cherry MX datasheet.
    """
    width: float = 7.0
    height: float = 15.0
    chamfer: float = 1.0

    @property
    def vertices(self) -> list[tuple[float, float]]:
        hw = self.width / 2.0
        hh = self.height / 2.0
        c = self.chamfer
        return [
            (-hw, -hh), ( hw - c, -hh), ( hw, -hh + c),
            ( hw,  hh - c), ( hw - c,  hh), (-hw + c,  hh),
            (-hw,  hh - c), (-hw, -hh + c),
        ]
