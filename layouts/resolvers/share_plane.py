"""SharePlane resolver: ensures components share the same Z mounting plane."""

from __future__ import annotations

from typing import Any

from layouts.base import Placement
from layouts.composer import ConstraintResolver, ResolverResult
from layouts.constraints import SharePlane


class SharePlaneResolver:
    """Set all subjects to the same Z plane."""

    kind = "share_plane"

    def resolve(
        self,
        constraint: SharePlane,
        components: dict[str, Any],
        current: dict[str, Placement],
        config: Any,
    ) -> ResolverResult:
        placements: dict[str, Placement] = {}
        for name in constraint.subjects:
            comp = components.get(name)
            if comp is None:
                continue
            existing = current.get(name)
            x = existing.x if existing is not None else 0.0
            y = existing.y if existing is not None else 0.0
            rot = existing.rotation if existing is not None else 0.0
            placements[name] = Placement(comp, x, y, rot, constraint.plane_z)

        return ResolverResult(
            True,
            placements,
            f"{len(placements)} component(s) on z={constraint.plane_z}",
        )


__all__ = ["SharePlaneResolver"]
