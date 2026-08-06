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
        context: dict[str, Any],
    ) -> ResolverResult:
        placements: dict[str, Placement] = {}
        current_z = 0.0
        missing: list[str] = []
        unplaced: list[str] = []

        for layer_names in constraint.layers:
            max_height = 0.0
            for name in layer_names:
                comp = components.get(name)
                if comp is None:
                    missing.append(name)
                    continue
                existing = current.get(name)
                if existing is None:
                    # Assigning (0, 0) here would silently invent a placement
                    # at the case center — the XY owner must run first.
                    unplaced.append(name)
                    continue
                placements[name] = Placement(
                    comp, existing.x, existing.y, existing.rotation, current_z,
                    existing.flip_x,
                )
                max_height = max(max_height, comp.size().height)
            current_z += max_height + constraint.gap

        if missing or unplaced:
            problems = []
            if missing:
                problems.append(f"unknown component(s): {', '.join(missing)}")
            if unplaced:
                problems.append(
                    f"no XY placement yet for: {', '.join(unplaced)}"
                )
            return ResolverResult(False, placements, "; ".join(problems))

        return ResolverResult(
            True,
            placements,
            f"z-stack: {len(constraint.layers)} layer(s), top at z={current_z:.1f}",
        )


__all__ = ["ZStackResolver"]
