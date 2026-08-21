"""Cutout generator.

Consumes connector definitions from the components and produces shell cutouts
(USB holes, HDMI hole, SD slot, audio slot, vents). Cutout size = connector
opening + clearance — calculated, never guessed.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

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


def _chamfered_cut(
    cq_helpers,
    width: float,
    height: float,
    length: float,
    chamfer: float,
    direction: tuple[float, float, float],
) -> Any:
    """Build a cut solid with a lead-in bevel on its outer opening.

    The cut is a loft from the connector opening (``width`` x ``height``) at
    the inner end to a slightly larger opening (``+ 2 * chamfer`` per side) at
    the outer end, so the shell opening flares outward for easy plug insertion.
    The long axis is aligned with ``direction`` and the inner end sits at the
    origin, ready for the caller to translate to the connector position.
    """
    dx, dy, _ = direction
    outer_w = width + 2 * chamfer
    outer_h = height + 2 * chamfer
    bottom = [
        (-width / 2, -height / 2),
        (width / 2, -height / 2),
        (width / 2, height / 2),
        (-width / 2, height / 2),
    ]
    top = [
        (-outer_w / 2, -outer_h / 2),
        (outer_w / 2, -outer_h / 2),
        (outer_w / 2, outer_h / 2),
        (-outer_w / 2, outer_h / 2),
    ]
    cut = cq_helpers.loft_between(bottom, top, length)
    # Rotate the loft's Z axis to align with the (axis-aligned) direction.
    if abs(dy) >= abs(dx):
        cut = cut.rotate((0, 0, 0), (1, 0, 0), 90.0 if dy > 0 else -90.0)
    else:
        cut = cut.rotate((0, 0, 0), (0, 1, 0), 90.0 if dx > 0 else -90.0)
    return cut


def build(cutouts: list, shell, wall_thickness: float, chamfer: float = 0.0):
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
    chamfer : float
        Lead-in bevel (mm) applied to the outer opening of each cutout. When
        zero, a plain box is bored (no bevel).

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

        # Assumes axis-aligned directions. The cut long axis (Z) is rotated to
        # align with ``direction``; width/height map so the opening stays
        # horizontal-along-wall / vertical.
        if chamfer > 0.0:
            cut = _chamfered_cut(cq_helpers, width, height, length, chamfer, direction)
        elif abs(dy) >= abs(dx):
            cut = cq_helpers.box_centered(width, height, length)
            cut = cut.rotate((0, 0, 0), (1, 0, 0), 90)
        else:
            cut = cq_helpers.box_centered(height, width, length)
            cut = cut.rotate((0, 0, 0), (0, 1, 0), 90)
        cut = cq_helpers.translate(cut, x + dx * length / 2.0, y + dy * length / 2.0, z + dz * length / 2.0)
        result = result.cut(cut)
    return result
