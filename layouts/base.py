"""Layout engine base.

A layout contains NO CAD — only placements. Placing a component records its
position and rotation; assembly and enclosure derive geometry from the
resulting placements.

Coordinate convention: +X right, +Y forward, +Z upward, origin at center of
the base.
"""

from __future__ import annotations

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
        assembly stage assigns the stacking height.
    """

    component: Component
    x: float
    y: float
    rotation: float = 0.0
    z: float = 0.0

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
