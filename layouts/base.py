"""Layout engine base.

A layout contains NO CAD — only placements. Placing a component records its
position and rotation; assembly and enclosure derive geometry from the
resulting placements.

Coordinate convention: +X right, +Y forward, +Z upward, origin at center of
the base.
"""

from __future__ import annotations

import math
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from components.base import Component


def rotated_footprint(width: float, depth: float, rotation: float) -> tuple[float, float]:
    """Axis-aligned world-frame ``(width, depth)`` of a box rotated about Z.

    A 90°/270° rotation swaps which physical dimension faces which world
    axis (e.g. a 65x30 mm board rotated 90° occupies 30 mm in X and 65 mm in
    Y) — this is the general form of that swap, exact at any angle. Used
    everywhere a placement's own ``rotation`` must be accounted for before
    comparing its footprint to a wall or another component.
    """
    rad = math.radians(rotation)
    eff_w = abs(width * math.cos(rad)) + abs(depth * math.sin(rad))
    eff_d = abs(width * math.sin(rad)) + abs(depth * math.cos(rad))
    return eff_w, eff_d


def volume_extents(placement: "Placement", box: Any) -> tuple[float, float, float]:
    """World-frame ``(width, depth, height)`` of one sub-volume under a
    placement's transform.

    A Z rotation swaps width/depth; a ``tilt_x`` mixes depth and height into
    each other, so both grow. Every consumer that compares boxes in world
    space (collisions, clearances, the enclosure envelope) sizes them through
    here rather than reading the raw component box.
    """
    eff_w, eff_d = rotated_footprint(box.width, box.depth, placement.rotation)
    eff_h = box.height
    if placement.tilt_x:
        rad = math.radians(placement.tilt_x)
        cos_t, sin_t = abs(math.cos(rad)), abs(math.sin(rad))
        eff_d, eff_h = (
            eff_d * cos_t + eff_h * sin_t,
            eff_d * sin_t + eff_h * cos_t,
        )
    return eff_w, eff_d, eff_h


def volume_footprint(placement: "Placement", box: Any) -> tuple[float, float]:
    """World-frame XY extent of one sub-volume (see :func:`volume_extents`)."""
    eff_w, eff_d, _ = volume_extents(placement, box)
    return eff_w, eff_d


def volume_z_span(
    placement: "Placement", box: Any, center_z: float
) -> tuple[float, float]:
    """World-frame Z range of one sub-volume whose transformed origin sits at
    ``center_z``.

    Flipped volumes hang below that origin instead of rising from it; a tilt
    swings part of the volume's depth into Z, widening the span symmetrically.
    """
    z0, z1 = (
        (center_z - box.height, center_z) if placement.flip_x
        else (center_z, center_z + box.height)
    )
    if not placement.tilt_x:
        return (z0, z1)
    _, depth = rotated_footprint(box.width, box.depth, placement.rotation)
    half = abs(depth / 2.0 * math.sin(math.radians(placement.tilt_x)))
    return (z0 - half, z1 + half)


