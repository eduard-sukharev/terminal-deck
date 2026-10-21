"""Fillet helpers.

No hardcoded radii. Edge and corner radii are parameters that derive from
``config/corners`` (``edge_radius``, ``radius``). These wrappers apply the
fillets to a solid; the shape math is deferred to the CAD pass.
"""

from __future__ import annotations

from typing import Any


def fillet_edges(shape: Any, edge_radius: float) -> Any:
    """Apply ``edge_radius`` (mm) to all sharp edges of a solid.

    Parameters
    ----------
    shape : Shape
        Solid to fillet.
    edge_radius : float
        Radius in millimeters, from ``config.corners.edge_radius``.

    Returns
    -------
    Shape
        The filleted solid.
    """
    from utilities import cad_helpers

    return cad_helpers.fillet_all_edges(shape, edge_radius)


def fillet_corners(shape: Any, corner_radius: float) -> Any:
    """Apply ``corner_radius`` (mm) to the vertical corner edges of a base/lid.

    Parameters
    ----------
    shape : Shape
        Solid to fillet.
    corner_radius : float
        Radius in millimeters, from ``config.corners.radius``.

    Returns
    -------
    Shape
        The filleted solid.
    """
    from utilities import cad_helpers

    return cad_helpers.fillet_vertical_edges(shape, corner_radius)
