"""Edge treatment of concave joints and bed faces (ADR 0003).

The case is chamfer-first (``docs/design_spec.md`` § Edge Treatment): every
outside face and every bed-facing edge gets a 45 degree chamfer, never a
fillet. Inside joints get a stress-relief edge so printed parts don't crack at
sharp inside corners: a 45 degree chamfer where the edge is horizontal in
print orientation (a fillet there would print as a curved overhang). The only
fillets in the build are the vertical concave joints, where a smooth relief
beats a sharp rebate and the joint is hidden inside the assembly — a fillet
along print Z prints cleanly.

A stepped Seam leaves each Section a notch on one side of a step and a tab on
the other. The notch's inside corner gets the concave relief above, so the
tab's corner that fits into it is treated too, a little larger
(``round_seam_corners``), or the two would not mate. Both are hidden inside
the joined part.

A column standing against a cavity wall crosses that wall face, and the two
vertical chords it leaves there are the same inside corner in the most handled
part of the case; ``merge_column_walls`` fillets them (ADR-0024).

OCC cannot always apply a chamfer (tight spots, thin neighbours). The edges
are tried together and, on failure, split in halves until the failing edge is
isolated; that edge is skipped and recorded as a SOFT warning, so a tight spot
never blocks the build. All CAD calls go through :mod:`utilities.cad_helpers`.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from geometry.printability import BED_DOWN, PrintOrientation
from utilities import cad_helpers

#: |tangent . bed normal| below this is horizontal, above its complement vertical.
_HORIZONTAL = 0.35
_VERTICAL = 0.94


@dataclass(frozen=True)
class ConcaveEdge:
    """A concave edge and how it runs relative to the bed."""

    info: cad_helpers.EdgeInfo

    def alignment(self, orientation: PrintOrientation) -> float:
        return abs(sum(t * n for t, n in zip(self.info.tangent, orientation.normal)))

    def horizontal(self, orientation: PrintOrientation) -> bool:
        return self.alignment(orientation) < _HORIZONTAL

    def vertical(self, orientation: PrintOrientation) -> bool:
        return self.alignment(orientation) > _VERTICAL


def concave_edges(shape) -> list[ConcaveEdge]:
    """The inside-corner edges of ``shape``."""
    return [ConcaveEdge(info) for info in cad_helpers.concave_edges(shape)]


def _apply(shape, infos, size: float, treat, label: str, report):
    """Treat ``infos`` on ``shape``, isolating and skipping any that fail."""
    if not infos:
        return shape
    try:
        return treat(shape, infos, size)
    except Exception:
        if len(infos) == 1:
            x, y, z, length = infos[0].key
            report.warn(
                f"{label} {size:g} mm skipped at ({x:g}, {y:g}, {z:g}), edge {length:g} mm: "
                "does not fit"
            )
            return shape
    half = len(infos) // 2
    shape = _apply(shape, infos[:half], size, treat, label, report)
    return _apply(shape, infos[half:], size, treat, label, report)


def relieve_concave_joints(shape, orientation: PrintOrientation, size: float, report):
    """Relieve the inside joints of ``shape`` by ``size`` mm.

    Horizontal (and slanted) concave edges are chamfered. Vertical concave
    edges are the one sanctioned fillet use: the relief is hidden inside the
    assembly and a fillet along print Z prints cleanly. ``orientation`` is the
    part's print orientation. Edges that don't take the treatment are skipped
    with a SOFT warning on ``report``.
    """
    if size <= 0.0:
        return shape
    edges = concave_edges(shape)
    vertical = [e.info for e in edges if e.vertical(orientation)]
    other = [e.info for e in edges if not e.vertical(orientation)]
    # Horizontal and slanted edges first: chamfers add no overhang.
    shape = _apply(shape, other, size, cad_helpers.chamfer_edges, "concave chamfer", report)
    # The verticals' keys survive the chamfers: only edges touching them moved.
    return _apply(shape, vertical, size, cad_helpers.fillet_edges, "concave fillet", report)


def bed_chamfer(shape, orientation: PrintOrientation, size: float, report):
    """Chamfer the outer edge of the bed face by ``size`` mm (elephant's foot)."""
    if size <= 0.0:
        return shape
    infos = cad_helpers.bed_boundary_edges(shape, orientation.normal)
    return _apply(shape, infos, size, cad_helpers.chamfer_edges, "bed-edge chamfer", report)


def seam_corner_points(seams, depth: float) -> list[tuple[float, float]]:
    """XY of every corner along ``seams`` (anything with
    ``polyline(depth) -> [(x, y)]``), i.e. both ends of every jog."""
    points = []
    for seam in seams:
        points += list(seam.polyline(depth))[1:-1]
    return points


def round_seam_corners(shape, orientation: PrintOrientation, seams, depth: float, radius: float, report, tol: float = 1e-2):
    """Fillet the outside corners at the steps of ``seams`` by ``radius`` mm.

    Only edges running along print Z through a step corner are touched: the
    tab corners that nest in the concave-filleted notches of the neighbouring
    Section. The joint is hidden inside the assembled part, so this is an
    inside treatment, not an outside face. Edges that don't take the fillet
    are skipped with a SOFT warning.
    """
    points = seam_corner_points(seams, depth)
    if radius <= 0.0 or not points:
        return shape
    infos = [
        info for info in cad_helpers.convex_edges(shape)
        if ConcaveEdge(info).vertical(orientation)
        and any(abs(info.key[0] - x) < tol and abs(info.key[1] - y) < tol for x, y in points)
    ]
    return _apply(shape, infos, radius, cad_helpers.fillet_edges, "seam corner fillet", report)


def cone_cut_edges(
    shape: Any, angle_deg: float, bed_z: float
) -> tuple[list[cad_helpers.EdgeInfo], list[cad_helpers.EdgeInfo]]:
    """The access cones' outside edges, split into mouth rims and lips (ADR-0023).

    A **rim** borders a conical face and a horizontal plane at the part's bed
    (``bed_z``) -- the mouth ring where the access cone or the column frustum
    leaves the floor face. A **lip** borders a conical face and the taper's
    *outer* sloped face (a plane tilted ``angle_deg`` off vertical with a
    downward normal, ``nz < 0``) -- where the taper's slice flares the cone
    open. Everything else stays sharp: the pocket's neck ring (cone against
    the cylindrical pocket), the clearance hole, the interior rings where a
    cone breaks the cavity floor, the flares against the cavity-side draft
    (their slope faces up, ``nz > 0``), and in particular the long edges
    where the front/rear walls meet the floor -- the fillet is only ever on
    the cones' own outside edges.
    """
    tilt = math.sin(math.radians(angle_deg))
    infos: dict[tuple, cad_helpers.EdgeInfo] = {}
    kinds: dict[tuple, set[str]] = {}
    on_bed: dict[tuple, bool] = {}
    outer_lip: dict[tuple, bool] = {}
    for face in cad_helpers.faces(shape):
        kind = cad_helpers.face_kind(face)
        bed_face = False
        slope_face = False
        if kind == "plane":
            normal = cad_helpers.face_normal(face)
            if abs(normal[2]) >= 0.9:
                bed_face = abs(cad_helpers.face_center(face)[2] - bed_z) <= 0.05
            elif abs(abs(normal[2]) - tilt) <= 0.05 and normal[2] < 0.0:
                # the taper's outer slope leans outward as it rises, so its
                # normal tilts down; the cavity-side draft's tilts up
                slope_face = True
        for wire in face.wires():
            for edge in wire.edges():
                info = cad_helpers.edge_info(edge)
                bucket = infos.setdefault(info.key, info)
                kinds.setdefault(bucket.key, set()).add(kind)
                on_bed[bucket.key] = on_bed.get(bucket.key, False) or bed_face
                outer_lip[bucket.key] = (
                    outer_lip.get(bucket.key, False) or slope_face
                )
    rims = [
        info
        for key, info in infos.items()
        if {"cone", "plane"} <= kinds[key] and on_bed[key]
    ]
    lips = [
        info
        for key, info in infos.items()
        if {"cone", "plane"} <= kinds[key] and not on_bed[key] and outer_lip[key]
    ]
    return rims, lips


def round_cone_cut(
    shape: Any,
    angle_deg: float,
    bed_z: float,
    radius: float,
    report: Any,
    lip_radius: float | None = None,
) -> Any:
    """Fillet the access cones' mouth rims by ``radius`` and their lips by
    ``lip_radius`` (ADR-0023; defaults to ``radius``).

    The one fillet on an outside face: the cones' rims and flared lips are
    hard to ease with a chamfer without reading as a second taper, and the
    wall/floor edges stay sharp by construction -- they are never selected.
    Edges that don't take the fillet are skipped with a SOFT warning.
    """
    rims, lips = cone_cut_edges(shape, angle_deg, bed_z)
    shape = _apply(
        shape, rims, radius, cad_helpers.fillet_edges, "cone rim fillet", report
    )
    shape = _apply(
        shape,
        lips,
        radius if lip_radius is None else lip_radius,
        cad_helpers.fillet_edges,
        "cone lip fillet",
        report,
    )
    return shape


def column_junction_edges(
    shape: Any,
    columns: Any,
    faces_y: Any,
    orientation: PrintOrientation = BED_DOWN,
    tol: float = 0.06,
) -> list[cad_helpers.EdgeInfo]:
    """The vertical chords where a column crosses a vertical face (ADR-0024).

    A column whose axis sits a couple of millimetres from a vertical face while
    its radius is larger than that gap pierces the face and leaves two vertical
    reentrant chords on it: a joint station does this to the front/rear cavity
    wall (``chassis_joint.side_inset`` against ``wall``), and a Well boss does it
    to the Well ring's outer face. Those chords are picked here -- and only
    them:

    * the edge must run along print Z, so the merged fillet prints cleanly,
    * its midpoint must lie on one of the vertical faces listed in ``faces_y``
      (the ``|y|`` of each). The X walls, the corner chamfer and any face not
      listed keep their chords sharp,
    * its plan distance from a column's axis must be that column's radius at the
      edge's height.

    ``columns`` are ``(x, y, r_min, r_max)`` quadruples: the axis in plan and
    the band the radius spans over the chord's height (a joint column is a
    frustum below the access cone's neck and a strict cylinder above it, so its
    chord's radius runs from the strict to the base diameter; a Well boss is one
    diameter). ``faces_y`` is one ``|y|`` or a sequence of them.
    """
    faces = (faces_y,) if isinstance(faces_y, (int, float)) else tuple(faces_y)
    found = []
    for edge in concave_edges(shape):
        if not edge.vertical(orientation):
            continue
        x, y, _ = edge.info.key[:3]
        if min(abs(abs(y) - face) for face in faces) > tol:
            continue
        for cx, cy, thin, thick in columns:
            radius = math.hypot(x - cx, y - cy)
            if thin - tol <= radius <= thick + tol:
                found.append(edge.info)
                break
    return found


def merge_column_walls(
    shape: Any,
    columns: Any,
    faces_y: Any,
    radius: float,
    report: Any,
    orientation: PrintOrientation = BED_DOWN,
) -> Any:
    """Fillet the columns' chords into the vertical faces they cross (ADR-0024).

    Wherever a column's disc crosses one of the faces in ``faces_y``, the
    reentrant corner along their chord is eased by ``radius`` mm
    (:func:`column_junction_edges` picks them). The fillet adds a smooth ridge
    where the two surfaces meet -- a crack starter removed from the print in the
    most handled part of the case -- and runs along print Z, so it prints
    cleanly. Apply it while the face still runs the column's full height: the
    base taper and the access cones slice it afterwards, and applied late the
    same edges arrive segmented into stubs a fillet cannot roll off.

    Edges that don't take the fillet are skipped with a SOFT warning on
    ``report``, so a tight spot never blocks the build.
    """
    if radius <= 0.0:
        return shape
    infos = column_junction_edges(shape, columns, faces_y, orientation)
    return _apply(shape, infos, radius, cad_helpers.fillet_edges, "column merge fillet", report)
