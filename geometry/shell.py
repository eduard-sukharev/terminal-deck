"""Shell helper: hollow out a solid at the configured wall thickness.

The wall thickness is a single parameter (``config.wall.thickness``);
everything else derives from it.
"""

from __future__ import annotations

from typing import Any

from utilities import cq_helpers


def offset_shell(shape: Any, wall_thickness: float, open_face: str = ">Z") -> Any:
    """Hollow a solid, leaving ``wall_thickness`` (mm) of material.

    Parameters
    ----------
    shape : cadquery.Shape
        Solid to shell (base or lid block).
    wall_thickness : float
        Wall thickness in millimeters.
    open_face : str
        Face selector for the open face (default ``">Z"`` for an open-top base;
        pass ``"<Z"`` for an open-bottom lid).

    Returns
    -------
    cadquery.Shape
        The hollowed solid with the outer boundary unchanged.

    Notes
    -----
    A negative shell offset keeps the outer boundary fixed while hollowing
    inward, leaving ``wall_thickness`` of material. This keeps the enclosure
    envelope exactly equal to the calculated size.
    """
    cq_helpers.require_cq()
    return shape.faces(open_face).workplane().shell(-wall_thickness)
