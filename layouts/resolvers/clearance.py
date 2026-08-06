"""Clearance resolver: enforces minimum gap between component solid volumes."""

from __future__ import annotations

from typing import Any

from layouts.base import Placement
from layouts.composer import ConstraintResolver, ResolverResult
from layouts.constraints import Clearance


def _separation(ca: float, sa: float, cb: float, sb: float) -> float:
    """Signed gap between two 1-D spans given their centers and sizes."""
    return abs(ca - cb) - (sa + sb) / 2.0


class ClearanceResolver:
    """Verify a minimum gap between two components.

    Both components are compared through :meth:`Component.occupied_volumes`,
    so a part tucked into a hollow region — for example under the keyboard's
    raised switch plate — is measured against the sub-volumes that are
    actually solid rather than against the overall bounding box.

    Two boxes are clear when they are separated by at least *gap* on any one
    axis; the reported gap is the worst such separation over every pair of
    sub-volumes. This reports violations rather than moving anything: the
    placement belongs to whichever constraint set it.
    """

    kind = "clearance"

    def resolve(
        self,
        constraint: Clearance,
        components: dict[str, Any],
        current: dict[str, Placement],
        config: Any,
        context: dict[str, Any],
    ) -> ResolverResult:
        subj = components.get(constraint.subject)
        target = components.get(constraint.target)
        subj_placement = current.get(constraint.subject)
        target_placement = current.get(constraint.target)

        if subj is None or target is None:
            missing = constraint.subject if subj is None else constraint.target
            return ResolverResult(False, {}, f"component {missing!r} not found")
        if subj_placement is None or target_placement is None:
            unplaced = (
                constraint.subject if subj_placement is None else constraint.target
            )
            return ResolverResult(
                False, {},
                f"{unplaced!r} not placed before this clearance check",
            )

        axis_index = {"x": 0, "y": 1, "z": 2}.get(constraint.axis or "")

        worst: float | None = None
        for ax, ay, az, abox in subj.occupied_volumes():
            for bx, by, bz, bbox in target.occupied_volumes():
                # World-frame volume centers (rotation + flip aware).
                sx, sy, sz = subj_placement.world_offset(ax, ay, az)
                tx, ty, tz = target_placement.world_offset(bx, by, bz)
                # Flipped components hang below their origin.
                if subj_placement.flip_x:
                    sz -= abox.height / 2.0
                else:
                    sz += abox.height / 2.0
                if target_placement.flip_x:
                    tz -= bbox.height / 2.0
                else:
                    tz += bbox.height / 2.0
                seps = (
                    _separation(sx, abox.width, tx, bbox.width),
                    _separation(sy, abox.depth, ty, bbox.depth),
                    _separation(sz, abox.height, tz, bbox.height),
                )
                pair_gap = seps[axis_index] if axis_index is not None else max(seps)
                worst = pair_gap if worst is None else min(worst, pair_gap)

        if worst is None:
            return ResolverResult(False, {}, "no solid volumes to compare")

        axis_label = f" on {constraint.axis}" if constraint.axis else ""
        if worst >= constraint.gap:
            return ResolverResult(
                True, {},
                f"{constraint.subject}↔{constraint.target} gap{axis_label}="
                f"{worst:.2f} >= {constraint.gap}",
            )
        return ResolverResult(
            False, {},
            f"{constraint.subject}↔{constraint.target} gap{axis_label}="
            f"{worst:.2f} < {constraint.gap} required",
        )


__all__ = ["ClearanceResolver"]
