"""CAD helpers — the single adapter between this codebase and build123d.

build123d is imported lazily so that data-layer modules (component specs,
config loading, validation) remain importable and testable without a CAD
installation. Only modules that actually generate geometry should depend on
this helper, and they must call :func:`require_cad` before use.

Shapes are opaque to callers: every operation goes through a function here,
so geometry modules never touch the CAD library directly.

All coordinates in this codebase follow the global convention:
+X right, +Y forward, +Z upward, origin at center of the base.
"""

from __future__ import annotations

import importlib
import math
from dataclasses import dataclass, field
from enum import Enum
from itertools import chain
from typing import Any

# SVG projection: front-left, above (+Z up). Presentation choices, not
# dimensions — tune freely.
SVG_VIEW_DIRECTION = (-50.0, -80.0, 60.0)
SVG_SCALE = 1.0
SVG_HIDDEN_LINE_WEIGHT = 0.15  # mm

_b3d_module: Any | None = None
_import_error: ImportError | None = None


class FaceRef(Enum):
    """The only two face selectors this codebase needs: top or bottom."""

    TOP = "top"
    BOTTOM = "bottom"


@dataclass(frozen=True)
class BBox:
    """Axis-aligned bounding box (mm) with the min/max/length accessors the
    debug renderers use."""

    xmin: float
    xmax: float
    ymin: float
    ymax: float
    zmin: float
    zmax: float

    @property
    def xlen(self) -> float:
        return self.xmax - self.xmin

    @property
    def ylen(self) -> float:
        return self.ymax - self.ymin

    @property
    def zlen(self) -> float:
        return self.zmax - self.zmin


@dataclass
class ColoredAssembly:
    """Named, RGBA-colored shapes kept separate (not fused), for glTF export."""

    parts: list[tuple[str, Any, tuple[float, float, float, float]]] = field(default_factory=list)


def require_cad() -> Any:
    """Return the build123d module, importing it lazily.

    Raises
    ------
    ImportError
        If build123d is not installed.
    """
    global _b3d_module, _import_error
    if _b3d_module is None:
        try:
            _b3d_module = importlib.import_module("build123d")
        except ImportError as exc:  # pragma: no cover - depends on env
            _import_error = exc
            raise
    return _b3d_module


def cad_available() -> bool:
    """True if build123d can be imported in this environment."""
    if _b3d_module is None and _import_error is None:
        try:
            require_cad()
        except ImportError:
            return False
    return _import_error is None


def _is_empty(shape: Any) -> bool:
    return shape is None or not shape.faces()


def _top_or_bottom_face(shape: Any, face_ref: FaceRef) -> Any:
    b3d = require_cad()
    faces = shape.faces().sort_by(b3d.Axis.Z)
    return faces[-1] if face_ref is FaceRef.TOP else faces[0]


def box_centered(width: float, depth: float, height: float) -> Any:
    """Return a solid box centered on the local origin (extents in mm)."""
    return require_cad().Box(width, depth, height)


def cylinder_centered(diameter: float, height: float) -> Any:
    """Return a solid cylinder centered on the local origin, axis along Z."""
    return require_cad().Cylinder(diameter / 2.0, height)


def frustum_centered(bottom_diameter: float, top_diameter: float, height: float) -> Any:
    """Return a solid frustum centered on the local origin, axis along Z.

    Bottom face (``bottom_diameter``) at local ``z = -height / 2``, top face
    (``top_diameter``) at ``z = +height / 2`` — the same Z convention as
    :func:`cylinder_centered`, so callers translate it up by ``height / 2``
    to seat the bottom face at ``z = 0``. Equal diameters degenerate to a
    plain cylinder.
    """
    b3d = require_cad()
    if bottom_diameter == top_diameter:
        return b3d.Cylinder(bottom_diameter / 2.0, height)
    return b3d.Cone(bottom_diameter / 2.0, top_diameter / 2.0, height)


def draft_inset(angle_deg: float, height: float) -> float:
    """Horizontal inset of a drafted wall over ``height`` mm (mm).

    ``angle_deg`` is measured from vertical. Used to derive the narrow face of
    a drafted box from its wide face.
    """
    return math.tan(math.radians(angle_deg)) * height


