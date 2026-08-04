"""Component data model and the abstract Component API.

Every hardware component in the build exports the same interface so that
placement, assembly, and enclosure generation stay generic. See the example
in ``docs/component_spec.md``.

Data model (all dimensions in millimeters, origin = component reference):
* :class:`BoundingBox` — measured overall size
* :class:`Hole` — mounting hole, XY in component frame
* :class:`Connector` — a physical connector with position and direction
* :class:`Keepout` — the volume other parts must not enter

Coordinate convention: +X right, +Y forward, +Z upward.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from utilities.constants import (
    CONNECTOR_AUDIO,
    CONNECTOR_ETHERNET,
    CONNECTOR_HDMI,
    CONNECTOR_MICROSD,
    CONNECTOR_POWER,
    CONNECTOR_USB_A,
    CONNECTOR_USB_C,
)


@dataclass(frozen=True)
class BoundingBox:
    """Overall measured size of a component, in millimeters.

    Attributes
    ----------
    width : float
        Extent along X.
    depth : float
        Extent along Y.
    height : float
        Extent along Z.
    """

    width: float
    depth: float
    height: float

    def __post_init__(self) -> None:
        if not (self.width > 0 and self.depth > 0 and self.height > 0):
            raise ValueError(f"BoundingBox dimensions must be positive: {self}")


@dataclass(frozen=True)
class Hole:
    """A mounting hole in the component frame.

    Attributes
    ----------
    x : float
        X position relative to component origin (mm).
    y : float
        Y position relative to component origin (mm).
    diameter : float
        Hole diameter (mm).
    height : float or None
        Height of the supporting boss above the shell floor (mm); ``None``
        means the default (``2 * wall_thickness``). Used when a component is
        mounted on standoffs (e.g. a raised switch plate).
    """

    x: float
    y: float
    diameter: float
    height: float | None = None

    def __post_init__(self) -> None:
        if self.diameter <= 0:
            raise ValueError(f"Hole diameter must be positive: {self}")
        if self.height is not None and self.height <= 0:
            raise ValueError(f"Hole boss height must be positive: {self}")


@dataclass(frozen=True)
class Connector:
    """A physical connector exposed on a component.

    Attributes
    ----------
    type : str
        Identifier, e.g. ``CONNECTOR_HDMI`` (see ``utilities.constants``).
    x, y, z : float
        Position of the connector origin relative to component origin (mm).
    direction : tuple[float, float, float]
        Unit vector the connector faces (its insertion/recess axis).
    width, height : float
        Connector opening cross-section (mm).
    depth : float
        Connector depth along its direction (mm).
    internal : bool
        True when the connector mates to another part inside the case
        (no shell cutout and no external access required).
    """

    type: str
    x: float
    y: float
    z: float
    direction: tuple[float, float, float]
    width: float
    height: float
    depth: float
    internal: bool = False

    def __post_init__(self) -> None:
        if not (self.width > 0 and self.height > 0 and self.depth > 0):
            raise ValueError(f"Connector extents must be positive: {self}")


@dataclass(frozen=True)
class Keepout:
    """Keep-out volume a component must be given around it (mm)."""

    width: float
    depth: float
    height: float

    def __post_init__(self) -> None:
        if not (self.width > 0 and self.depth > 0 and self.height > 0):
            raise ValueError(f"Keepout extents must be positive: {self}")


class Component(ABC):
    """Abstract hardware component.

    Subclasses declare measured values (``size``, mounting holes, connectors)
    and implement :meth:`build` to generate their CAD geometry.

    Implementation notes
    --------------------
    * All dimensions originate from configuration, measured components, or
      calculated geometry. Never intuition.
    * ``reference_origin`` defaults to the center of the base and should be
      overridden only by components whose origin differs by design.
    """

    #: Human-readable component name.
    name: str = "Component"

    @abstractmethod
    def size(self) -> BoundingBox:
        """Return the measured overall :class:`BoundingBox` (mm)."""

    def mounting_holes(self) -> list[Hole]:
        """Return mounting holes relative to the component origin (mm).

        Defaults to no mounting holes. Override to declare real holes.
        """
        return []

    def mounting_screw(self) -> str | None:
        """Return the screw library key used to mount this component.

        ``None`` (default) means the build's configured standoff screw
        (``config.screws.standoff``) is used. Override when a component mounts
        with a specific screw size.
        """
        return None

    def connectors(self) -> list[Connector]:
        """Return connectors exposed by this component.

        Defaults to none. Override to declare real connectors.
        """
        return []

    def keepout(self) -> Keepout:
        """Return the keep-out volume (mm).

        Defaults to the measured size plus a small cable allowance. Override
        when the component needs asymmetric clearance.
        """
        box = self.size()
        return Keepout(box.width + 4.0, box.depth + 4.0, box.height + 4.0)

    def occupied_volumes(self) -> list[tuple[float, float, float, BoundingBox]]:
        """Return the solid sub-volumes of this component (mm).

        Each entry is ``(x, y, z, box)`` — a bounding box of ``box`` centered
        at the given local offset. Defaults to the full measured size at the
        origin. Override when the component is hollow (e.g. a raised plate with
        empty space beneath it) so collision checks only flag real overlaps.
        """
        return [(0.0, 0.0, 0.0, self.size())]

    def reference_origin(self) -> tuple[float, float, float]:
        """Return the component origin offset in the world frame (mm).

        The global origin is the center of the base. Default: no offset.
        """
        return (0.0, 0.0, 0.0)

    def build(self):
        """Generate the component's CadQuery geometry.

        Returns
        -------
        cadquery.Shape
            The solid model centered on the component origin.

        Raises
        ------
        NotImplementedError
            CAD generation is not implemented in the scaffolding pass.
        """
        raise NotImplementedError(
            f"{type(self).__name__}.build() not implemented — "
            "implement CAD generation per docs/cad_api.md"
        )

    def __repr__(self) -> str:  # pragma: no cover - debug aid
        return f"<{type(self).__name__} name={self.name!r}>"


__all__ = [
    "BoundingBox",
    "Hole",
    "Connector",
    "Keepout",
    "Component",
    "CONNECTOR_AUDIO",
    "CONNECTOR_ETHERNET",
    "CONNECTOR_HDMI",
    "CONNECTOR_MICROSD",
    "CONNECTOR_POWER",
    "CONNECTOR_USB_A",
    "CONNECTOR_USB_C",
]
