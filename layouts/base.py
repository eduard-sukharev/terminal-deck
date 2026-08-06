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

from components.base import Component


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
    """

    component: Component
    x: float
    y: float
    rotation: float = 0.0
    z: float = 0.0
    flip_x: bool = False

    @property
    def box(self) -> tuple[float, float, float, float]:
        """Axis-aligned XY footprint ``(x0, y0, x1, y1)`` ignoring rotation (mm)."""
        size = self.component.size()
        return (
            self.x - size.width / 2,
            self.y - size.depth / 2,
            self.x + size.width / 2,
            self.y + size.depth / 2,
        )

    def world_offset(self, x: float, y: float, z: float) -> tuple[float, float, float]:
        """Transform a local offset into world coordinates (mm).

        Applies the placement's Z rotation followed by the optional 180° flip
        about X (``flip_x``). A flip turns the component over so its top face
        lies at ``z`` and the body hangs below it — the mounting convention
        for boards mounted flat against the panel back.
        """
        rad = math.radians(self.rotation)
        rx = x * math.cos(rad) - y * math.sin(rad)
        ry = x * math.sin(rad) + y * math.cos(rad)
        if self.flip_x:
            ry, rz = -ry, -z
        else:
            rz = z
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
        return (wx, wy, wz)

    def z_bounds(self) -> tuple[float, float]:
        """Return the component's occupied Z range ``(z0, z1)`` (mm).

        Flipped components extend downward from ``z`` (top face at ``z``);
        all others extend upward (bottom face at ``z``).
        """
        height = self.component.size().height
        if self.flip_x:
            return (self.z - height, self.z)
        return (self.z, self.z + height)


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
