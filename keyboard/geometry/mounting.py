"""Mounting hole generation.

Computes mounting hole positions from the keyboard layout. Holes are placed
between rows, aligned with the first/second and last/second-to-last switches,
preferring empty space near wide keys (>1u).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from keyboard.metadata import MountingHole

if TYPE_CHECKING:
    from keyboard.layout.key import Key
    from keyboard.metadata import Cutout


def generate_mounting_holes(
    outline: list[tuple[float, float]],
    edge_offset: float = 5.0,
    screw_diameter: float = 2.0,
    switch_cutouts: list[Cutout] | None = None,
    stabilizer_cutouts: list[Cutout] | None = None,
    keys: list[Key] | None = None,
    pitch: float = 19.05,
    centroid: tuple[float, float] | None = None,
) -> list[MountingHole]:
    """Generate mounting holes between rows, aligned with edge switches.

    Two holes on the left side (between row 0-1 and row 2-3) and two on the
    right side, placed near wide keys where there's empty space.

    Parameters
    ----------
    outline : list[tuple[float, float]]
        Plate outline polygon vertices.
    edge_offset : float
        Not used in row-based placement (kept for API compat).
    screw_diameter : float
        Screw hole diameter (mm).
    switch_cutouts : list[Cutout] | None
        Switch cutouts (used for overlap avoidance).
    stabilizer_cutouts : list[Cutout] | None
        Stabilizer cutouts (used for overlap avoidance).
    keys : list[Key] | None
        Layout keys with width/height in units (needed for row detection).
    pitch : float
        Switch pitch in mm.
    centroid : tuple[float, float] | None
        Layout centroid in units.

    Returns
    -------
    list[MountingHole]
        Four mounting hole positions.
    """
    if not outline or not keys or centroid is None:
        return _fallback_corners(outline, edge_offset, screw_diameter)

    cx, cy = centroid

    # Group keys by row (same Y within tolerance).
    rows: dict[float, list[Key]] = {}
    for k in keys:
        ry = round(k.y, 2)
        if ry not in rows:
            rows[ry] = []
        rows[ry].append(k)

    sorted_rows = sorted(rows.items(), key=lambda item: item[0])
    if len(sorted_rows) < 4:
        return _fallback_corners(outline, edge_offset, screw_diameter)

    # Row Y positions in mm (centroid-adjusted).
    row_ys = [ry * pitch - cy * pitch for ry, _ in sorted_rows]

    # Y positions: between row 0-1 and between row 2-3.
    y_lower = (row_ys[0] + row_ys[1]) / 2.0
    y_upper = (row_ys[2] + row_ys[3]) / 2.0

    # Find X positions from the first two and last two keys in each row.
    def _key_x_mm(k: Key) -> float:
        return (k.x - cx) * pitch

    def _key_right_mm(k: Key) -> float:
        return (k.x + k.width / 2.0 - cx) * pitch

    def _key_left_mm(k: Key) -> float:
        return (k.x - k.width / 2.0 - cx) * pitch

    # Collect candidate X positions from the first two keys in row 0 and row 1.
    left_candidates: list[tuple[float, float, float]] = []  # (x, weight, key_width)
    for ry, row_keys in sorted_rows[:2]:
        sorted_row = sorted(row_keys, key=lambda k: k.x)
        if len(sorted_row) >= 2:
            k1, k2 = sorted_row[0], sorted_row[1]
            gap_start = _key_right_mm(k1)
            gap_end = _key_left_mm(k2)
            mid = (gap_start + gap_end) / 2.0
            # Prefer wider gaps and proximity to wide keys.
            gap_width = gap_end - gap_start
            max_w = max(k1.width, k2.width)
            weight = gap_width + (max_w - 1.0) * 5.0  # bonus for wide keys
            left_candidates.append((mid, weight, max_w))

    # Collect candidate X positions from the last two keys in row 0 and row 1.
    right_candidates: list[tuple[float, float, float]] = []
    for ry, row_keys in sorted_rows[:2]:
        sorted_row = sorted(row_keys, key=lambda k: k.x)
        if len(sorted_row) >= 2:
            k1, k2 = sorted_row[-2], sorted_row[-1]
            gap_start = _key_right_mm(k1)
            gap_end = _key_left_mm(k2)
            mid = (gap_start + gap_end) / 2.0
            gap_width = gap_end - gap_start
            max_w = max(k1.width, k2.width)
            weight = gap_width + (max_w - 1.0) * 5.0
            right_candidates.append((mid, weight, max_w))

    # Same for upper rows (row 2 and row 3).
    for ry, row_keys in sorted_rows[2:4]:
        sorted_row = sorted(row_keys, key=lambda k: k.x)
        if len(sorted_row) >= 2:
            k1, k2 = sorted_row[0], sorted_row[1]
            gap_start = _key_right_mm(k1)
            gap_end = _key_left_mm(k2)
            mid = (gap_start + gap_end) / 2.0
            gap_width = gap_end - gap_start
            max_w = max(k1.width, k2.width)
            weight = gap_width + (max_w - 1.0) * 5.0
            left_candidates.append((mid, weight, max_w))

    for ry, row_keys in sorted_rows[2:4]:
        sorted_row = sorted(row_keys, key=lambda k: k.x)
        if len(sorted_row) >= 2:
            k1, k2 = sorted_row[-2], sorted_row[-1]
            gap_start = _key_right_mm(k1)
            gap_end = _key_left_mm(k2)
            mid = (gap_start + gap_end) / 2.0
            gap_width = gap_end - gap_start
            max_w = max(k1.width, k2.width)
            weight = gap_width + (max_w - 1.0) * 5.0
            right_candidates.append((mid, weight, max_w))

    # Pick the best candidate for each position (highest weight).
    left_lower_x = max(left_candidates[:2], key=lambda c: c[1])[0] if len(left_candidates) >= 2 else left_candidates[0][0]
    left_upper_x = max(left_candidates[2:4], key=lambda c: c[1])[0] if len(left_candidates) >= 4 else left_candidates[-1][0]
    right_lower_x = max(right_candidates[:2], key=lambda c: c[1])[0] if len(right_candidates) >= 2 else right_candidates[0][0]
    right_upper_x = max(right_candidates[2:4], key=lambda c: c[1])[0] if len(right_candidates) >= 4 else right_candidates[-1][0]

    candidates = [
        MountingHole(left_lower_x, y_lower, screw_diameter),
        MountingHole(right_lower_x, y_lower, screw_diameter),
        MountingHole(left_upper_x, y_upper, screw_diameter),
        MountingHole(right_upper_x, y_upper, screw_diameter),
    ]

    # Avoid overlapping with cutouts.
    all_cutouts = (switch_cutouts or []) + (stabilizer_cutouts or [])
    if not all_cutouts:
        return candidates

    xs = [p[0] for p in outline]
    ys = [p[1] for p in outline]
    x0, x1 = min(xs), max(xs)
    y0, y1 = min(ys), max(ys)

    result: list[MountingHole] = []
    for hole in candidates:
        safe = _safe_hole_position(hole.x, hole.y, all_cutouts, x0, x1, y0, y1)
        result.append(MountingHole(safe[0], safe[1], hole.diameter))
    return result


def _fallback_corners(
    outline: list[tuple[float, float]],
    edge_offset: float,
    screw_diameter: float,
) -> list[MountingHole]:
    """Fallback: place holes at the four corners of the bounding box."""
    if not outline:
        return []
    xs = [p[0] for p in outline]
    ys = [p[1] for p in outline]
    x0, x1 = min(xs), max(xs)
    y0, y1 = min(ys), max(ys)
    return [
        MountingHole(x0 + edge_offset, y0 + edge_offset, screw_diameter),
        MountingHole(x1 - edge_offset, y0 + edge_offset, screw_diameter),
        MountingHole(x1 - edge_offset, y1 - edge_offset, screw_diameter),
        MountingHole(x0 + edge_offset, y1 - edge_offset, screw_diameter),
    ]


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

    Tries X-axis shift first, then Y-axis shift. Re-checks all cutouts
    after each shift to catch secondary overlaps.
    """
    clearance = 1.0
    mid_x = (x0 + x1) / 2.0
    mid_y = (y0 + y1) / 2.0

    for _ in range(3):
        overlapped = False
        for cut in cutouts:
            rx, ry = x - cut.x, y - cut.y
            if not _point_in_polygon(rx, ry, cut.vertices):
                continue

            overlapped = True
            cut_lx = min(v[0] for v in cut.vertices) + cut.x
            cut_rx = max(v[0] for v in cut.vertices) + cut.x
            cut_ly = min(v[1] for v in cut.vertices) + cut.y
            cut_ry = max(v[1] for v in cut.vertices) + cut.y

            if x < mid_x:
                x = cut_rx + clearance
            else:
                x = cut_lx - clearance
            x = max(x0 + clearance, min(x, x1 - clearance))

            rx, ry = x - cut.x, y - cut.y
            if _point_in_polygon(rx, ry, cut.vertices):
                x = cut_rx + clearance if x < mid_x else cut_lx - clearance
                x = max(x0 + clearance, min(x, x1 - clearance))

                if y < mid_y:
                    y = cut_ry + clearance
                else:
                    y = cut_ly - clearance
                y = max(y0 + clearance, min(y, y1 - clearance))

        if not overlapped:
            break

    return (x, y)


__all__ = ["generate_mounting_holes"]
