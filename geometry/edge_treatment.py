"""Edge treatment of concave joints and bed faces (ADR-0025).

The material dihedral picks the treatment (``docs/design_spec.md`` § Edge
Treatment): a convex (``<= 90`` through the material) edge is an outside face
and gets a 45 degree chamfer, never a fillet; a concave (``>= 270``) edge is a
reentrant corner and gets a fillet so the material rolls from one face into the
other. Judge that in the part's **own print orientation** (``PrintOrientation``,
per part -- the Deck prints face down, so its inner ceiling is the bed face): a
concave joint that opens toward that bed keeps its 45 degree chamfer instead,
because the round would print as a curved overhang; a joint that opens away
from the bed takes the round.

The rule covers every boss base: a boss always meets its floor, wall or ring at
a concave angle, so ``fillet_boss_bases`` rounds the ring where it springs from
its plane (``boss_base_edges`` picks it, and skips it when the cove would open
toward the part's bed). The other built fillets are the vertical concave
joints, where a smooth relief beats a sharp rebate and the joint is hidden
inside the assembly, plus the chords a column or Well boss leaves where it
crosses a face (``merge_column_walls``, ADR-0024).

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


def fillet_junctions(
    shape,
    chord_infos: list[cad_helpers.EdgeInfo],
    base_infos: list[cad_helpers.EdgeInfo],
    chord_radius: float,
    base_radius: float,
    report,
):
    """Fillet a boss's wall chords and its base ring in one pass.

    A boss's vertical chord and its base ring meet at a vertex. Filleting them
    in separate passes cannot work: the second edge ends on the first fillet's
    surface and OCC cannot roll it off. One ``BRepFilletAPI_MakeFillet`` pass
    with a radius per edge builds the corner blend instead. If the combined
    pass fails, fall back to the phased order (chords, then bases) so as much
    as possible is still eased; failing edges are skipped with a SOFT warning.
    """
    if not chord_infos and not base_infos:
        return shape
    pairs = []
    seen = set()
    for info in chord_infos:
        if info.key not in seen:
            seen.add(info.key)
            pairs.append((info, chord_radius))
    for info in base_infos:
        if info.key not in seen:
            seen.add(info.key)
            pairs.append((info, base_radius))
    try:
        return cad_helpers.fillet_edges_variable(shape, pairs)
    except Exception:
        shape = _apply(
            shape, chord_infos, chord_radius, cad_helpers.fillet_edges,
            "column merge fillet", report,
        )
        return _apply(
            shape, base_infos, base_radius, cad_helpers.fillet_edges,
            "boss base fillet", report,
        )


def relieve_concave_joints(shape, orientation: PrintOrientation, size: float, report):
    """Relieve the inside joints of ``shape`` by ``size`` mm.

    Horizontal (and slanted) concave edges are chamfered, because a fillet
    there opens toward the bed and prints as a curved overhang. Vertical
    concave edges are filleted: the relief is hidden inside the assembly and a
    fillet along print Z prints cleanly. ``orientation`` is the part's print
    orientation. Edges that don't take the treatment are skipped with a SOFT
    warning on ``report``.
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


def boss_base_edges(
    shape: Any,
    columns: Any,
    plane_z: float,
    axis: float,
    orientation: PrintOrientation = BED_DOWN,
    tol: float = 0.06,
) -> list[cad_helpers.EdgeInfo]:
    """The concave ring where a boss springs from a floor, wall or ceiling.

    A boss meets the plane it grows from in a circular reentrant edge, and the
    rule is that every such base is filleted (ADR-0025). ``columns`` are the
    ``(x, y, r_min, r_max)`` quadruples used by :func:`column_junction_edges`,
    ``plane_z`` is the base plane, and ``axis`` is the sign along Z the boss
    grows from it (+1 upward, -1 downward).

    The round only prints when its cove opens away from the part's bed: a boss
    that grows toward the bed stands on its base, so the fillet opens up out of
    the print; one growing away from the bed would need support under the round
    and is left for the chamfer. ``orientation`` is the part's print
    orientation, never the assembly's Z.
    """
    if axis * orientation.normal[2] >= 0.0:
        return []
    found = []
    for edge in concave_edges(shape):
        info = edge.info
        if info.curve_type != "circle":
            continue
        x, y, z, _ = info.key
        if abs(z - plane_z) > tol:
            continue
        for cx, cy, thin, thick in columns:
            radius = math.hypot(x - cx, y - cy)
            if thin - tol <= radius <= thick + tol:
                found.append(info)
                break
    return found


