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


def chamfered_rect_vertices(
    width: float, depth: float, chamfer: float
) -> list[tuple[float, float]]:
    """Return the 8 vertices of a rectangle with its four corners cut off.

    The low-poly stand-in for :func:`stadium_vertices` /
    :func:`rectangle_vertices`: a keycap lofted between two of these has
    10 faces instead of ~34. ``chamfer`` is the leg length of each corner
    cut (mm), clamped just under half the shorter side so no vertices
    collapse together. Vertices run counter-clockwise starting on the +X edge,
    so two outlines of different size pair 1:1 for a ruled loft.
    """
    hw, hd = width / 2.0, depth / 2.0
    k = min(chamfer, 0.99 * min(hw, hd))
    return [
        (hw, -(hd - k)), (hw, hd - k),
        (hw - k, hd), (-(hw - k), hd),
        (-hw, hd - k), (-hw, -(hd - k)),
        (-(hw - k), -hd), (hw - k, -hd),
    ]


def keycap_footprint(
    switch_centers: list[tuple[float, float]],
    specs: list[dict[str, float | int]],
) -> tuple[float, float, float, float]:
    """Union of the keycaps' base rectangles: ``(x0, y0, x1, y1)`` in mm.

    Each cap's base rectangle is rotated about its own switch centre, exactly
    as :func:`keyboard.geometry.keycaps.keycap_specs` and the keycap loft
    place it. This is the *real* cap footprint — the Well Cutout is sized from
    it (ADR-0014), not from the switch centres: a cap reaches half a base
    beyond its switch, and a rotated cap's corners reach further still, which
    is what a rocking keycap would strike.
    """
    if len(specs) != len(switch_centers):
        raise ValueError(
            f"{len(specs)} keycap specs for {len(switch_centers)} switch centers"
        )
    xs: list[float] = []
    ys: list[float] = []
    for (cx, cy), spec in zip(switch_centers, specs):
        half_w = float(spec["base_w"]) / 2.0
        half_d = float(spec["base_d"]) / 2.0
        rad = math.radians(float(spec["rotation"]))
        cos_r, sin_r = math.cos(rad), math.sin(rad)
        for dx, dy in (
            (half_w, half_d),
            (-half_w, half_d),
            (-half_w, -half_d),
            (half_w, -half_d),
        ):
            xs.append(cx + dx * cos_r - dy * sin_r)
            ys.append(cy + dx * sin_r + dy * cos_r)
    return (min(xs), min(ys), max(xs), max(ys))


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
        ``segments``, ``base_chamfer``, ``top_chamfer``.
    """
    cx, cy = layout_centroid
    base_size = profile.base_size()
    top_diameter = profile.top_diameter()
    cap_height = profile.height()
    segments = profile.segments()
    base_chamfer = profile.base_chamfer()

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
        # Chamfer tangent to the round top: a circle of radius r inside its
        # bounding square is touched by the chamfer line x + y = r*sqrt(2),
        # which cuts each corner by a leg of r * (2 - sqrt(2)).
        top_chamfer = corner_radius * (2.0 - math.sqrt(2.0))

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
            "base_chamfer": base_chamfer,
            "top_chamfer": top_chamfer,
        })
    return result