def inner_corner_chamfer(chamfer: float, wall: float) -> float:
    """The cavity's corner chamfer that keeps ``wall`` mm of material (mm).

    The outer shell's vertical corners are chopped by ``chamfer`` (chamfer
    first). A *square* cavity corner sits ``(2 * wall - chamfer) / sqrt(2)``
    from that face — zero for the default 4 mm chamfer on a 2 mm wall, i.e. a
    knife edge that prints as a hole. Chopping the cavity by
    ``chamfer - wall * (2 - sqrt(2))`` puts the inner chamfer face exactly one
    ``wall`` from the outer one, so the corner is as thick as the walls.
    Clamped at zero: a small outer chamfer needs no inner relief.
    """
    return max(0.0, chamfer - wall * (2.0 - math.sqrt(2.0)))


def _rect_vertices(
    width: float, depth: float, chamfer: float
) -> list[tuple[float, float]]:
    """CCW vertices of a rectangle, optionally with its four corners chopped.

    The chamfered form is an octagon so a ruled loft between two such outlines
    keeps a flat 45 degree face at each corner (chamfer-first, never a fillet).
    """
    if width <= 0.0 or depth <= 0.0:
        raise ValueError("tapered box needs positive width and depth")
    half_w, half_d = width / 2.0, depth / 2.0
    c = min(max(chamfer, 0.0), half_w, half_d)
    if c <= 0.0:
        return [
            (-half_w, -half_d),
            (half_w, -half_d),
            (half_w, half_d),
            (-half_w, half_d),
        ]
    return [
        (-half_w + c, -half_d),
        (half_w - c, -half_d),
        (half_w, -half_d + c),
        (half_w, half_d - c),
        (half_w - c, half_d),
        (-half_w + c, half_d),
        (-half_w, half_d - c),
        (-half_w, -half_d + c),
    ]


def tapered_box(
    bottom_width: float,
    bottom_depth: float,
    top_width: float,
    top_depth: float,
    z0: float,
    z1: float,
    chamfer: float = 0.0,
    x: float = 0.0,
    y: float = 0.0,
) -> Any:
    """Loft a solid between two rectangular outlines at ``z0`` and ``z1``.

    The side faces are ruled planes, so a width change drafts the walls. With
    ``chamfer > 0`` both outlines are octagons and the outer corners stay
    chopped (chamfer-first). The solid spans exactly ``z0..z1``.
    """
    if z1 <= z0:
        raise ValueError("tapered box needs z1 > z0")
    bottom = _rect_vertices(bottom_width, bottom_depth, chamfer)
    top = _rect_vertices(top_width, top_depth, chamfer)
    return loft_between(bottom, top, z1 - z0, x=x, y=y, z=z0)


def translate(shape: Any, x: float, y: float, z: float) -> Any:
    """Translate a shape by an absolute (x, y, z) offset in mm."""
    return require_cad().Pos(x, y, z) * shape


def rotate_about(
    shape: Any,
    p0: tuple[float, float, float],
    p1: tuple[float, float, float],
    angle_deg: float,
) -> Any:
    """Rotate a shape ``angle_deg`` degrees about the axis through ``p0``/``p1``.

    Right-handed about the ``p0 -> p1`` direction. Needed where the axis
    doesn't pass through the origin (e.g. the clamshell "open" transform in
    ``main.py``, which rotates about the hinge line).
    """
    b3d = require_cad()
    direction = tuple(b - a for a, b in zip(p0, p1))
    return shape.rotate(b3d.Axis(origin=p0, direction=direction), angle_deg)


def mirror_z(shape: Any) -> Any:
    """Mirror ``shape`` through the XY plane (``z -> -z``)."""
    b3d = require_cad()
    return b3d.mirror(shape, b3d.Plane.XY)


def rotate_x(shape: Any, angle_deg: float) -> Any:
    """Rotate a shape about the X axis through the origin."""
    return rotate_about(shape, (0, 0, 0), (1, 0, 0), angle_deg)


def rotate_y(shape: Any, angle_deg: float) -> Any:
    """Rotate a shape about the Y axis through the origin."""
    return rotate_about(shape, (0, 0, 0), (0, 1, 0), angle_deg)


def rotate_z(shape: Any, angle_deg: float) -> Any:
    """Rotate a shape about the Z axis through the origin."""
    return rotate_about(shape, (0, 0, 0), (0, 0, 1), angle_deg)