def fillet_boss_bases(
    shape: Any,
    columns: Any,
    plane_z: float,
    axis: float,
    radius: float,
    report: Any,
    orientation: PrintOrientation = BED_DOWN,
) -> Any:
    """Fillet the concave ring under every boss base on a plane (ADR-0025).

    The fillet rolls the floor, wall or ceiling into the boss wall and removes
    the reentrant corner at the root -- the crack starter at the most loaded
    edge of a printed boss. :func:`boss_base_edges` picks the rings and applies
    the print-orientation test; edges that don't take the fillet are skipped
    with a SOFT warning, so a tight spot never blocks the build.
    """
    if radius <= 0.0:
        return shape
    infos = boss_base_edges(shape, columns, plane_z, axis, orientation)
    return _apply(shape, infos, radius, cad_helpers.fillet_edges, "boss base fillet", report)


def rect_junction_edges(
    shape: Any,
    rects: Any,
    faces_y: Any,
    orientation: PrintOrientation = BED_DOWN,
    tol: float = 0.06,
) -> list[cad_helpers.EdgeInfo]:
    """The vertical chords where a rectangular boss crosses a wall face.

    A boss bridged into its facing wall as a rectangle (ADR-0026) meets each
    wall in two vertical reentrant edges, at ``x = cx +/- half_width``. A rect
    is ``(cx, y_in, y_out, half_width)`` with signed ``y`` endpoints. The edge
    must run along print Z and its midpoint must sit on one of ``faces_y`` and
    on the rectangle's long side; ``orientation`` is the part's print
    orientation.
    """
    faces = (faces_y,) if isinstance(faces_y, (int, float)) else tuple(faces_y)
    found = []
    for edge in concave_edges(shape):
        if not edge.vertical(orientation):
            continue
        x, y, _ = edge.info.key[:3]
        if min(abs(abs(y) - face) for face in faces) > tol:
            continue
        for cx, y0, y1, half in rects:
            low, high = (y0, y1) if y0 <= y1 else (y1, y0)
            if abs(abs(x - cx) - half) <= tol and low - tol <= y <= high + tol:
                found.append(edge.info)
                break
    return found


def rect_base_edges(
    shape: Any,
    rects: Any,
    plane_z: float,
    axis: float,
    orientation: PrintOrientation = BED_DOWN,
    tol: float = 0.06,
) -> list[cad_helpers.EdgeInfo]:
    """The concave base edges under a rectangular boss on a plane.

    A rectangle bridged between two walls (ADR-0026) meets its base plane in
    two straight edges along Y, at ``x = cx +/- half_width``, between the ring's
    outer face and the facing wall. A rect is ``(cx, y_in, y_out, half_width)``.
    The round is gated by ``axis`` and ``orientation`` exactly as
    :func:`boss_base_edges` does.
    """
    if axis * orientation.normal[2] >= 0.0:
        return []
    found = []
    for edge in concave_edges(shape):
        info = edge.info
        if abs(info.key[2] - plane_z) > tol:
            continue
        x, y = info.key[0], info.key[1]
        for cx, y0, y1, half in rects:
            low, high = (y0, y1) if y0 <= y1 else (y1, y0)
            if abs(abs(x - cx) - half) <= tol and low - tol <= y <= high + tol:
                found.append(info)
                break
    return found
