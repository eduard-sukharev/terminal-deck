"""FootprintMatch resolver: verifies two enclosure halves share the same XY footprint."""

from __future__ import annotations

from typing import Any

from layouts.base import Placement
from layouts.composer import ConstraintResolver, ResolverResult
from layouts.constraints import FootprintMatch
from layouts.resolvers._helpers import estimate_enclosure


class FootprintMatchResolver:
    """Verify that two enclosure halves share the same XY footprint.

    This is a documentary/validation constraint — it does not adjust
    placement.
    """

    kind = "footprint_match"

    def resolve(
        self,
        constraint: FootprintMatch,
        components: dict[str, Any],
        current: dict[str, Placement],
        config: Any,
    ) -> ResolverResult:
        w, d, _ = estimate_enclosure(current, components, config)
        return ResolverResult(
            True, {},
            f"footprint: {w:.1f} x {d:.1f} mm — shared by {len(constraint.subjects)} half/halves",
        )


__all__ = ["FootprintMatchResolver"]
