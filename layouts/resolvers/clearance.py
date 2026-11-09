"""Clearance resolver: enforces minimum gap between component solid volumes."""

from __future__ import annotations

from typing import Any

from layouts.base import Placement, volume_footprint, volume_z_span
from layouts.composer import ConstraintResolver, ResolverResult
from layouts.constraints import Clearance


def _separation(ca: float, sa: float, cb: float, sb: float) -> float:
    """Signed gap between two 1-D spans given their centers and sizes."""
    return abs(ca - cb) - (sa + sb) / 2.0


def _span_gap(a0: float, a1: float, b0: float, b1: float) -> float:
    """Signed gap between two 1-D intervals given their raw bounds.

    Unlike :func:`_separation`, this does not assume the interval is
    symmetric about a center — needed for Z, where a
    :func:`layouts.base.volume_z_span`) can widen a sub-volume's Z-span
    asymmetrically. Using ``_separation`` with a naive center+height for a
    volume understates how far it actually reaches, letting a
    clearance check pass that the equivalent collision check would catch.
    """
    return max(a0 - b1, b0 - a1)


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
                aw, ad = volume_footprint(subj_placement, abox)
                bw, bd = volume_footprint(target_placement, bbox)
                az0, az1 = volume_z_span(subj_placement, abox, sz)
                bz0, bz1 = volume_z_span(target_placement, bbox, tz)
                seps = (
                    _separation(sx, aw, tx, bw),
                    _separation(sy, ad, ty, bd),
                    _span_gap(az0, az1, bz0, bz1),
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
