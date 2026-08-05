"""TargetEnvelope resolver: records the enclosure size hint (documentary only)."""

from __future__ import annotations

from typing import Any

from layouts.composer import ConstraintResolver, ResolverResult
from layouts.constraints import TargetEnvelope


class TargetEnvelopeResolver:
    """Publish the target enclosure size for later resolvers to align against.

    Produces no placements. Declaring this first makes every wall-relative
    constraint deterministic: ``edge_alignment``, ``centered_on`` and
    ``region`` otherwise estimate the enclosure from whatever is already
    placed, which changes as the recipe proceeds.
    """

    kind = "target_envelope"

    def resolve(
        self,
        constraint: TargetEnvelope,
        components: dict[str, Any],
        current: dict[str, Any],
        config: Any,
        context: dict[str, Any],
    ) -> ResolverResult:
        if constraint.width is None or constraint.depth is None:
            return ResolverResult(
                False, {},
                "target_envelope needs both width and depth to pin the walls",
            )

        context["envelope"] = (constraint.width, constraint.depth, constraint.height)
        dims = (
            f"{constraint.width} x {constraint.depth} x "
            f"{constraint.height if constraint.height is not None else '?'}"
        )
        return ResolverResult(
            True,
            {},
            f"target envelope: {dims} mm",
        )


__all__ = ["TargetEnvelopeResolver"]
