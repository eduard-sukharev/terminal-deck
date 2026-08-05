"""Constraint dataclass hierarchy for declarative layout composition.

Each constraint declares a geometric relationship between components (or
between a component and the enclosure). Constraints are pure data — they
contain no logic. Resolvers in ``layouts/resolvers/`` interpret them.

Priority semantics:
    HARD — must be satisfied; violation stops the build.
    SOFT — should be satisfied; violation logs a warning.
    GOAL — optimization target; metric reported, no error.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum


class ConstraintPriority(IntEnum):
    HARD = 0
    SOFT = 1
    GOAL = 2


@dataclass(frozen=True)
class Constraint:
    kind: str = field(default="constraint", init=False)
    priority: ConstraintPriority = ConstraintPriority.HARD
    description: str = ""


# ── concrete constraint types ──────────────────────────────────────────


@dataclass(frozen=True, kw_only=True)
class EdgeAlignment(Constraint):
    """Align an edge of *subject* to an edge of *target* (or the enclosure).

    Parameters
    ----------
    subject : str
        Component name (key in the components dict).
    subject_edge : str
        One of ``"front"``, ``"rear"``, ``"left"``, ``"right"``.
    target : str
        Component name or ``"enclosure"``.
    target_edge : str
        One of ``"front"``, ``"rear"``, ``"left"``, ``"right"``.
    offset : float
        Extra gap between the two edges (mm). Positive = outward from
        *subject*.
    """
    kind: str = field(default="edge_alignment", init=False)
    subject: str
    subject_edge: str
    target: str
    target_edge: str
    offset: float = 0.0


@dataclass(frozen=True, kw_only=True)
class CenteredOn(Constraint):
    """Center *subject* on one or more axes within a region.

    Parameters
    ----------
    subject : str
        Component name.
    axes : tuple[str, ...]
        Axes to center on, e.g. ``("x",)`` or ``("x", "y")``.
    relative_to : str or None
        Component name or ``"enclosure"``. ``None`` means the enclosure
        interior.
    """
    kind: str = field(default="centered_on", init=False)
    subject: str
    axes: tuple[str, ...]
    relative_to: str | None = None


@dataclass(frozen=True, kw_only=True)
class KeyboardMountingHoles(Constraint):
    """Position mounting holes between keyboard rows, near wide keys.

    Two holes on the left side (between row 0-1 and row 2-3) and two on
    the right side, placed in gaps near wide keys (>1u).

    The resolver reads the keyboard layout (keys, pitch) and computes
    positions that avoid switch/stabilizer cutouts.
    """
    kind: str = field(default="keyboard_mounting_holes", init=False)
    subject: str = "keyboard"
    screw_diameter: float | None = None  # None = use component default


@dataclass(frozen=True, kw_only=True)
class FixedPosition(Constraint):
    """Set a component's position directly.

    Only the specified axes are set; ``None`` leaves the current value
    unchanged (or defaults to 0 if no prior placement exists).
    """
    kind: str = field(default="fixed_position", init=False)
    subject: str
    x: float | None = None
    y: float | None = None
    z: float | None = None
    rotation: float = 0.0


@dataclass(frozen=True, kw_only=True)
class CenteredGroup(Constraint):
    """Center a group of components on one or more axes.

    The group's collective bounding box is centered on the specified axes.
    Each component is shifted by the same delta so the group midpoint
    aligns with the target center.

    Parameters
    ----------
    subjects : list[str]
        Component names in the group.
    axes : tuple[str, ...]
        Axes to center on, e.g. ``("y",)`` or ``("x", "y")``.
    relative_to : str or None
        Component name or ``"enclosure"``. ``None`` means the enclosure
        interior.
    """
    kind: str = field(default="centered_group", init=False)
    subjects: list[str]
    axes: tuple[str, ...]
    relative_to: str | None = None


@dataclass(frozen=True, kw_only=True)
class Clearance(Constraint):
    """Minimum gap between two components' keepout volumes.

    Parameters
    ----------
    subject : str
        Component name.
    target : str
        Component name.
    gap : float
        Minimum distance (mm).
    axis : str or None
        ``None`` = 3D clearance; ``"x"``, ``"y"``, or ``"z"`` for
        axis-specific.
    """
    kind: str = field(default="clearance", init=False)
    subject: str
    target: str
    gap: float
    axis: str | None = None


@dataclass(frozen=True, kw_only=True)
class ZStack(Constraint):
    """Stacking order with Z-gaps between layers.

    Parameters
    ----------
    layers : list[list[str]]
        Ordered list of layers, each a list of component names in that
        layer. Layer 0 is the bottom (z=0).
    gap : float
        Vertical gap between adjacent layers (mm).
    """
    kind: str = field(default="z_stack", init=False)
    layers: list[list[str]]
    gap: float = 0.0


@dataclass(frozen=True, kw_only=True)
class SharePlane(Constraint):
    """Components share the same Z mounting plane."""
    kind: str = field(default="share_plane", init=False)
    subjects: list[str]
    plane_z: float = 0.0


@dataclass(frozen=True, kw_only=True)
class RegionConstraint(Constraint):
    """Component must lie within a named region of the enclosure interior.

    Parameters
    ----------
    subject : str
        Component name.
    region : str
        One of ``"upper_half"``, ``"lower_half"``, ``"front_third"``,
        ``"rear_wall"``, etc.
    margin : float
        Inset from the region boundary (mm).
    """
    kind: str = field(default="region", init=False)
    subject: str
    region: str
    margin: float = 0.0


@dataclass(frozen=True, kw_only=True)
class CablePath(Constraint):
    """Cable route between connectors with straight-line passage.

    Parameters
    ----------
    from_component : str
        Source component name.
    from_connector_type : str
        Connector type identifier (see ``utilities.constants``).
    to_component : str
        Destination component name.
    to_connector_type : str
        Connector type identifier.
    via_point : tuple[float, float, float] or None
        Intermediate point the cable must pass through (e.g. hinge tunnel
        center). ``None`` = direct line.
    clearance_diameter : float
        Minimum tunnel/opening diameter for the cable bundle (mm).
    max_bend_radius : float
        Maximum allowed bend radius (mm). Larger = gentler bend.
    """
    kind: str = field(default="cable_path", init=False)
    from_component: str
    from_connector_type: str
    to_component: str
    to_connector_type: str
    via_point: tuple[float, float, float] | None = None
    clearance_diameter: float = 8.0
    max_bend_radius: float = 30.0


@dataclass(frozen=True, kw_only=True)
class FootprintMatch(Constraint):
    """Two enclosure halves must share the same XY footprint."""
    kind: str = field(default="footprint_match", init=False)
    subjects: tuple[str, ...]


@dataclass(frozen=True, kw_only=True)
class RelativePlacement(Constraint):
    """Component placed relative to another with explicit offset.

    Parameters
    ----------
    subject : str
        Component to place.
    target : str
        Reference component.
    offset_x : float
        X offset from *target* origin (mm).
    offset_y : float
        Y offset from *target* origin (mm).
    offset_z : float
        Z offset from *target* origin (mm).
    rotation : float
        Rotation about Z (degrees).
    """
    kind: str = field(default="relative_placement", init=False)
    subject: str
    target: str
    offset_x: float = 0.0
    offset_y: float = 0.0
    offset_z: float = 0.0
    rotation: float = 0.0


@dataclass(frozen=True, kw_only=True)
class TargetEnvelope(Constraint):
    """Expected enclosure size (optional hint for region constraints).

    When a region constraint (e.g. ``"upper_half"``) runs before the
    enclosure size is known, this hint provides the bounds. If omitted,
    the composer estimates from placed-so-far components.
    """
    kind: str = field(default="target_envelope", init=False)
    width: float | None = None
    depth: float | None = None
    height: float | None = None


__all__ = [
    "ConstraintPriority",
    "Constraint",
    "EdgeAlignment",
    "FixedPosition",
    "KeyboardMountingHoles",
    "CenteredOn",
    "CenteredGroup",
    "Clearance",
    "ZStack",
    "SharePlane",
    "RegionConstraint",
    "CablePath",
    "FootprintMatch",
    "RelativePlacement",
    "TargetEnvelope",
]
