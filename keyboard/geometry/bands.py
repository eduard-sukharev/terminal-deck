"""Per-row keycap bands — the single source for a stepped plate and Well.

A keyboard layout's rows need not share an X extent: a 40% board with a narrow
spacebar row (``saber``) is a staircase, not a rectangle. This module turns the
real keycap footprints into contiguous **row bands** ``(y0, y1, x0, x1)`` in
plate-local mm, one per row, whose Y edges sit at the midpoints between adjacent
row extents. The plate and the Well's Cutout are then both grown from these
bands, so ``plate = cutout + wall`` holds band by band and the two can never
drift apart (ADR-0014).

Because row extents can differ by less than a printable feature (``jd40``'s rows
differ by <= 0.21 mm from their slightly different end keycaps), the bands are
**quantized** per side: a sub-``minimum_feature`` difference is not a real step,
so it is merged into the outer extent. A layout whose rows differ by a real
amount (``saber``: 4.8-9.5 mm) keeps its staircase.

Pure data: no CAD library, no enclosure imports.
"""

from __future__ import annotations

import math
from collections.abc import Sequence

#: A row band ``(y0, y1, x0, x1)`` in plate-local mm.
Band = tuple[float, float, float, float]

#: Keycap centres whose Y differ by less than this belong to one row (mm).
_ROW_TOLERANCE: float = 1.0

#: Differences below this are treated as the same edge (mm).
_EPS: float = 1e-9


def _cap_extents(spec: dict) -> tuple[float, float, float, float]:
    """The ``(x0, y0, x1, y1)`` of one keycap's base rectangle (rotated)."""
    half_w = float(spec["base_w"]) / 2.0
    half_d = float(spec["base_d"]) / 2.0
    rad = float(spec.get("rotation", 0.0)) * 3.141592653589793 / 180.0
    cos_r, sin_r = math.cos(rad), math.sin(rad)
    cx, cy = float(spec["x"]), float(spec["y"])
    xs: list[float] = []
    ys: list[float] = []
    for dx, dy in (
        (half_w, half_d),
        (-half_w, half_d),
        (-half_w, -half_d),
        (half_w, -half_d),
    ):
        xs.append(cx + dx * cos_r - dy * sin_r)
        ys.append(cy + dx * sin_r + dy * cos_r)
    return (min(xs), min(ys), max(xs), max(ys))


def keycap_bands(specs: Sequence[dict]) -> list[Band]:
    """One contiguous band per keycap row, front (low Y) to back.

    Rows are grouped by the keycap centres' Y (``_ROW_TOLERANCE``); their X
    extents come from the real rotated base rectangles, so a wide or rotated
    key widens its row exactly as it widens the Cutout. Inner Y edges are the
    midpoints between neighbouring row extents, which keeps the bands
    contiguous (one connected Cutout) even though rows are separated by a
    sub-millimetre gap.
    """
    if not specs:
        return []
    rows: list[tuple[float, list[dict]]] = []
    for spec in sorted(specs, key=lambda s: float(s["y"])):
        y = float(spec["y"])
        if rows and abs(rows[-1][0] - y) < _ROW_TOLERANCE:
            rows[-1][1].append(spec)
        else:
            rows.append((y, [spec]))

    extents = []
    for _, row_specs in rows:
        caps = [_cap_extents(spec) for spec in row_specs]
        extents.append(
            (
                min(c[0] for c in caps),
                min(c[1] for c in caps),
                max(c[2] for c in caps),
                max(c[3] for c in caps),
            )
        )

    bounds = [extents[0][1]]
    for lower, upper in zip(extents, extents[1:]):
        bounds.append((lower[3] + upper[1]) / 2.0)
    bounds.append(extents[-1][3])
    return [
        (bounds[i], bounds[i + 1], extents[i][0], extents[i][2])
        for i in range(len(extents))
    ]


def _group_side(values: list[float], outer: str, threshold: float) -> list[float]:
    """Merge adjacent values that differ from their group by < ``threshold``.

    ``outer`` is ``"min"`` for a left edge (the widest extent is the most
    negative) or ``"max"`` for a right edge. The merged group takes the outer
    value, so a sub-printable step is widened away rather than emitted.
    """
    result = list(values)
    index = 0
    while index < len(values):
        end = index
        outer_value = values[index]
        while end + 1 < len(values) and abs(values[end + 1] - outer_value) < threshold:
            end += 1
            outer_value = (
                min(outer_value, values[end])
                if outer == "min"
                else max(outer_value, values[end])
            )
        for k in range(index, end + 1):
            result[k] = outer_value
        index = end + 1
    return result


def quantize_bands(bands: Sequence[Band], threshold: float) -> list[Band]:
    """Merge sub-``threshold`` X steps per side and collapse equal neighbours.

    A step narrower than ``threshold`` is not printable, so it is folded into
    the outer extent (``min`` on the left, ``max`` on the right) instead of
    becoming a 0.1 mm staircase. Adjacent bands that end up identical are
    merged, so a rectangular layout (``jd40``/``planck``) collapses to a single
    band -- exactly today's rounded rectangle.
    """
    if threshold <= 0.0 or not bands:
        return list(bands)
    left = _group_side([b[2] for b in bands], "min", threshold)
    right = _group_side([b[3] for b in bands], "max", threshold)
    merged: list[Band] = []
    for (y0, y1, _, _), x0, x1 in zip(bands, left, right):
        if merged and abs(merged[-1][2] - x0) < _EPS and abs(merged[-1][3] - x1) < _EPS:
            py0, _, px0, px1 = merged[-1]
            merged[-1] = (py0, y1, px0, px1)
        else:
            merged.append((y0, y1, x0, x1))
    return merged


def grow_bands(bands: Sequence[Band], side: float, end: float) -> list[Band]:
    """Grow every band by ``side`` in X and the end bands by ``end`` in Y.

    Inner Y edges are shared, so ``grow_bands(cutout, wall, wall)`` gives the
    plate and ``plate = cutout + wall`` per band. The outer Y edges get the
    ``end`` allowance; the staircase's inner edges do not.
    """
    result: list[Band] = []
    last = len(bands) - 1
    for i, (y0, y1, x0, x1) in enumerate(bands):
        ny0 = y0 - end if i == 0 else y0
        ny1 = y1 + end if i == last else y1
        result.append((ny0, ny1, x0 - side, x1 + side))
    return result


__all__ = ["Band", "grow_bands", "keycap_bands", "quantize_bands"]
