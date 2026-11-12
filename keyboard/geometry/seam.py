"""Split line for a keyboard plate that must not cut through any cutout.

The plate is cut into left/right Halves along a path that, row by row, runs
through the gap between key columns nearest the plate center. A single
straight line cannot do that for a real layout (a spacebar stabilizer spans
the middle of its row), so the path jogs sideways in the clear band between
rows. Pure data: no CAD library needed.
"""

from __future__ import annotations

from dataclasses import dataclass

from keyboard.metadata import Cutout, KeyboardGeometryModel

#: Cutouts whose centers differ in Y by less than this belong to one row (mm).
_ROW_TOLERANCE: float = 1.0


@dataclass(frozen=True)
class RowSeam:
    """A Seam made of ``(y0, y1, x)`` segments, front-to-back."""

    bands: tuple[tuple[float, float, float], ...]

    def segments(self, depth: float) -> list[tuple[float, float, float]]:
        """The segments, with the outer ends stretched to span ``depth``."""
        bands = [list(b) for b in self.bands]
        bands[0][0] = min(bands[0][0], -depth / 2.0)
        bands[-1][1] = max(bands[-1][1], depth / 2.0)
        return [tuple(b) for b in bands]

    def polyline(self, depth: float) -> list[tuple[float, float]]:
        """The Seam as a polyline ``(x, y)`` from the front edge to the back.

        Consecutive points form alternating vertical runs (along a band) and
        horizontal jogs (at the row gaps), so a reader can see the path the
        split follows.
        """
        segments = self.segments(depth)
        points = [(segments[0][2], segments[0][0])]
        for (_, y1, x), nxt in zip(segments, segments[1:] + [None]):
            points.append((x, y1))
            if nxt is not None:
                points.append((nxt[2], y1))
        return points

    @property
    def x_range(self) -> tuple[float, float]:
        xs = [x for _, _, x in self.bands]
        return (min(xs), max(xs))



def _x_span(cut: Cutout) -> tuple[float, float]:
    xs = [cut.x + v[0] for v in cut.vertices]
    return (min(xs), max(xs))


def _y_span(cut: Cutout) -> tuple[float, float]:
    ys = [cut.y + v[1] for v in cut.vertices]
    return (min(ys), max(ys))


def _cutouts(model: KeyboardGeometryModel) -> list[Cutout]:
    return list(model.switch_cutouts) + list(model.stabilizer_cutouts)


def _rows(model: KeyboardGeometryModel) -> list[list[Cutout]]:
    rows: list[list[Cutout]] = []
    for cut in sorted(_cutouts(model), key=lambda c: c.y):
        if rows and abs(rows[-1][0].y - cut.y) < _ROW_TOLERANCE:
            rows[-1].append(cut)
        else:
            rows.append([cut])
    return rows


def _row_gap_nearest_center(row: list[Cutout]) -> float:
    """X of the middle of the gap between this row's cutouts nearest x=0."""
    merged: list[list[float]] = []
    for lo, hi in sorted(_x_span(c) for c in row):
        if merged and lo <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], hi)
        else:
            merged.append([lo, hi])
    mids = [(a[1] + b[0]) / 2.0 for a, b in zip(merged, merged[1:])]
    if not mids:
        raise ValueError("row has no gap between key columns to split at")
    return min(mids, key=abs)


def plate_seam(model: KeyboardGeometryModel) -> RowSeam:
    """Seam through the key-column gap nearest the center of every row."""
    rows = _rows(model)
    extents = [
        (min(_y_span(c)[0] for c in row), max(_y_span(c)[1] for c in row))
        for row in rows
    ]
    half = model.metadata.height / 2.0
    edges = [-half] + [
        (a[1] + b[0]) / 2.0 for a, b in zip(extents, extents[1:])
    ] + [half]
    return RowSeam(tuple(
        (edges[i], edges[i + 1], _row_gap_nearest_center(row))
        for i, row in enumerate(rows)
    ))


def seam_conflicts(model: KeyboardGeometryModel, seam: RowSeam) -> list[str]:
    """Describe every cutout the Seam (segments or jogs) would cut through."""
    problems = []
    segs = seam.segments(model.metadata.height)
    for cut in _cutouts(model):
        x0, x1 = _x_span(cut)
        y0, y1 = _y_span(cut)
        for sy0, sy1, sx in segs:
            if sy0 < y1 and y0 < sy1 and x0 < sx < x1:
                problems.append(f"Seam x={sx:.1f} cuts cutout at ({cut.x:.1f}, {cut.y:.1f})")
        for (_, by, ax), (_, _, bx) in zip(segs, segs[1:]):
            if y0 < by < y1 and x0 < max(ax, bx) and min(ax, bx) < x1:
                problems.append(f"Seam jog at y={by:.1f} cuts cutout at ({cut.x:.1f}, {cut.y:.1f})")
    return problems


