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
    cad_helpers,
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

    # The polygons are drawn in the local XY plane, then this whole loft is
    # rotated so its Z (length) axis lines up with ``direction``. A rotation
    # about X (used below for a Y-facing connector) leaves local Y fixed, so
    # local X must already hold ``width`` for the opening to end up
    # width-along-the-wall / height-vertical. A rotation about Y (X-facing)
    # instead leaves local Y mapped onto world Y, so it's ``height`` that
    # must sit on local X here for the same final width/height roles — the
    # same swap the plain-box cut path makes via its
    # ``box_centered(height, width, length)`` call for that branch.
    y_facing = abs(dy) >= abs(dx)
    a, b = (width, height) if y_facing else (height, width)
    outer_a, outer_b = (outer_w, outer_h) if y_facing else (outer_h, outer_w)

    bottom = [(-a / 2, -b / 2), (a / 2, -b / 2), (a / 2, b / 2), (-a / 2, b / 2)]
    top = [
        (-outer_a / 2, -outer_b / 2),
        (outer_a / 2, -outer_b / 2),
        (outer_a / 2, outer_b / 2),
        (-outer_a / 2, outer_b / 2),
    ]
    # Centered on its own length axis (bottom/inner face at -length/2, outer
    # face at +length/2) so it lines up with the caller's shared translate,
    # which assumes a centered shape — the same convention as the plain-box
    # cut path below. ``loft_between`` otherwise puts the bottom face at
    # z=0, which would leave the inner half of the bore uncut.
    cut = cad_helpers.loft_between(bottom, top, length, z=-length / 2.0)
    # Rotate the loft's Z axis to align with the (axis-aligned) direction.
    if y_facing:
        cut = cad_helpers.rotate_x(cut, 90.0 if dy > 0 else -90.0)
    else:
        cut = cad_helpers.rotate_y(cut, 90.0 if dx > 0 else -90.0)
    return cut


def cutout_tool(cutout: Any, wall_thickness: float, chamfer: float = 0.0) -> Any:
    """Build one cutout's cut solid, positioned in the world frame.

    Factored out of :func:`build` so tooling that wants the cutout's own
    shape (e.g. a debug section/cutaway renderer) can reuse the exact same
    geometry that gets subtracted from the shell, rather than re-deriving it.

    Parameters
    ----------
    cutout : dict or Cutout
        A shell opening (as produced by ``Assembly.connector_cutouts``). A
        dict may carry an axis-aligned ``direction`` and wall ``distance``;
        the cut box is then bored from the connector through the wall.
    wall_thickness : float
        Shell wall thickness (mm).
    chamfer : float
        Lead-in bevel (mm) applied to the outer opening. When zero, a plain
        box is bored (no bevel).

    Returns
    -------
    Shape
        The cut solid, spanning from the connector origin through the wall.
    """
    from utilities import cad_helpers

    cad_helpers.require_cad()
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
        cut = _chamfered_cut(cad_helpers, width, height, length, chamfer, direction)
    elif abs(dy) >= abs(dx):
        cut = cad_helpers.box_centered(width, height, length)
        cut = cad_helpers.rotate_x(cut, 90)
    else:
        cut = cad_helpers.box_centered(height, width, length)
        cut = cad_helpers.rotate_y(cut, 90)
    return cad_helpers.translate(cut, x + dx * length / 2.0, y + dy * length / 2.0, z + dz * length / 2.0)


def build(cutouts: list, shell, wall_thickness: float, chamfer: float = 0.0):
    """Cut all cutouts into a shell solid.

    Parameters
    ----------
    cutouts : list of dict or Cutout
        Shell openings (as produced by ``Assembly.connector_cutouts``).
    shell : Shape
        Shell solid to cut, in the same (world) frame as the cutouts.
    wall_thickness : float
        Shell wall thickness (mm).
    chamfer : float
        Lead-in bevel (mm) applied to the outer opening of each cutout. When
        zero, a plain box is bored (no bevel).

    Returns
    -------
    Shape
        The shell with all openings removed.
    """
    from utilities import cad_helpers

    result = shell
    for cutout in cutouts:
        result = cad_helpers.cut(result, cutout_tool(cutout, wall_thickness, chamfer))
    return result