def union(shape: Any, *others: Any) -> Any:
    """Boolean-union ``shape`` with one or more other shapes (empties skipped)."""
    parts = [s for s in (shape, *others) if not _is_empty(s)]
    if not parts:
        return empty_solid()
    if len(parts) == 1:
        return parts[0]
    return parts[0].fuse(*parts[1:])


def cut(shape: Any, *tools: Any) -> Any:
    """Boolean-subtract one or more ``tools`` from ``shape`` (empties skipped)."""
    tools = [t for t in tools if not _is_empty(t)]
    if not tools or _is_empty(shape):
        return shape
    return shape.cut(*tools)


def intersect(shape: Any, other: Any) -> Any:
    """Boolean-intersect ``shape`` with ``other``."""
    if _is_empty(shape) or _is_empty(other):
        return empty_solid()
    # build123d's ``intersect`` returns a list of shapes (or ``None``).
    found = shape.intersect(other)
    if not found:
        return empty_solid()
    return found[0] if len(found) == 1 else make_compound(list(found))


def clean(shape: Any) -> Any:
    """Run OCC shape healing on ``shape``.

    Needed after a union/cut whose result has sliver or degenerate topology
    at a seam (harmless for STEP/STL export, but can crash the SVG
    exporter's hidden-line removal) — see ``main.py``'s base+deck union for
    the concrete case this guards against.
    """
    return shape.clean()


def chamfer_vertical_edges(shape: Any, length: float) -> Any:
    """Chamfer only the Z-parallel (vertical) edges of ``shape``.

    The chamfer-first treatment: the four vertical corners of a case shell,
    a Bearing clamp's base and its chassis pocket get a 45-degree chamfer
    while the top/bottom edges stay square. Never a fillet on these — an
    outside corner is always chopped (``docs/design_spec.md``).
    """
    b3d = require_cad()
    return b3d.chamfer(shape.edges().filter_by(b3d.Axis.Z), length)


def chamfer_face_edges(shape: Any, face_ref: FaceRef, length: float) -> Any:
    """Chamfer the perimeter edges of ``shape``'s top or bottom face."""
    face = _top_or_bottom_face(shape, face_ref)
    return require_cad().chamfer(face.edges(), length)


def shell_open_face(shape: Any, wall_thickness: float, face_ref: FaceRef) -> Any:
    """Hollow ``shape``, leaving ``wall_thickness`` mm of material, open at ``face_ref``.

    The outer boundary stays fixed while hollowing inward; ``face_ref``
    selects which face (top or bottom) is removed to open the shell.
    """
    b3d = require_cad()
    face = _top_or_bottom_face(shape, face_ref)
    return b3d.offset(shape, amount=-wall_thickness, openings=face)


def sketch_slots(
    points: list[tuple[float, float]], width: float, length: float, depth: float
) -> Any:
    """Return a compound of rectangular slot solids, one per XY point.

    Each slot is ``width`` (X) by ``length`` (Y), extruded ``depth`` along Z
    from the XY plane. Used for vent slot cutters. Returns an empty solid if
    ``points`` is empty.
    """
    if not points:
        return empty_solid()
    slots = [
        translate(box_centered(width, length, depth), x, y, depth / 2.0) for x, y in points
    ]
    return make_compound(slots)


def empty_solid() -> Any:
    """Return an empty shape — a sentinel for "nothing to build here"."""
    return require_cad().Compound()


def new_assembly() -> ColoredAssembly:
    """Return a new, empty colored assembly."""
    return ColoredAssembly()


def assembly_add(
    assembly: ColoredAssembly,
    shape: Any,
    name: str,
    rgba: tuple[float, float, float, float],
) -> None:
    """Add ``shape`` to ``assembly`` as a named child with an RGBA color."""
    assembly.parts.append((name, shape, rgba))


def is_assembly(obj: Any) -> bool:
    """True if ``obj`` is a colored assembly (vs. a bare shape/solid)."""
    return isinstance(obj, ColoredAssembly)


def export_shape(shape: Any, path: str, fmt: str) -> None:
    """Export ``shape`` to ``path`` in ``fmt`` (``"STEP"`` or ``"STL"``).

    SVG goes through :func:`export_svg` instead; it is a 2D projection with
    its own options.
    """
    b3d = require_cad()
    fmt = fmt.upper()
    if fmt == "STEP":
        b3d.export_step(shape, str(path))
    elif fmt == "STL":
        b3d.export_stl(shape, str(path))
    else:
        raise ValueError(f"unsupported export format {fmt!r}")


