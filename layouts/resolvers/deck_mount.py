"""DeckMount resolver: tilts a component onto the sloped base deck."""

from __future__ import annotations

import math
from typing import Any

from layouts.base import Placement, rotated_footprint
from layouts.composer import ConstraintResolver, ResolverResult
from layouts.constraints import DeckMount


class DeckMountResolver:
    """Tilt a component to the deck slope, pivoting about its front-bottom edge.

    The base deck is a wedge (see ``case.base.Base.deck_level_at``): flat
    along the front edge, rising toward the rear. A part mounted on it picks
    up the same tilt. Pivoting about the front-bottom edge — rather than the
    component's center — is what keeps the front of the case at its original
    height while the rear opens up, which is the whole point of the wedge:
    a center pivot would drop the front by as much as it raises the rear.

    The tilt is read from ``config.deck.slope`` rather than the recipe, so
    one config value moves the deck and everything riding it together.
    """

    kind = "deck_mount"

    def resolve(
        self,
        constraint: DeckMount,
        components: dict[str, Any],
        current: dict[str, Placement],
        config: Any,
        context: dict[str, Any],
    ) -> ResolverResult:
        subj = components.get(constraint.subject)
        if subj is None:
            return ResolverResult(
                False, {}, f"component {constraint.subject!r} not found",
            )

        deck = getattr(config, "deck", None)
        slope = deck.slope if deck is not None else 0.0

        existing = current.get(constraint.subject)
        x = existing.x if existing is not None else 0.0
        y = existing.y if existing is not None else 0.0
        rotation = existing.rotation if existing is not None else 0.0
        flip_x = existing.flip_x if existing is not None else False

        # Negative tilt raises -Y (the rear), matching deck_level_at.
        tilt_x = -slope

        # Tilting about the origin drops the front edge by half the depth
        # times sin(slope); lift by that much to pin the front edge to
        # floor_z and send the whole rise to the rear instead.
        box = subj.size()
        _, eff_depth = rotated_footprint(box.width, box.depth, rotation)
        rise = (eff_depth / 2.0) * math.sin(math.radians(abs(slope)))
        z = constraint.floor_z + rise

        return ResolverResult(
            True,
            {constraint.subject: Placement(subj, x, y, rotation, z, flip_x, tilt_x)},
            f"{constraint.subject} on deck: tilt={tilt_x:g}°, "
            f"front edge @ z={constraint.floor_z:.1f} (origin z={z:.2f})",
        )


__all__ = ["DeckMountResolver"]
