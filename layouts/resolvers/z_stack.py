"""ZStack resolver: assigns Z heights to component layers."""

from __future__ import annotations

from typing import Any

from layouts.base import Placement
from layouts.composer import ConstraintResolver, ResolverResult
from layouts.constraints import ZStack


class ZStackResolver:
    """Assign Z stacking heights to layers of components.

    Layer 0 sits at z=0. Each subsequent layer sits above the tallest
    component in the previous layer plus the configured gap.
    """

    kind = "z_stack"

    def resolve(
        self,
        constraint: ZStack,
        components: dict[str, Any],
        current: dict[str, Placement],
        config: Any,
    ) -> ResolverResult:
        placements: dict[str, Placement] = {}
        current_z = 0.0

        for layer_idx, layer_names in enumerate(constraint.layers):
            max_height = 0.0
            for name in layer_names:
                comp = components.get(name)
                if comp is None:
                    continue
                box = comp.size()
                existing = current.get(name)
                x = existing.x if existing is not None else 0.0
                y = existing.y if existing is not None else 0.0
                rotation = existing.rotation if existing is not None else 0.0
                placements[name] = Placement(comp, x, y, rotation, current_z)
                max_height = max(max_height, box.height)
            current_z += max_height + constraint.gap

        return ResolverResult(
            True,
            placements,
            f"z-stack: {len(constraint.layers)} layer(s), top at z={current_z:.1f}",
        )


__all__ = ["ZStackResolver"]