def export_svg(shape: Any, path: str) -> None:
    """Export a hidden-line-removed isometric projection of ``shape`` as SVG."""
    b3d = require_cad()
    # Look from a fixed world-space direction at the world origin, so every
    # part (base, lid, hinge, ...) is projected from the same angle rather
    # than from one relative to its own center.
    visible, hidden = shape.project_to_viewport(SVG_VIEW_DIRECTION, look_at=(0.0, 0.0, 0.0))
    exporter = b3d.ExportSVG(scale=SVG_SCALE)
    exporter.add_layer("Visible")
    exporter.add_layer("Hidden", line_type=b3d.LineType.ISO_DOT, line_weight=SVG_HIDDEN_LINE_WEIGHT)
    exporter.add_shape(visible, layer="Visible")
    exporter.add_shape(hidden, layer="Hidden")
    exporter.write(str(path))


def export_assembly(assembly: ColoredAssembly, path: str, fmt: str) -> None:
    """Export a colored assembly (see :func:`new_assembly`) to ``path``.

    Only glTF is supported; binary ``.glb`` vs. text ``.gltf`` follows the
    file extension.
    """
    b3d = require_cad()
    if fmt.upper() != "GLTF":
        raise ValueError(f"unsupported assembly export format {fmt!r}")
    children = []
    for name, shape, rgba in assembly.parts:
        part = shape.moved(b3d.Location())  # copy: don't tint the caller's shape
        part.label = name
        part.color = b3d.Color(*rgba)
        children.append(part)
    root = b3d.Compound(children=children, label="assembly")
    b3d.export_gltf(root, str(path), binary=str(path).lower().endswith(".glb"))


def import_step(path: str) -> Any:
    """Import a STEP file as a shape."""
    return require_cad().import_step(str(path))


