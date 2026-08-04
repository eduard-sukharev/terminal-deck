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
    shape : cadquery.Shape
        Solid to fillet.
    edge_radius : float
        Radius in millimeters, from ``config.corners.edge_radius``.

    Returns
    -------
    cadquery.Shape
        The filleted solid.
    """
    from utilities import cq_helpers

    cq_helpers.require_cq()
    return shape.edges().fillet(edge_radius)


def fillet_corners(shape: Any, corner_radius: float) -> Any:
    """Apply ``corner_radius`` (mm) to the vertical corner edges of a base/lid.

    Parameters
    ----------
    shape : cadquery.Shape
        Solid to fillet.
    corner_radius : float
        Radius in millimeters, from ``config.corners.radius``.

    Returns
    -------
    cadquery.Shape
        The filleted solid.
    """
    from utilities import cq_helpers

    cq = cq_helpers.require_cq()
    selector = cq.selectors.ParallelDirSelector(cq.Vector(0.0, 0.0, 1.0))
    return shape.edges(selector).fillet(corner_radius)
