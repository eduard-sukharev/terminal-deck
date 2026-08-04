"""Key data model — purely descriptive, no geometry."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Key:
    """One key in the keyboard layout.

    All positions are in key units (1 unit = 19.05 mm). The layout parser
    converts KLE JSON rows into absolute positions. This object contains
    **no geometry** — it is purely descriptive.
    """

    x: float = 0.0
    y: float = 0.0
    width: float = 1.0
    height: float = 1.0
    rotation: float = 0.0
    rotation_x: float = 0.0
    rotation_y: float = 0.0
    legend: str = ""
    switch_type: str | None = None
    stabilizer_type: str | None = None
    switch_rotation: float | None = None
    stab_rotation: float | None = None
    kerf: float | None = None