def _ccw(vertices: list[tuple[float, float]]) -> list[tuple[float, float]]:
    """Return ``vertices`` wound counter-clockwise (positive signed area)."""
    area = sum(
        x0 * y1 - x1 * y0
        for (x0, y0), (x1, y1) in zip(vertices, vertices[1:] + vertices[:1])
    )
    return list(vertices) if area >= 0 else list(reversed(vertices))


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
    """
    b3d = require_cad()
    wire = b3d.Wire.make_polygon([(vx, vy, 0.0) for vx, vy in _ccw(vertices)], close=True)
    solid = b3d.extrude(b3d.Face(wire), amount=height)
    return translate(solid, x, y, z - height / 2.0)


def loft_between(
    bottom_verts: list[tuple[float, float]],
    top_verts: list[tuple[float, float]],
    height: float,
    x: float = 0.0,
    y: float = 0.0,
    z: float = 0.0,
) -> Any:
    """Loft a solid between two closed polygon wires.

    The bottom wire lies on the XY plane; the top wire is offset by *height*
    along Z. Both wires must have the **same number of vertices** in the
    **same angular order** (CCW from +X) to produce an untwisted ruled loft.

    The resulting solid is translated so its **bottom** face sits at *z*.
    """
    b3d = require_cad()
    bottom = b3d.Wire.make_polygon([(vx, vy, 0.0) for vx, vy in bottom_verts], close=True)
    top = b3d.Wire.make_polygon([(vx, vy, height) for vx, vy in top_verts], close=True)
    solid = b3d.Solid.make_loft([bottom, top], ruled=True)
    return translate(solid, x, y, z)


def make_compound(shapes: list[Any]) -> Any:
    """Return one unfused compound containing the solids of *shapes*.

    Use this to batch many solids before a single :func:`union` — far faster
    than N sequential unions because OCC processes the whole compound in one
    boolean operation.
    """
    b3d = require_cad()
    solids = list(chain.from_iterable(s.solids() for s in shapes if not _is_empty(s)))
    return b3d.Compound(solids) if solids else empty_solid()


def split_x(shape: Any, at: float = 0.0) -> tuple[Any, Any]:
    """Split ``shape`` into the parts with x <= at and x >= at.

    The two halves are exact intersections with half-space slabs, so their
    volumes add back to the original (a butt joint with no material lost).
    Used to turn a part into its printable Sections.
    """
    box = bounding_box(shape)
    reach = 2.0 * (box.xlen + box.ylen + box.zlen) + 20.0
    y_mid = (box.ymin + box.ymax) / 2.0
    z_mid = (box.zmin + box.zmax) / 2.0
    size = box_centered(reach, 2.0 * reach, 2.0 * reach)
    left = translate(size, at - reach / 2.0, y_mid, z_mid)
    right = translate(size, at + reach / 2.0, y_mid, z_mid)
    return intersect(shape, left), intersect(shape, right)


def split_x_stepped(
    shape: Any, at: float = 0.0, step: float = 4.0, steps: int = 6
) -> tuple[Any, Any]:
    """Split ``shape`` at a stepped Seam (``__--__--__``) along X.

    Kept for ad-hoc tests; the configured split lives in
    :mod:`geometry.split`, which also cuts trapezoid Seams.
    """
    if steps < 2 or step <= 0.0:
        return split_x(shape, at)
    box = bounding_box(shape)
    y0, y1 = box.ymin, box.ymax
    segment = (y1 - y0) / steps
    seam: list[tuple[float, float]] = []
    for index in range(steps):
        x = at + (step / 2.0 if index % 2 == 0 else -step / 2.0)
        seam.append((x, y0 + index * segment))
        seam.append((x, y0 + (index + 1) * segment))
    reach = 2.0 * (box.xlen + box.ylen + box.zlen) + 20.0
    height = box.zlen + 2.0 * reach
    z_mid = (box.zmin + box.zmax) / 2.0
    right_poly = seam + [(at + reach, y1), (at + reach, y0)]
    left_poly = seam + [(at - reach, y1), (at - reach, y0)]
    right = extrude_polygon(right_poly, height, z=z_mid)
    left = extrude_polygon(left_poly, height, z=z_mid)
    return intersect(shape, left), intersect(shape, right)


def split_sections(shape: Any, spec: Any = None, at: float = 0.0) -> tuple[Any, Any]:
    """Split ``shape`` along X, honouring a straight or stepped ``Split``.

    Deprecated for build use: a configured part is split with
    :func:`geometry.split.split_part`, which also cuts trapezoid Seams and
    returns every Section.
    """
    if spec is not None:
        at = float(getattr(spec, "x", at))
        if str(getattr(spec, "style", "straight")) == "stepped":
            return split_x_stepped(
                shape,
                at=at,
                step=float(getattr(spec, "step", 4.0)),
                steps=int(getattr(spec, "steps", 6)),
            )
    return split_x(shape, at=at)


def bounding_box(shape: Any) -> BBox:
    """Return the bounding box of ``shape`` with min/max/length accessors.

    Prefer :func:`bounding_box_mm` where only the extents are needed; this
    is for callers (debug renderers) that need the min/max corners too.
    """
    box = shape.bounding_box()
    return BBox(box.min.X, box.max.X, box.min.Y, box.max.Y, box.min.Z, box.max.Z)


def bounding_box_mm(shape: Any) -> tuple[float, float, float]:
    """Return (width, depth, height) in mm of a shape."""
    box = bounding_box(shape)
    return (box.xlen, box.ylen, box.zlen)


def volume_mm3(shape: Any) -> float:
    """Return the solid volume in mm^3 — used for geometry regression checks."""
    return shape.volume


def center_of_mass_mm(shape: Any) -> tuple[float, float, float]:
    """Return the (x, y, z) center of mass in mm."""
    center = shape.center()
    return (center.X, center.Y, center.Z)


def face_count(shape: Any) -> int:
    """Return the number of faces in the shape."""
    return len(shape.faces())


def solid_count(shape: Any) -> int:
    """Return the number of solids in the shape."""
    return len(shape.solids())


def extrude_profile_x(vertices_yz: list[tuple[float, float]], length: float) -> Any:
    """Extrude a closed (Y, Z) polygon along X, centered on ``x = 0``."""
    b3d = require_cad()
    wire = b3d.Wire.make_polygon([(0.0, vy, vz) for vy, vz in vertices_yz], close=True)
    return b3d.extrude(b3d.Face(wire), amount=length / 2.0, both=True)


#: How far (mm) the support cap's blank runs past the height where its 45
#: degree faces meet, so the boolean trims the top to a clean edge instead of
#: leaving a zero-width face.
_CAP_TRIM = 0.5


def support_cap(
    rect: tuple[float, float, float, float],
    z0: float,
    free_x: tuple[bool, bool] = (False, False),
    free_y: tuple[bool, bool] = (False, False),
) -> Any:
    """The 45 degree cap a face-down printed boss needs under its flat top.

    A boss that is merged into a wall and stops short of the part's ceiling
    leaves a horizontal top face. Printed face down, that face is the boss's
    *first* layer, with nothing under it but the wall it touches, so the
    printer has to bridge a ledge instead of stacking on support (45 degrees
    from vertical is the self-supporting limit). The cap is the material that
    rides on the ledge: it tapers away from every **free** side (a side facing
    the cavity) at 45 degrees until the taper runs out at the wall, so each
    layer is carried by the one above it. A side merged into a wall stays
    straight, and the boss keeps its full footprint below ``z0`` -- the cap
    only replaces the ledge, it does not make the boss a full column.

    Parameters
    ----------
    rect : tuple
        The boss's footprint as ``(x0, x1, y0, y1)``; the cap stands on it.
    z0 : float
        The boss's top face -- the ledge the cap supports.
    free_x, free_y : tuple[bool, bool]
        Per axis, which side is free as ``(low side, high side)``. Two free
        sides of one axis are tapered from both ends toward the middle.

    Returns
    -------
    Shape
        The cap solid standing on ``z0``, or an empty solid when every side is
        merged into a wall. Union it into the boss before the shell booleans.
    """
    x0, x1, y0, y1 = rect
    low_x, high_x = free_x
    low_y, high_y = free_y
    width, depth = x1 - x0, y1 - y0
    # Where each axis' taper runs out: a single free side crosses the whole
    # boss, two free sides of the same axis meet in the middle.
    collapses = []
    if low_x or high_x:
        collapses.append(width if low_x != high_x else width / 2.0)
    if low_y or high_y:
        collapses.append(depth if low_y != high_y else depth / 2.0)
    if not collapses:
        return empty_solid()
    height = min(collapses) + _CAP_TRIM
    reach = width + depth + height + 10.0

    body = box_centered(width, depth, height)
    body = translate(body, (x0 + x1) / 2.0, (y0 + y1) / 2.0, z0 + height / 2.0)

    def taper(edge: float, sign: int, along_x: bool) -> Any:
        """The 45 degree half-space on the free side of the face at ``edge``.

        ``sign`` is -1 for the low side and +1 for the high one: the face's
        top edge rises into the boss, so the plane moves *inward* with height.
        """
        inner = edge - sign * height
        outer = edge + sign * reach
        other = (y0 - reach, y1 + reach) if along_x else (x0 - reach, x1 + reach)

        def point(moving: float, fixed: float) -> tuple[float, float]:
            return (moving, fixed) if along_x else (fixed, moving)

        bottom = [
            point(outer, other[0]),
            point(edge, other[0]),
            point(edge, other[1]),
            point(outer, other[1]),
        ]
        top = [
            point(outer, other[0]),
            point(inner, other[0]),
            point(inner, other[1]),
            point(outer, other[1]),
        ]
        return loft_between(bottom, top, height, z=z0)

    tools = []
    if low_x:
        tools.append(taper(x0, -1, along_x=True))
    if high_x:
        tools.append(taper(x1, 1, along_x=True))
    if low_y:
        tools.append(taper(y0, -1, along_x=False))
    if high_y:
        tools.append(taper(y1, 1, along_x=False))
    return cut(body, *tools)


# -- Face queries (printability, edge treatment) ------------------------------

def faces(shape: Any) -> list[Any]:
    """Every face of ``shape``."""
    return list(shape.faces())


def is_planar(face: Any) -> bool:
    """True for a planar face."""
    return face.is_planar


def face_area(face: Any) -> float:
    return face.area


def face_center(face: Any) -> tuple[float, float, float]:
    c = face.center()
    return (c.X, c.Y, c.Z)


def face_normal(face: Any) -> tuple[float, float, float]:
    """Outward unit normal of a planar face."""
    n = face.normal_at()
    return (n.X, n.Y, n.Z)


def face_sample_normals(face: Any, grid: int = 3) -> list[tuple[float, float, float]]:
    """Outward unit normals sampled across ``face`` (one for a planar face)."""
    if face.is_planar:
        return [face_normal(face)]
    out = []
    for i in range(grid):
        for j in range(grid):
            u, v = (i + 0.5) / grid, (j + 0.5) / grid
            try:
                n = face.normal_at(face.position_at(u, v))
            except Exception:  # degenerate parametrisation: skip the sample
                continue
            out.append((n.X, n.Y, n.Z))
    return out or [face_normal(face)]


# -- Edge queries and treatment (geometry.edge_treatment) -----------------------

@dataclass(frozen=True)
class EdgeInfo:
    """An edge located by where it is, so it can be found again after a boolean.

    ``key`` is the edge midpoint and length, rounded to a micron; ``tangent``
    is the unit tangent at the midpoint; ``curve_type`` is the OCC geometry
    class (``"line"``, ``"circle"``, ...) so a caller can treat only straight
    edges (a chamfer along an arc is a different, much fussier operation).
    """

    key: tuple[float, float, float, float]
    length: float
    tangent: tuple[float, float, float]
    curve_type: str = "line"

    @property
    def midpoint(self) -> tuple[float, float, float]:
        return self.key[:3]


def _edge_key(edge: Any) -> tuple[float, float, float, float]:
    p = edge.position_at(0.5)
    return (round(p.X, 3), round(p.Y, 3), round(p.Z, 3), round(edge.length, 3))


def _unit(v: Any) -> tuple[float, float, float]:
    n = v.length or 1.0
    return (v.X / n, v.Y / n, v.Z / n)


def _is_concave(shape: Any, edge: Any, faces: list[Any]) -> bool:
    """True where the two faces at ``edge`` meet at an inside corner of ``shape``.

    Walk off the edge along face 1 (in its plane, away from the edge): if face
    2's outward normal points the way we walked, the material wraps around the
    edge, i.e. it is concave.
    """
    b3d = require_cad()
    f1, f2 = faces
    mid = edge.position_at(0.5)
    t = edge.tangent_at(0.5)
    n1 = f1.normal_at(mid)
    n2 = f2.normal_at(mid)
    d = n1.cross(t)
    if d.length < 1e-9:
        return False
    d = d.normalized()
    for sign in (1.0, -1.0):
        probe = mid + d * (0.01 * sign)
        if f1.distance_to(b3d.Vertex(probe.X, probe.Y, probe.Z)) < 1e-4:
            return (d * sign).dot(n2) > 1e-6
    return False


def _edge_faces(shape: Any) -> list[tuple[Any, list[Any]]]:
    """``(edge, [faces at that edge])`` for every edge of ``shape``."""
    from OCP.TopAbs import TopAbs_EDGE, TopAbs_FACE
    from OCP.TopExp import TopExp
    from OCP.TopoDS import TopoDS
    from OCP.TopTools import TopTools_IndexedDataMapOfShapeListOfShape

    b3d = require_cad()
    table = TopTools_IndexedDataMapOfShapeListOfShape()
    TopExp.MapShapesAndAncestors_s(shape.wrapped, TopAbs_EDGE, TopAbs_FACE, table)
    pairs = []
    for i in range(1, table.Extent() + 1):
        edge = b3d.Edge(TopoDS.Edge_s(table.FindKey(i)))
        faces = [b3d.Face(TopoDS.Face_s(f)) for f in table.FindFromIndex(i)]
        pairs.append((edge, faces))
    return pairs


def concave_edges(shape: Any) -> list[EdgeInfo]:
    """Every inside-corner edge of ``shape``."""
    found = []
    for edge, faces in _edge_faces(shape):
        if len(faces) != 2:
            continue
        try:
            if not _is_concave(shape, edge, faces):
                continue
        except Exception:  # a degenerate edge: leave it alone
            continue
        found.append(EdgeInfo(
            key=_edge_key(edge), length=edge.length, tangent=_unit(edge.tangent_at(0.5)),
            curve_type=edge.geom_type.name.lower(),
        ))
    return found


def convex_edges(shape: Any) -> list[EdgeInfo]:
    """Every outside-corner edge of ``shape`` (two faces meeting at an angle)."""
    found = []
    for edge, faces in _edge_faces(shape):
        if len(faces) != 2:
            continue
        try:
            mid = edge.position_at(0.5)
            n1, n2 = faces[0].normal_at(mid), faces[1].normal_at(mid)
            if n1.cross(n2).length < 1e-6 or _is_concave(shape, edge, faces):
                continue  # tangent (smooth) or inside corner
        except Exception:  # a degenerate edge: leave it alone
            continue
        found.append(EdgeInfo(
            key=_edge_key(edge), length=edge.length, tangent=_unit(edge.tangent_at(0.5)),
            curve_type=edge.geom_type.name.lower(),
        ))
    return found


def bed_boundary_edges(shape: Any, normal: tuple[float, float, float], tol: float = 1e-3) -> list[EdgeInfo]:
    """Outer-boundary edges of the planar face(s) lying on the bed (convex or not)."""
    extreme = max(
        sum(c * n for c, n in zip((x, y, z), normal))
        for x in (shape.bounding_box().min.X, shape.bounding_box().max.X)
        for y in (shape.bounding_box().min.Y, shape.bounding_box().max.Y)
        for z in (shape.bounding_box().min.Z, shape.bounding_box().max.Z)
    )
    found = []
    for face in shape.faces():
        if not face.is_planar:
            continue
        fn = face.normal_at()
        if fn.X * normal[0] + fn.Y * normal[1] + fn.Z * normal[2] < 1.0 - 1e-4:
            continue
        c = face.center()
        if abs(c.X * normal[0] + c.Y * normal[1] + c.Z * normal[2] - extreme) > tol:
            continue
        for edge in face.outer_wire().edges():
            found.append(EdgeInfo(
                key=_edge_key(edge), length=edge.length,
                tangent=_unit(edge.tangent_at(0.5)),
                curve_type=edge.geom_type.name.lower(),
            ))
    return found


def _locate(shape: Any, infos: list[EdgeInfo]) -> list[Any]:
    wanted = {info.key for info in infos}
    return [edge for edge in shape.edges() if _edge_key(edge) in wanted]


def _checked(before: Any, after: Any) -> Any:
    if after is None or not after.is_valid or len(after.solids()) < 1:
        raise ValueError("edge treatment produced an invalid solid")
    if len(after.solids()) != len(before.solids()):
        raise ValueError("edge treatment changed the solid count")
    return after


_POOL: Any = None


def _pool() -> Any:
    global _POOL
    if _POOL is None:
        import multiprocessing
        from concurrent.futures import ProcessPoolExecutor

        import atexit

        _POOL = ProcessPoolExecutor(max_workers=1, mp_context=multiprocessing.get_context("spawn"))
        atexit.register(_POOL.shutdown, wait=False, cancel_futures=True)
    return _POOL


def _isolated(shape: Any, infos: list[EdgeInfo], size: float, mode: str) -> Any:
    """Chamfer/fillet in a child process, so an OCC segfault only fails the attempt."""
    import os
    import tempfile
    from concurrent.futures.process import BrokenProcessPool

    from utilities import _cad_worker

    global _POOL
    b3d = require_cad()
    with tempfile.TemporaryDirectory() as tmp:
        src, dst = os.path.join(tmp, "in.brep"), os.path.join(tmp, "out.brep")
        b3d.export_brep(shape, src)
        future = _pool().submit(_cad_worker.treat, src, dst, mode, [list(i.key) for i in infos], size)
        try:
            future.result(timeout=120)
        except BrokenProcessPool as exc:
            _POOL = None
            raise ValueError("OCC crashed on this edge treatment") from exc
        except Exception as exc:
            raise ValueError(f"edge treatment failed: {exc}") from exc
        result = b3d.import_brep(dst)
    solids = result.solids()
    if len(solids) != len(shape.solids()):
        raise ValueError("edge treatment changed the solid count")
    return solids[0] if len(solids) == 1 else result


def chamfer_edges(shape: Any, infos: list[EdgeInfo], size: float) -> Any:
    """Chamfer the edges at ``infos`` by ``size`` mm; raises if OCC cannot."""
    if not _locate(shape, infos):
        return shape
    return _isolated(shape, infos, size, "chamfer")


def fillet_edges(shape: Any, infos: list[EdgeInfo], size: float) -> Any:
    """Fillet the edges at ``infos`` by ``size`` mm; raises if OCC cannot."""
    if not _locate(shape, infos):
        return shape
    return _isolated(shape, infos, size, "fillet")
