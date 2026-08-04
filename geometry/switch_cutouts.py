"""Built-in switch cutout types beyond the canonical MX notched polygon.

Each type is a frozen dataclass with a ``vertices`` property, registered
with :func:`~geometry.cutout_registry.register_switch_cutout`.
"""

from __future__ import annotations

from dataclasses import dataclass

from geometry.cutout_registry import register_switch_cutout


@register_switch_cutout("mx-basic")
@dataclass(frozen=True)
class MxBasicSwitchCutout:
    """Plain 14×14 mm square — no notches, for lasercut plates."""
    width: float = 14.0

    @property
    def vertices(self) -> list[tuple[float, float]]:
        hw = self.width / 2.0
        return [(-hw, -hw), (hw, -hw), (hw, hw), (-hw, hw)]


@register_switch_cutout("alps")
@dataclass(frozen=True)
class AlpsSwitchCutout:
    """Alps SKCM/SKCL switch cutout: 15.5×12.8 mm with corner notches."""
    width: float = 15.5
    depth: float = 12.8
    notch: float = 2.0

    @property
    def vertices(self) -> list[tuple[float, float]]:
        hw = self.width / 2.0
        hd = self.depth / 2.0
        n = self.notch
        return [
            ( hw,  hd), (-hw,  hd), (-hw,  n), (-n,   n),
            (-n,  -n), (-hw, -n),  (-hw, -hd), ( hw, -hd),
            ( hw, -n), ( n,  -n),  ( n,   n),  ( hw,  n),
        ]


@register_switch_cutout("choc")
@dataclass(frozen=True)
class ChocSwitchCutout:
    """Kailh Choc v1 (PG1350) cutout: 14×14 mm with shallower notches."""
    width: float = 14.0
    notch: float = 3.0

    @property
    def vertices(self) -> list[tuple[float, float]]:
        hw = self.width / 2.0
        n = self.notch
        return [
            ( hw,  hw), (-hw,  hw), (-hw,  n), (-n,   n),
            (-n,  -n), (-hw, -n),  (-hw, -hw), ( hw, -hw),
            ( hw, -n), ( n,  -n),  ( n,   n),  ( hw,  n),
        ]
