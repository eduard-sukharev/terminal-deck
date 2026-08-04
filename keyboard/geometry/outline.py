"""Plate outline generation.

Computes the plate outline polygon from switch centers, a configurable
margin, and a corner radius.
"""

from __future__ import annotations

import math


def generate_outline(
    switch_centers: list[tuple[float, float]],
    margin: float = 6.0,
    corner_radius: float = 8.0,
    segments: int = 8,
) -> list[tuple[float, float]]:
    """Generate the plate outline polygon.

    Algorithm per ``docs/keyboard_architecture.md``:

        1. Collect switch centers.
        2. Compute occupied bounding box.
        3. Expand by *margin*.
        4. Round corners with *corner_radius*.

    Parameters
    ----------
    switch_centers : list[tuple[float, float]]
        (x, y) positions of every switch center in mm.
    margin : float
        Extra space beyond the outermost switch centers (mm).
    corner_radius : float
        Radius of rounded corners (mm).
    segments : int
        Number of segments per rounded corner (default 8).

    Returns
    -------
    list[tuple[float, float]]
        Closed polygon vertices of the plate outline.
    """
    if not switch_centers:
        return []

    xs = [p[0] for p in switch_centers]
    ys = [p[1] for p in switch_centers]
    x0, x1 = min(xs), max(xs)
    y0, y1 = min(ys), max(ys)

    left = x0 - margin
    right = x1 + margin
    bottom = y0 - margin
    top = y1 + margin

    return _rounded_rect(left, bottom, right, top, corner_radius, segments)


def _rounded_rect(
    left: float,
    bottom: float,
    right: float,
    top: float,
    radius: float,
    segments: int,
) -> list[tuple[float, float]]:
    """Rounded rectangle polygon, clockwise from bottom-left."""
    if radius <= 0:
        return [(left, bottom), (right, bottom), (right, top), (left, top)]

    verts: list[tuple[float, float]] = []
    corners = [
        (right - radius, bottom + radius, 0.0, 90.0),   # bottom-right
        (right - radius, top - radius, 90.0, 180.0),     # top-right
        (left + radius, top - radius, 180.0, 270.0),     # top-left
        (left + radius, bottom + radius, 270.0, 360.0),  # bottom-left
    ]
    for cx, cy, start_deg, end_deg in corners:
        for i in range(segments):
            angle = math.radians(start_deg + (end_deg - start_deg) * i / segments)
            verts.append((cx + radius * math.cos(angle), cy + radius * math.sin(angle)))
    return verts
