"""Null stabilizer cutout — produces no geometry.

Useful for hand-wired builds with no stabilizers. Registering a "none" type
lets the config select ``stabilizer_cutout: none`` and the build function
returns ``None`` instead of a solid.
"""

from __future__ import annotations

from dataclasses import dataclass

from geometry.cutout_registry import register_stabilizer_cutout


@register_stabilizer_cutout("none")
@dataclass(frozen=True)
class NullStabilizerCutout:
    """No stabilizer cutout — produces no geometry.

    ``build_stabilizer_cutout`` returns ``None`` for this type.
    """

    @property
    def vertices(self):
        raise NotImplementedError(
            "NullStabilizerCutout has no vertices — the build function "
            "returns None for this type."
        )
