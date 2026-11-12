"""Plate outline generation.

Computes the plate outline polygon from switch centers, per-side margins, and a
corner radius.
"""

from __future__ import annotations

import math

#: A margin per side, ``(left, right, bottom, top)`` = ``(-X, +X, -Y, +Y)`` of
#: the switch-center bounding box, or one uniform ``float`` for every side.
Margins = float | tuple[float, float, float, float]


def generate_outline(
    switch_centers: list[tuple[float, float]],
    margin: Margins = 6.0,
    corner_radius: float = 8.0,
    segments: int = 8,
) -> list[tuple[float, float]]:
    """Generate the plate outline polygon.

    Algorithm per ``docs/keyboard_architecture.md``, with the margins derived
    from the Well Cutout (ADR-0014):

        1. Collect switch centers.
        2. Compute occupied bounding box.
        3. Expand by *margin* on each side.
        4. Round corners with *corner_radius*.

    The margins are **per side** because the plate is the Well Cutout grown by
    one wall on every side, and the keycap footprint (hence the Cutout) need
    not be centred on the switch-center bounding box: a wide key on one end
    alone makes the plate's border asymmetric.

    Parameters
    ----------
    switch_centers : list[tuple[float, float]]
        (x, y) positions of every switch center in mm.
    margin : Margins
        Extra space beyond the outermost switch centers (mm): one uniform
        value, or ``(left, right, bottom, top)``.
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

    if isinstance(margin, tuple):
        left_m, right_m, bottom_m, top_m = margin
    else:
        left_m = right_m = bottom_m = top_m = margin

    left = x0 - left_m
    right = x1 + right_m
    bottom = y0 - bottom_m
    top = y1 + top_m

    return _rounded_rect(left, bottom, right, top, corner_radius, segments)


def _rounded_rect(
    left: float,
    bottom: float,
    right: float,
    top: float,
    radius: float,
    segments: int,
) -> list[tuple[float, float]]:
    """Rounded rectangle polygon, counter-clockwise from the bottom edge.

    Each corner arc is centred at the inset point and swept across the
    quadrant that *replaces* the sharp corner: the bottom-right arc runs from
    the bottom edge (270°) to the right edge (0°), the top-right arc from the
    right edge (0°) to the top edge (90°), and so on. Sweeping any other
    quadrant would bulge the corner outward past the plate edges.
    """
    if radius <= 0:
        return [(left, bottom), (right, bottom), (right, top), (left, top)]

    verts: list[tuple[float, float]] = []
    corners = [
        (right - radius, bottom + radius, 270.0, 360.0),  # bottom-right
        (right - radius, top - radius, 0.0, 90.0),        # top-right
        (left + radius, top - radius, 90.0, 180.0),       # top-left
        (left + radius, bottom + radius, 180.0, 270.0),   # bottom-left
    ]
    for cx, cy, start_deg, end_deg in corners:
        for i in range(segments):
            angle = math.radians(start_deg + (end_deg - start_deg) * i / segments)
            verts.append((cx + radius * math.cos(angle), cy + radius * math.sin(angle)))
    return verts
