"""Default resolver registry.

Phase 1: real resolvers for EdgeAlignment, CenteredOn, and ZStack.
Remaining constraints still use stubs.
"""

from __future__ import annotations

from layouts.composer import ConstraintResolver
from layouts.resolvers.cable_path import CablePathResolver
from layouts.resolvers.centered_group import CenteredGroupResolver
from layouts.resolvers.centered_on import CenteredOnResolver
from layouts.resolvers.clearance import ClearanceResolver
from layouts.resolvers.edge_alignment import EdgeAlignmentResolver
from layouts.resolvers.fixed_position import FixedPositionResolver
from layouts.resolvers.footprint_match import FootprintMatchResolver
from layouts.resolvers.keyboard_mounting_holes import KeyboardMountingHolesResolver
from layouts.resolvers.region import RegionResolver
from layouts.resolvers.relative_placement import RelativePlacementResolver
from layouts.resolvers.share_plane import SharePlaneResolver
from layouts.resolvers.target_envelope import TargetEnvelopeResolver
from layouts.resolvers.z_stack import ZStackResolver


def default_resolver_registry() -> dict[str, ConstraintResolver]:
    """Return the default resolver registry."""
    real: dict[str, ConstraintResolver] = {
        "cable_path": CablePathResolver(),
        "centered_group": CenteredGroupResolver(),
        "centered_on": CenteredOnResolver(),
        "clearance": ClearanceResolver(),
        "edge_alignment": EdgeAlignmentResolver(),
        "fixed_position": FixedPositionResolver(),
        "footprint_match": FootprintMatchResolver(),
        "keyboard_mounting_holes": KeyboardMountingHolesResolver(),
        "region": RegionResolver(),
        "relative_placement": RelativePlacementResolver(),
        "share_plane": SharePlaneResolver(),
        "target_envelope": TargetEnvelopeResolver(),
        "z_stack": ZStackResolver(),
    }
    return real


__all__ = ["default_resolver_registry"]
