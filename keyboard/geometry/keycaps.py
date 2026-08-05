"""Keycap geometry — pure-math vertex samplers for lofting.

Provides rectangle and stadium (rounded-rectangle) boundary samplers with
matched vertex counts, plus a :func:`keycap_specs` function that computes
per-keycap dimensions from layout keys and a profile.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from keyboard.layout.key import Key


def rectangle_vertices(
    width: float, depth: float, n: int = 32
) -> list[tuple[float, float]]:
    """Sample a rectangle boundary at *n* uniform angles from centre.

    Vertices are ordered CCW starting from the +X axis, matching the angular
    order of :func:`stadium_vertices` so the two can be paired in a loft.
    """
    hw, hd = width / 2.0, depth / 2.0
    verts: list[tuple[float, float]] = []
    for i in range(n):
        theta = 2.0 * math.pi * i / n
        ct, st = math.cos(theta), math.sin(theta)
        if abs(ct) > 1e-12 and abs(st) > 1e-12:
            t = min(hw / abs(ct), hd / abs(st))
        elif abs(ct) > 1e-12:
            t = hw / abs(ct)
        else:
            t = hd / abs(st)
        verts.append((t * ct, t * st))
    return verts


def stadium_vertices(
    width: float, depth: float, corner_radius: float, n: int = 32
) -> list[tuple[float, float]]:
    """Sample a stadium (rounded-rectangle) boundary at *n* uniform angles.

    The stadium is centred at the origin with its long axis along X.
    When ``width == depth == 2 * corner_radius`` the result is a circle
    of radius ``corner_radius``, matching the 1u keycap case.

    Vertices are ordered CCW from the +X axis, one per angle, so they pair
    1:1 with :func:`rectangle_vertices` for lofting.
    """
    hw, hd = width / 2.0, depth / 2.0
    c = hw - corner_radius  # centre offset of the right semicircle

    # Circle degenerate case.
    if abs(c) < 1e-12 and abs(hd - corner_radius) < 1e-12:
        r = corner_radius
        return [(r * math.cos(2.0 * math.pi * i / n),
                 r * math.sin(2.0 * math.pi * i / n)) for i in range(n)]

    verts: list[tuple[float, float]] = []
    for i in range(n):
        theta = 2.0 * math.pi * i / n
        ct, st = math.cos(theta), math.sin(theta)

        candidates: list[tuple[float, float, float]] = []

        # Right semicircle: centre (c, 0), radius corner_radius.
        disc = corner_radius * corner_radius - c * c * st * st
        if disc >= 0:
            t = c * ct + math.sqrt(disc)
            if t > 0:
                x = t * ct
                if x >= c - 1e-9:
                    candidates.append((t, x, t * st))

        # Left semicircle: centre (-c, 0), radius corner_radius.
        if disc >= 0:
            t = -c * ct + math.sqrt(disc)
            if t > 0:
                x = t * ct
                if x <= -c + 1e-9:
                    candidates.append((t, x, t * st))

        # Top edge: y = hd.
        if st > 1e-12:
            t = hd / st
            x = t * ct
            if abs(x) <= c + 1e-9:
                candidates.append((t, x, hd))

        # Bottom edge: y = -hd.
        if st < -1e-12:
            t = -hd / st
            x = t * ct
            if abs(x) <= c + 1e-9:
                candidates.append((t, x, -hd))

        if candidates:
            _, x, y = min(candidates, key=lambda cand: cand[0])
            verts.append((x, y))
        else:
            verts.append((
                hw * (1.0 if ct >= 0 else -1.0),
                hd * (1.0 if st >= 0 else -1.0),
            ))

    return verts


def keycap_specs(
    keys: list[Key],
    profile: Any,
    pitch: float = 19.05,
    layout_centroid: tuple[float, float] = (0.0, 0.0),
) -> list[dict[str, float | int]]:
    """Compute per-keycap geometry specs from layout keys and a profile.

    Parameters
    ----------
    keys : list[Key]
        All keys in the layout.
    profile
        A ``KeycapProtocol`` instance providing ``base_size``, ``top_diameter``,
        ``height``, and ``segments``.
    pitch : float
        Switch pitch in mm (default 19.05).
    layout_centroid : tuple[float, float]
        Centroid of the layout in units (for centering).

    Returns
    -------
    list[dict]
        One dict per key with keys: ``x``, ``y``, ``rotation``, ``base_w``,
        ``base_d``, ``top_w``, ``top_d``, ``corner_radius``, ``height``,
        ``segments``.
    """
    cx, cy = layout_centroid
    base_size = profile.base_size()
    top_diameter = profile.top_diameter()
    cap_height = profile.height()
    segments = profile.segments()

    result: list[dict[str, float | int]] = []
    for key in keys:
        x = (key.x - cx) * pitch
        y = (key.y - cy) * pitch

        rot = key.rotation if key.rotation is not None else 0.0
        if key.height > key.width and rot == 0.0:
            rot = 90.0

        base_w = key.width * base_size
        base_d = key.height * base_size
        top_w = key.width * top_diameter
        top_d = key.height * top_diameter
        corner_radius = min(top_w, top_d) / 2.0

        result.append({
            "x": x,
            "y": y,
            "rotation": rot,
            "base_w": base_w,
            "base_d": base_d,
            "top_w": top_w,
            "top_d": top_d,
            "corner_radius": corner_radius,
            "height": cap_height,
            "segments": segments,
        })
    return result
