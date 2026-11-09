"""RelativePlacement resolver: places a component at an explicit offset from another."""

from __future__ import annotations

import dataclasses
from typing import Any

from layouts.base import Placement
from layouts.composer import ConstraintResolver, ResolverResult
from layouts.constraints import RelativePlacement


class RelativePlacementResolver:
    """Place a component at a fixed offset from another component's origin."""

    kind = "relative_placement"

    def resolve(
        self,
        constraint: RelativePlacement,
        components: dict[str, Any],
        current: dict[str, Placement],
        config: Any,
        context: dict[str, Any],
    ) -> ResolverResult:
        subj = components.get(constraint.subject)
        if subj is None:
            return ResolverResult(
                False, {},
                f"component {constraint.subject!r} not found",
            )

        target_placement = current.get(constraint.target)
        if target_placement is None:
            return ResolverResult(
                False, {},
                f"target {constraint.target!r} not placed yet",
            )

        offset_x, offset_y, offset_z = (
            constraint.offset_x, constraint.offset_y, constraint.offset_z
        )
        source = "recipe offsets"
        if constraint.use_reference_origin:
            # Pass the target's own flip through: an override with a
            # direction-sensitive bias (UsbCPlug/MiniHdmiPlug centering a
            # symmetric body on a connector) needs to know, since the
            # world_offset transform below negates a flipped target's Z
            # component — see Component.reference_origin's docstring.
            ref_x, ref_y, ref_z = subj.reference_origin(flip=target_placement.flip_x)
            # The recipe still owns Z: reference_origin() describes the in-plane
            # mounting offset, not which side of the partner the board sits on.
            offset_x, offset_y = ref_x, ref_y
            offset_z = constraint.offset_z or ref_z
            source = "reference_origin()"

        # Route the offset through the target's own rotation/flip
        # (Placement.world_offset), not a flat addition: offset_x/offset_y/
        # offset_z (and reference_origin()) describe the offset in the
        # target's own local frame, the same as a connector position does.
        # A flat add only happens to agree with that for an unrotated,
        # unflipped target (every target this has been used against, until
        # a mated cable plug on the HDMI driver board needed one that is
        # rotated 180° *and* flipped) — for any other target it silently
        # places the subject off by the rotation/flip that never got
        # applied.
        #
        # from_top measures the gap from the target's highest occupied point
        # rather than its origin; swap in that datum before the transform
        # (rather than adding offset_z separately afterward) so rotation/flip
        # still apply consistently to reach it.
        datum_placement = (
            dataclasses.replace(target_placement, z=target_placement.z_bounds()[1])
            if constraint.from_top else target_placement
        )
        x, y, z = datum_placement.world_offset(offset_x, offset_y, offset_z)
        existing = current.get(constraint.subject)
        rotation = (
            constraint.rotation
            if constraint.rotation is not None
            else (existing.rotation if existing is not None else 0.0)
        )
        flip_x = (
            constraint.flip
            if constraint.flip is not None
            else (existing.flip_x if existing is not None else False)
        )
        return ResolverResult(
            True,
            {constraint.subject: Placement(subj, x, y, rotation, z, flip_x)},
            f"{constraint.subject} @ ({x:.1f}, {y:.1f}, {z:.1f}) "
            f"rel. to {constraint.target} via {source}",
        )


__all__ = ["RelativePlacementResolver"]