# -- Section outlines (pure data; the CAD split lives in the adapter) ------


def _area(poly: list[tuple[float, float]]) -> float:
    """Signed shoelace area (mm^2); positive for a counter-clockwise polygon."""
    return sum(
        a[0] * b[1] - b[0] * a[1] for a, b in zip(poly, poly[1:] + poly[:1])
    ) / 2.0


def _ccw(poly: list[tuple[float, float]]) -> list[tuple[float, float]]:
    return poly if _area(poly) >= 0.0 else list(reversed(poly))


def _seam_band(seam: RowSeam, ylo: float, yhi: float) -> list[tuple[float, float, float]]:
    """The Seam's band x per ``(y0, y1)``, with the ends stretched past the part."""
    bands = [list(b) for b in seam.bands]
    bands[0][0] = min(bands[0][0], ylo)
    bands[-1][1] = max(bands[-1][1], yhi)
    return [tuple(b) for b in bands]


def _staircase(
    bands: list[tuple[float, float, float]], ylo: float, yhi: float, far: float
) -> list[tuple[float, float]]:
    """The region on one side of the Seam, closed through a far edge at ``far``.

    The polygon runs bottom to top along the Seam's staircase, then closes
    through the far edge (negative ``far`` is the left Section).
    """
    points: list[tuple[float, float]] = [(far, ylo), (bands[0][2], ylo)]
    for i, (_, y1, x) in enumerate(bands):
        points.append((x, y1))
        if i + 1 < len(bands):
            points.append((bands[i + 1][2], y1))
    points.append((far, yhi))
    return _ccw(points)


def _clip_intersection(
    s: tuple[float, float], e: tuple[float, float],
    a: tuple[float, float], b: tuple[float, float],
) -> tuple[float, float]:
    """Where segment ``s-e`` crosses the infinite line ``a-b``."""
    sx, sy = s
    ex, ey = e
    dx, dy = ex - sx, ey - sy
    ax, ay = a
    bx, by = b
    cx, cy = bx - ax, by - ay
    denom = dx * cy - dy * cx
    if abs(denom) < 1e-15:
        return e
    t = ((ax - sx) * cy - (ay - sy) * cx) / denom
    return (sx + t * dx, sy + t * dy)


def _clip_by_convex(
    subject: list[tuple[float, float]],
    clipper: list[tuple[float, float]],
    eps: float = 1e-9,
) -> list[tuple[float, float]]:
    """Sutherland–Hodgman: the part of ``subject`` inside a convex ``clipper``."""
    clipper = _ccw(clipper)
    out = list(subject)
    for i, a in enumerate(clipper):
        b = clipper[(i + 1) % len(clipper)]
        if not out:
            return []
        inp, out = out, []
        s = inp[-1]
        for e in inp:
            side_e = (b[0] - a[0]) * (e[1] - a[1]) - (b[1] - a[1]) * (e[0] - a[0])
            side_s = (b[0] - a[0]) * (s[1] - a[1]) - (b[1] - a[1]) * (s[0] - a[0])
            if side_e >= -eps:
                if side_s < -eps:
                    out.append(_clip_intersection(s, e, a, b))
                out.append(e)
            elif side_s >= -eps:
                out.append(_clip_intersection(s, e, a, b))
            s = e
    # Drop repeated vertices (a clipped edge can leave collinear duplicates).
    clean: list[tuple[float, float]] = []
    for point in out:
        if not clean or abs(point[0] - clean[-1][0]) > eps or abs(
            point[1] - clean[-1][1]
        ) > eps:
            clean.append(point)
    if len(clean) > 1 and abs(clean[0][0] - clean[-1][0]) <= eps and abs(
        clean[0][1] - clean[-1][1]
    ) <= eps:
        clean.pop()
    return clean


def section_outlines(
    outline: list[tuple[float, float]], seam: RowSeam, depth: float
) -> tuple[list[tuple[float, float]], list[tuple[float, float]]]:
    """Split a plate ``outline`` along ``seam`` into ``(left, right)`` polygons.

    ``depth`` is the part's extent in Y (centered on the origin), the same
    value the CAD splitter takes. The outline must be convex — the keyboard
    plate is a rounded rectangle — so it can clip the Seam's staircase. Pure
    data: the Section **solids** are cut by the CAD adapter.
    """
    xs = [x for x, _ in outline]
    ys = [y for _, y in outline]
    ylo, yhi = min(ys), max(ys)
    bands = _seam_band(seam, min(ylo, -depth / 2.0), max(yhi, depth / 2.0))
    far = max(abs(min(xs)), abs(max(xs))) + 1.0
    return (
        _clip_by_convex(_staircase(bands, ylo, yhi, -far), outline),
        _clip_by_convex(_staircase(bands, ylo, yhi, +far), outline),
    )

