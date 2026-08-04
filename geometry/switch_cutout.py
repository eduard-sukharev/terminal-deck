"""Canonical Cherry MX switch cutout geometry.

Provides the standard 14×14 mm notched polygon (12 vertices) as a reusable
CadQuery solid. The polygon matches the ergogen definition in ``JD40.yaml``
— both represent the same Cherry MX standard.

Stabilizer cutout geometry lives in :mod:`geometry.stabilizer_cutout`.

Usage::

    from geometry.switch_cutout import build_cutout

    # Cut switch holes in a plate
    for x, y in switch_positions:
        plate = plate.cut(build_cutout(plate_thickness + 1.0, x, y))

    # Build switch housings above the plate
    for x, y in switch_positions:
        body = body.union(build_cutout(switch_depth, x, y, plate_thickness))
"""

from __future__ import annotations

from dataclasses import dataclass

from geometry.cutout_registry import register_switch_cutout


@register_switch_cutout("mx")
@dataclass(frozen=True)
class SwitchCutoutSpec:
    """Canonical Cherry MX switch cutout profile (standard 14×14 mm).

    The Cherry MX specification defines a 14×14 mm opening with four 3.5 mm
    corner notches that accommodate the switch's mounting pins. This polygon
    is the industry-standard shape — see the ergogen definition in
    ``JD40.yaml`` for the equivalent shift-chain representation.

    These are constants from the Cherry MX standard, not configuration
    parameters. Deviating from them would break switch compatibility.
    """

    width: float = 14.0
    notch: float = 3.5

    @property
    def vertices(self) -> list[tuple[float, float]]:
        """The 12 vertices of the Cherry MX cutout polygon, centered on origin.

        Traced from the ergogen shift-chain in ``JD40.yaml``::

            Start   ( 7.0,  7.0)   top-right corner
            → shift (-14,   0  ) → (-7.0,  7.0)   top-left corner
            → shift (  0,  -3.5) → (-7.0,  3.5)   left edge, upper notch
            → shift (  3.5,  0 ) → (-3.5,  3.5)   left notch inner corner (top)
            → shift (  0,  -7  ) → (-3.5, -3.5)   left notch inner corner (bottom)
            → shift (-3.5,  0 ) → (-7.0, -3.5)   left edge, lower notch
            → shift (  0,  -3.5) → (-7.0, -7.0)   bottom-left corner
            → shift ( 14,   0  ) → ( 7.0, -7.0)   bottom-right corner
            → shift (  0,   3.5) → ( 7.0, -3.5)   right edge, lower notch
            → shift (-3.5,  0 ) → ( 3.5, -3.5)   right notch inner corner (bottom)
            → shift (  0,   7  ) → ( 3.5,  3.5)   right notch inner corner (top)
            → shift (  3.5,  0 ) → ( 7.0,  3.5)   right edge, upper notch

        Returns
        -------
        list[tuple[float, float]]
            Twelve (x, y) pairs, closed polygon centered on (0, 0).
        """
        hw = self.width / 2.0
        n = self.notch
        return [
            ( hw,  hw),
            (-hw,  hw),
            (-hw,  n ),
            (-n,   n ),
            (-n,  -n ),
            (-hw, -n ),
            (-hw, -hw),
            ( hw, -hw),
            ( hw, -n ),
            ( n,  -n ),
            ( n,   n ),
            ( hw,  n ),
        ]


def build_cutout(
    height: float,
    x: float = 0.0,
    y: float = 0.0,
    z: float = 0.0,
    cutout_type: str = "mx",
) -> object:
    """Return a solid extrusion of the selected switch cutout polygon.

    The solid is centered at ``(x, y, z)``, spanning ``z - height/2`` to
    ``z + height/2``.

    Parameters
    ----------
    height : float
        Extrusion height along Z (mm). For plate cutting, use
        ``plate_thickness + 1.0`` to guarantee clean-through.
    x, y, z : float
        Center position in the world / plate frame (mm).
    cutout_type : str
        Registered switch cutout type name. Default ``"mx"``.

    Returns
    -------
    cadquery.Workplane or None
        The extruded solid, or None for no-op types.
    """
    from geometry.cutout_registry import get_switch_cutout
    from utilities import cq_helpers

    cq = cq_helpers.require_cq()
    cls = get_switch_cutout(cutout_type)
    spec = cls()
    try:
        verts = spec.vertices
    except NotImplementedError:
        return None
    solid = cq.Workplane("XY").polyline(verts).close().extrude(height)
    return cq_helpers.translate(solid, x, y, z - height / 2.0)


# Re-export stabilizer cutout from its own module for backward compatibility.
from geometry.stabilizer_cutout import (  # noqa: F401
    StabilizerCutoutSpec,
    StabilizerPlacement,
    build_stabilizer_cutout,
    stabilizer_offset,
    stabilizer_pair,
)
