"""Shell helper: hollow out a solid at the configured wall thickness.

The wall thickness is a single parameter (``config.wall.thickness``);
everything else derives from it.
"""

from __future__ import annotations

from typing import Any

from utilities import cad_helpers


def offset_shell(
    shape: Any, wall_thickness: float, open_face: "cad_helpers.FaceRef" = cad_helpers.FaceRef.TOP
) -> Any:
    """Hollow a solid, leaving ``wall_thickness`` (mm) of material.

    Parameters
    ----------
    shape : Shape
        Solid to shell (base or lid block).
    wall_thickness : float
        Wall thickness in millimeters.
    open_face : cad_helpers.FaceRef
        Which face to open (default ``FaceRef.TOP`` for an open-top base;
        pass ``FaceRef.BOTTOM`` for an open-bottom lid).

    Returns
    -------
    Shape
        The hollowed solid with the outer boundary unchanged.

    Notes
    -----
    A negative shell offset keeps the outer boundary fixed while hollowing
    inward, leaving ``wall_thickness`` of material. This keeps the enclosure
    envelope exactly equal to the calculated size.

    Uses the ``.workplane()``-intervening shell chain (see
    :func:`utilities.cad_helpers.shell_closed`) — this is
    the original chain every ``offset_shell`` caller (the lid) has always
    used; it is numerically different from the plain chain
    ``case.base.Base.build_bottom`` uses directly.
    """
    return cad_helpers.shell_closed(shape, wall_thickness)
