"""Default resolver registry.

Every constraint kind has a working resolver. Resolvers split into two
groups: those that produce placements (``fixed_position``, ``centered_on``,
``centered_group``, ``edge_alignment``, ``relative_placement``, ``z_stack``,
``share_plane``) and those that only verify an already-resolved layout
(``clearance``, ``region``, ``cable_path``, ``port_access``,
``footprint_match``), plus ``target_envelope``, which publishes the enclosure
size the wall-relative resolvers align against.
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
from layouts.resolvers.port_access import PortAccessResolver
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
        "port_access": PortAccessResolver(),
        "region": RegionResolver(),
        "relative_placement": RelativePlacementResolver(),
        "share_plane": SharePlaneResolver(),
        "target_envelope": TargetEnvelopeResolver(),
        "z_stack": ZStackResolver(),
    }
    return real


__all__ = ["default_resolver_registry"]
