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

OCC cannot always apply a chamfer (tight spots, thin neighbours). The edges
are tried together and, on failure, split in halves until the failing edge is
isolated; that edge is skipped and recorded as a SOFT warning, so a tight spot
never blocks the build. All CAD calls go through :mod:`utilities.cad_helpers`.
"""

from __future__ import annotations

from dataclasses import dataclass

from geometry.printability import PrintOrientation
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
    """XY of both corners of every step of ``seams`` (anything with
    ``segments(depth) -> [(y0, y1, x)]``)."""
    points = []
    for seam in seams:
        segments = seam.segments(depth)
        for (_, y, xa), (_, _, xb) in zip(segments, segments[1:]):
            if abs(xa - xb) > 1e-9:
                points += [(xa, y), (xb, y)]
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
