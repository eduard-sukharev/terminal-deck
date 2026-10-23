"""Nearest free spot for a boss, column or standoff (pure data, no CAD).

A full 2D search over expanding rings around a target, not a nudge along one
line: with a component (the keyboard) spanning almost the whole footprint, the
straight path from a nominal spot toward the case center is blocked along its
whole length, and only a 2D search finds the gaps off to the side.
"""

from __future__ import annotations

import math
from collections.abc import Callable

Bounds = tuple[float, float, float, float]  # x0, y0, x1, y1


def nearest_free_spot(
    target: tuple[float, float],
    conflicts: Callable[[float, float], bool],
    bounds: Bounds,
    step: float = 1.0,
) -> tuple[float, float] | None:
    """Nearest point to ``target`` that ``conflicts`` clears, within ``bounds``.

    Returns ``None`` if nothing within ``bounds`` is free. Candidates outside
    ``bounds`` are never returned, even the target itself.
    """
    tx, ty = target
    x0, y0, x1, y1 = bounds

    def ok(x: float, y: float) -> bool:
        return x0 <= x <= x1 and y0 <= y <= y1 and not conflicts(x, y)

    if ok(tx, ty):
        return (tx, ty)
    max_radius = max(math.hypot(cx - tx, cy - ty) for cx in (x0, x1) for cy in (y0, y1))
    r = step
    while r <= max_radius:
        n = max(12, int(2 * math.pi * r / step))
        for i in range(n):
            theta = 2 * math.pi * i / n
            x, y = tx + r * math.cos(theta), ty + r * math.sin(theta)
            if ok(x, y):
                return (x, y)
        r += step
    return None


def drop_close(
    spots: list[tuple[float, float]], min_separation: float
) -> list[tuple[float, float]]:
    """Keep spots in order, dropping any closer than ``min_separation`` to a kept one."""
    kept: list[tuple[float, float]] = []
    for spot in spots:
        if all(math.hypot(spot[0] - kx, spot[1] - ky) >= min_separation for kx, ky in kept):
            kept.append(spot)
    return kept
