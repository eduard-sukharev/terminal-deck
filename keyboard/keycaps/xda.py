"""XDA keycap profile — uniform spherical profile, all keys same shape.

Dimensions from the plan: base 18.5×18.5 mm square, top Ø15.0 mm circle,
9.0 mm tall.  Wide keys (width > 1u) use a stadium (rounded-rectangle) top
with the same 15.0 mm band and 7.5 mm corner radius.
"""

from __future__ import annotations

from typing import Any

from keyboard.registry import register_keycap


@register_keycap("xda")
class XdaKeycap:
    """XDA profile keycap — data only, no CadQuery."""

    def base_size(self) -> float:
        return 18.5

    def top_diameter(self) -> float:
        return 15.0

    def height(self) -> float:
        return 9.0

    def segments(self) -> int:
        return 32

    def metadata(self) -> dict[str, Any]:
        return {
            "profile": "xda",
            "base_size": 18.5,
            "top_diameter": 15.0,
            "height": 9.0,
            "segments": 32,
        }
