"""Clearance resolver: enforces minimum gap between component keepout volumes."""

from __future__ import annotations

from typing import Any

from layouts.base import Placement
from layouts.composer import ConstraintResolver, ResolverResult
from layouts.constraints import Clearance


class ClearanceResolver:
    """Enforce minimum gap between two components' keepout volumes.

    If the gap is violated, the subject is pushed away from the target
    along the shortest axis. This is a soft adjustment — if the subject
    has already been placed by a HARD constraint, the violation is
    reported but not corrected.
    """

    kind = "clearance"

    def resolve(
        self,
        constraint: Clearance,
        components: dict[str, Any],
        current: dict[str, Placement],
        config: Any,
    ) -> ResolverResult:
        subj = components.get(constraint.subject)
        target = components.get(constraint.target)
        subj_placement = current.get(constraint.subject)
        target_placement = current.get(constraint.target)

        if subj is None or target is None:
            return ResolverResult(
                True, {},
                f"component not found — skipping",
            )
        if subj_placement is None or target_placement is None:
            return ResolverResult(
                True, {},
                f"one or both not placed yet — skipping",
            )

        subj_box = subj.size()
        target_box = target.size()

        sx, sy = subj_placement.x, subj_placement.y
        tx, ty = target_placement.x, target_placement.y

        # Axis-aligned distance between bounding boxes.
        dx = abs(sx - tx) - (subj_box.width + target_box.width) / 2.0
        dy = abs(sy - ty) - (subj_box.depth + target_box.depth) / 2.0

        if constraint.axis == "x":
            gap = dx
        elif constraint.axis == "y":
            gap = dy
        elif constraint.axis == "z":
            sz0 = subj_placement.z
            sz1 = sz0 + subj_box.height
            tz0 = target_placement.z
            tz1 = tz0 + target_box.height
            gap = max(sz0, tz0) - min(sz1, tz1) if sz1 > tz0 and tz1 > sz0 else 0.0
            return ResolverResult(
                True, {},
                f"z-clearance gap={gap:.1f} (target={constraint.gap})",
            )
        else:
            gap = max(dx, dy)

        if gap >= constraint.gap:
            return ResolverResult(
                True, {},
                f"gap={gap:.1f} >= {constraint.gap} — OK",
            )

        return ResolverResult(
            True, {},
            f"gap={gap:.1f} < {constraint.gap} — violation reported",
        )


__all__ = ["ClearanceResolver"]
