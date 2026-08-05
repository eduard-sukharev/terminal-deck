"""TargetEnvelope resolver: records the enclosure size hint (documentary only)."""

from __future__ import annotations

from typing import Any

from layouts.composer import ConstraintResolver, ResolverResult
from layouts.constraints import TargetEnvelope


class TargetEnvelopeResolver:
    """Accept a TargetEnvelope hint. Produces no placements."""

    kind = "target_envelope"

    def resolve(
        self,
        constraint: TargetEnvelope,
        components: dict[str, Any],
        current: dict[str, Any],
        config: Any,
    ) -> ResolverResult:
        dims = (
            f"{constraint.width or '?'} x {constraint.depth or '?'} x {constraint.height or '?'}"
        )
        return ResolverResult(
            True,
            {},
            f"target envelope: {dims} mm",
        )


__all__ = ["TargetEnvelopeResolver"]
