"""CadQuery helpers — the single adapter between this codebase and CadQuery.

CadQuery is imported lazily so that data-layer modules (component specs,
config loading, validation) remain importable and testable without a
CadQuery installation. Only modules that actually generate geometry should
depend on this helper, and they must call :func:`require_cq` before use.

All coordinates in this codebase follow the global convention:
+X right, +Y forward, +Z upward, origin at center of the base.
"""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import cadquery as cq

_cq_module: Any | None = None
_import_error: ImportError | None = None


def require_cq() -> Any:
    """Return the CadQuery module, importing it lazily.

    Raises
    ------
    ImportError
        If CadQuery is not installed.
    """
    global _cq_module, _import_error
    if _cq_module is None:
        try:
            _cq_module = importlib.import_module("cadquery")
        except ImportError as exc:  # pragma: no cover - depends on env
            _import_error = exc
            raise
    return _cq_module


def cq_available() -> bool:
    """True if CadQuery can be imported in this environment."""
    if _cq_module is None and _import_error is None:
        try:
            require_cq()
        except ImportError:
            return False
    return _import_error is None


def box_centered(width: float, depth: float, height: float) -> Any:
    """Return a solid box centered on the local origin.

    Parameters
    ----------
    width : float
        Extent along X (mm).
    depth : float
        Extent along Y (mm).
    height : float
        Extent along Z (mm).
    """
    cq = require_cq()
    return cq.Workplane("XY").box(width, depth, height)


def cylinder_centered(diameter: float, height: float) -> Any:
    """Return a solid cylinder centered on the local origin, axis along Z.

    Uses keyword arguments because CadQuery's ``Workplane.cylinder`` argument
    order for ``radius``/``height`` differs across releases.
    """
    cq = require_cq()
    return cq.Workplane("XY").cylinder(radius=diameter / 2.0, height=height)


def translate(shape: Any, x: float, y: float, z: float) -> Any:
    """Translate a shape by an absolute (x, y, z) offset in mm."""
    return shape.translate((x, y, z))


def rotate_z(shape: Any, angle_deg: float) -> Any:
    """Rotate a shape about the Z axis by ``angle_deg`` degrees."""
    return shape.rotate((0, 0, 0), (0, 0, 1), angle_deg)


def extrude_polygon(
    vertices: list[tuple[float, float]],
    height: float,
    x: float = 0.0,
    y: float = 0.0,
    z: float = 0.0,
) -> Any:
    """Extrude a closed polygon into a solid, centered at (x, y, z).

    Parameters
    ----------
    vertices : list[tuple[float, float]]
        Closed polygon vertices in XY, centered on origin.
    height : float
        Extrusion height along Z (mm).
    x, y, z : float
        Center position in the world frame (mm).

    Returns
    -------
    cadquery.Workplane
        The extruded solid.
    """
    cq = require_cq()
    solid = cq.Workplane("XY").polyline(vertices).close().extrude(height)
    return translate(solid, x, y, z - height / 2.0)


def loft_between(
    bottom_verts: list[tuple[float, float]],
    top_verts: list[tuple[float, float]],
    height: float,
    x: float = 0.0,
    y: float = 0.0,
    z: float = 0.0,
) -> Any:
    """Loft a solid between two closed polygon wires, centred at (x, y, z).

    The bottom wire lies on the XY plane; the top wire is offset by *height*
    along Z.  Both wires must have the **same number of vertices** in the
    **same angular order** (CCW from +X) to produce an untwisted ruled loft.

    The resulting solid is translated so its **bottom** face sits at *z*.
    """
    cq = require_cq()
    solid = (
        cq.Workplane("XY")
        .polyline(bottom_verts).close()
        .workplane(offset=height)
        .polyline(top_verts).close()
        .loft()
    )
    return translate(solid, x, y, z)


def make_compound(shapes: list[Any]) -> Any:
    """Return a single Workplane containing *shapes* as one unfused compound.

    Use this to batch many solids before a single ``.union()`` — far faster
    than N sequential unions because OCP processes the whole compound in one
    boolean operation.
    """
    cq = require_cq()
    compound = cq.Compound.makeCompound([s.val() for s in shapes])
    return cq.Workplane("XY").newObject([compound])


def bounding_box_mm(shape: Any) -> tuple[float, float, float]:
    """Return (width, depth, height) in mm of a CadQuery shape.

    Uses the OCP bounding box for measured truth. Avoid recomputing per
    component where the measured component value is authoritative.
    """
    bbox = shape.val().BoundingBox()
    return (bbox.xlen, bbox.ylen, bbox.zlen)