@dataclass(frozen=True)
class Placement:
    """A single component placed in the world frame.

    Attributes
    ----------
    component : Component
        The placed component.
    x : float
        Component origin X in the world frame (mm).
    y : float
        Component origin Y in the world frame (mm).
    rotation : float
        Rotation about Z in degrees (0 = forward along +Y).
    z : float
        Component origin Z in the world frame (mm). Defaults to 0; the
        assembly stage assigns the stacking height. For a flipped component
        this is the top face; the body extends downward.
    flip_x : bool
        Mirror the component about the X axis (a 180° rotation about X),
        turning it over. Used for boards mounted flat against the back of
        another part (e.g. the HDMI driver against the panel back). Flipped
        components occupy ``[z - height, z]`` instead of ``[z, z + height]``.
    tilt_x : float
        Tilt about the X axis in degrees, applied about the component's own
        origin after ``rotation`` and ``flip_x``. Distinct from ``flip_x``,
        which is the fixed 180° turn-over: this is the small wedge angle a
        part picks up from being mounted on the sloped base deck (negative
        raises -Y / the rear, matching ``case.base.Base.deck_level_at``).
        Unlike a Z rotation, a tilt mixes the component's depth into its
        world height, so it widens both the Y footprint and the Z bounds.
    """

    component: Component
    x: float
    y: float
    rotation: float = 0.0
    z: float = 0.0
    flip_x: bool = False
    tilt_x: float = 0.0

    def _tilt(self, y: float, z: float) -> tuple[float, float]:
        """Apply ``tilt_x`` to a YZ pair (no-op at tilt 0)."""
        if not self.tilt_x:
            return (y, z)
        rad = math.radians(self.tilt_x)
        cos_t, sin_t = math.cos(rad), math.sin(rad)
        return (y * cos_t - z * sin_t, y * sin_t + z * cos_t)

    @property
    def box(self) -> tuple[float, float, float, float]:
        """Axis-aligned world-frame XY footprint ``(x0, y0, x1, y1)`` (mm).

        Accounts for the placement's Z rotation (see :func:`rotated_footprint`)
        so a 90°/270°-rotated non-square component reports its true world
        extent, not its unrotated local one, and for ``tilt_x``, which swings
        part of the component's height into its Y extent.
        """
        eff_w, eff_d, _ = volume_extents(self, self.component.size())
        return (
            self.x - eff_w / 2,
            self.y - eff_d / 2,
            self.x + eff_w / 2,
            self.y + eff_d / 2,
        )

    def world_offset(self, x: float, y: float, z: float) -> tuple[float, float, float]:
        """Transform a local offset into world coordinates (mm).

        Applies the placement's Z rotation, then the optional 180° flip about
        X (``flip_x``), then the ``tilt_x`` wedge angle — the same order
        :meth:`assemblies.assembly.Assembly.build_subset` applies them to the
        solid, so data-layer positions and generated geometry agree. A flip
        turns the component over so its top face lies at ``z`` and the body
        hangs below it — the mounting convention for boards mounted flat
        against the panel back.
        """
        rad = math.radians(self.rotation)
        rx = x * math.cos(rad) - y * math.sin(rad)
        ry = x * math.sin(rad) + y * math.cos(rad)
        if self.flip_x:
            ry, rz = -ry, -z
        else:
            rz = z
        ry, rz = self._tilt(ry, rz)
        return (self.x + rx, self.y + ry, self.z + rz)

    def world_direction(self, dx: float, dy: float, dz: float) -> tuple[float, float, float]:
        """Transform a local direction into world coordinates."""
        rad = math.radians(self.rotation)
        wx = dx * math.cos(rad) - dy * math.sin(rad)
        wy = dx * math.sin(rad) + dy * math.cos(rad)
        if self.flip_x:
            wy, wz = -wy, -dz
        else:
            wz = dz
        wy, wz = self._tilt(wy, wz)
        return (wx, wy, wz)

    def z_bounds(self) -> tuple[float, float]:
        """Return the component's occupied Z range ``(z0, z1)`` (mm).

        Flipped components extend downward from ``z`` (top face at ``z``);
        all others extend upward (bottom face at ``z``). A ``tilt_x`` swings
        part of the component's depth into Z, so the tilted range is the
        axis-aligned bound of the tilted box, measured from the same origin.
        """
        size = self.component.size()
        height = size.height
        if not self.tilt_x:
            if self.flip_x:
                return (self.z - height, self.z)
            return (self.z, self.z + height)

        # Corners of the component's YZ profile in its own frame, tilted.
        _, depth = rotated_footprint(size.width, size.depth, self.rotation)
        z0_local, z1_local = (-height, 0.0) if self.flip_x else (0.0, height)
        zs = [
            self._tilt(y, z)[1]
            for y in (-depth / 2.0, depth / 2.0)
            for z in (z0_local, z1_local)
        ]
        return (self.z + min(zs), self.z + max(zs))


class Layout(ABC):
    """Abstract layout.

    Subclasses override :meth:`_build_placements` to place components and
    return the resulting :class:`Placement` list. Layouts must not touch CAD.
    """

    name: str = "layout"

    def __init__(self, components: dict[str, Component] | None = None) -> None:
        """Create a layout.

        Parameters
        ----------
        components : dict[str, Component], optional
            Components keyed by role (e.g. ``"keyboard"``, ``"sbc"``). The
            concrete layout reads what it needs and may instantiate defaults.
        """
        self.components: dict[str, Component] = components or {}
        self._placements: list[Placement] | None = None

    def place(
        self,
        component: Component,
        x: float,
        y: float,
        rotation: float = 0.0,
        z: float = 0.0,
    ) -> None:
        """Record a placement in this layout.

        Parameters
        ----------
        component : Component
            The component to place.
        x, y : float
            Component origin in the world frame (mm).
        rotation : float
            Rotation about Z (degrees).
        z : float
            Stacking height (mm); assembly assigns this when 0.
        """
        self._placements.append(Placement(component, x, y, rotation, z))

    def placements(self) -> list[Placement]:
        """Return the resolved placements, building them on first access."""
        if self._placements is None:
            self._placements = []
            self._build_placements(self._placements)
        return list(self._placements)

    @abstractmethod
    def _build_placements(self, placements: list[Placement]) -> None:
        """Populate ``placements`` with :meth:`place` calls (no CAD)."""
