"""Mounting hole generation.

Computes mounting hole positions from the plate outline and configuration.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from keyboard.metadata import MountingHole

if TYPE_CHECKING:
    from keyboard.metadata import Cutout


def generate_mounting_holes(
    outline: list[tuple[float, float]],
    edge_offset: float = 5.0,
    screw_diameter: float = 2.0,
    switch_cutouts: list[Cutout] | None = None,
    stabilizer_cutouts: list[Cutout] | None = None,
) -> list[MountingHole]:
    """Generate mounting holes near the plate corners.

    Each hole is checked against switch and stabilizer cutouts and shifted
    to the nearest safe position if it would overlap.

    Parameters
    ----------
    outline : list[tuple[float, float]]
        Plate outline polygon vertices.
    edge_offset : float
        Distance from the plate edge to hole center (mm).
    screw_diameter : float
        Screw hole diameter (mm).
    switch_cutouts : list[Cutout] | None
        Switch cutouts to avoid overlapping.
    stabilizer_cutouts : list[Cutout] | None
        Stabilizer cutouts to avoid overlapping.

    Returns
    -------
    list[MountingHole]
        Mounting hole positions.
    """
    if not outline:
        return []

    xs = [p[0] for p in outline]
    ys = [p[1] for p in outline]
    x0, x1 = min(xs), max(xs)
    y0, y1 = min(ys), max(ys)

    candidates = [
        MountingHole(x0 + edge_offset, y0 + edge_offset, screw_diameter),
        MountingHole(x1 - edge_offset, y0 + edge_offset, screw_diameter),
        MountingHole(x1 - edge_offset, y1 - edge_offset, screw_diameter),
        MountingHole(x0 + edge_offset, y1 - edge_offset, screw_diameter),
    ]

    all_cutouts = (switch_cutouts or []) + (stabilizer_cutouts or [])
    if not all_cutouts:
        return candidates

    result: list[MountingHole] = []
    for hole in candidates:
        safe = _safe_hole_position(hole.x, hole.y, all_cutouts, x0, x1, y0, y1)
        result.append(MountingHole(safe[0], safe[1], hole.diameter))
    return result


def _point_in_polygon(
    px: float, py: float, verts: list[tuple[float, float]]
) -> bool:
    """Ray-casting point-in-polygon test."""
    inside = False
    n = len(verts)
    j = n - 1
    for i in range(n):
        xi, yi = verts[i]
        xj, yj = verts[j]
        if ((yi > py) != (yj > py)) and (
            px < (xj - xi) * (py - yi) / (yj - yi) + xi
        ):
            inside = not inside
        j = i
    return inside


def _safe_hole_position(
    x: float,
    y: float,
    cutouts: list[Cutout],
    x0: float,
    x1: float,
    y0: float,
    y1: float,
) -> tuple[float, float]:
    """Shift a mounting hole to avoid overlapping any cutout.

    Tries X-axis shift first (toward plate center), then Y-axis shift.
    """
    clearance = 1.0

    for cut in cutouts:
        rx, ry = x - cut.x, y - cut.y
        if not _point_in_polygon(rx, ry, cut.vertices):
            continue

        cut_lx = min(v[0] for v in cut.vertices) + cut.x
        cut_rx = max(v[0] for v in cut.vertices) + cut.x
        cut_ly = min(v[1] for v in cut.vertices) + cut.y
        cut_ry = max(v[1] for v in cut.vertices) + cut.y

        mid_x = (x0 + x1) / 2.0

        if x < mid_x:
            x = cut_rx + clearance
        else:
            x = cut_lx - clearance

        x = max(x0 + clearance, min(x, x1 - clearance))

    return (x, y)
