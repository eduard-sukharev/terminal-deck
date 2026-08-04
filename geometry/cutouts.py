"""Cutout generator.

Consumes connector definitions from the components and produces shell cutouts
(USB holes, HDMI hole, SD slot, audio slot, vents). Cutout size = connector
opening + clearance — calculated, never guessed.
"""

from __future__ import annotations

from dataclasses import dataclass

from components.base import Connector


@dataclass(frozen=True)
class Cutout:
    """A shell opening for one connector.

    Attributes
    ----------
    connector_type : str
        Connector identifier the cutout serves.
    x, y, z : float
        Cutout center in the shell frame (mm).
    width : float
        Cutout width (mm) — connector width plus clearance.
    height : float
        Cutout height (mm) — connector height plus clearance.
    clearance : float
        Per-side clearance added to the connector opening (mm).
    """

    connector_type: str
    x: float
    y: float
    z: float
    width: float
    height: float
    clearance: float

    @property
    def depth(self) -> float:
        """Cutout depth equals the shell wall thickness (mm)."""
        raise NotImplementedError(
            "Cutout.depth is provided by the shell pass — see shell wall thickness"
        )


def from_connector(connector: Connector, clearance: float) -> Cutout:
    """Build a :class:`Cutout` from a :class:`Connector`.

    Parameters
    ----------
    connector : Connector
        The component connector to expose.
    clearance : float
        Per-side clearance added to the opening (mm).

    Returns
    -------
    Cutout
        The calculated shell opening.
    """
    return Cutout(
        connector_type=connector.type,
        x=connector.x,
        y=connector.y,
        z=connector.z,
        width=connector.width + 2 * clearance,
        height=connector.height + 2 * clearance,
        clearance=clearance,
    )


def generate(connectors: list[Connector], clearance: float) -> list[Cutout]:
    """Generate one :class:`Cutout` per connector."""
    return [from_connector(connector, clearance) for connector in connectors]


def build(cutouts: list, shell, wall_thickness: float):
    """Cut all cutouts into a shell solid.

    Parameters
    ----------
    cutouts : list of dict or Cutout
        Shell openings (as produced by ``Assembly.connector_cutouts``). Each
        dict may carry an axis-aligned ``direction`` and wall ``distance``;
        the cut box is then bored from the connector through the wall.
    shell : cadquery.Workplane
        Shell solid to cut, in the same (world) frame as the cutouts.
    wall_thickness : float
        Shell wall thickness (mm).

    Returns
    -------
    cadquery.Workplane
        The shell with all openings removed.
    """
    from utilities import cq_helpers

    cq = cq_helpers.require_cq()
    result = shell
    for cutout in cutouts:
        if isinstance(cutout, dict):
            x, y, z = cutout["x"], cutout["y"], cutout["z"]
            width, height = cutout["width"], cutout["height"]
            direction = cutout.get("direction", (0.0, 0.0, 1.0))
            distance = cutout.get("distance", 0.0)
        else:
            x, y, z = cutout.x, cutout.y, cutout.z
            width, height = cutout.width, cutout.height
            direction = (0.0, 0.0, 1.0)
            distance = 0.0

        # Bore from the connector origin through the wall, with a penetration
        # margin of one wall thickness so the opening fully crosses the face.
        length = distance + wall_thickness
        dx, dy, dz = direction

        # Assumes axis-aligned directions. The cut box long axis (Z) is
        # rotated to align with ``direction``; width/height map so the opening
        # stays horizontal-along-wall / vertical.
        if abs(dy) >= abs(dx):
            cut = cq_helpers.box_centered(width, height, length)
            cut = cut.rotate((0, 0, 0), (1, 0, 0), 90)
        else:
            cut = cq_helpers.box_centered(height, width, length)
            cut = cut.rotate((0, 0, 0), (0, 1, 0), 90)
        cut = cq_helpers.translate(cut, x + dx * length / 2.0, y + dy * length / 2.0, z + dz * length / 2.0)
        result = result.cut(cut)
    return result
