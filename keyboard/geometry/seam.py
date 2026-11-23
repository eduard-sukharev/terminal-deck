"""Split line for a keyboard plate that must not cut through any cutout.

The plate is cut into left/right Halves along a path that, row by row, runs
through the gap between key columns nearest the plate center. A single
straight line cannot do that for a real layout (a spacebar stabilizer spans
the middle of its row), so the path jogs sideways in the clear band between
rows. Pure data: no CAD library needed.
"""

from __future__ import annotations

import math
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

    def x_at(self, y: float) -> float:
        """The seam's X at plate-local ``y`` (mm).

        Returns the ``x`` of the band containing ``y``. Bands are used as-is
        (not depth-stretched), matching the :class:`~utilities.config_loader.Seam`
        interface used by :func:`geometry.seam_joint.add_pins`. A ``y`` that falls
        between bands (on a jog) interpolates; a ``y`` outside every band clamps to
        the nearest edge band.
        """
        bands = self.bands
        if y <= bands[0][1]:
            return bands[0][2]
        for y0, y1, x in bands:
            if y0 <= y <= y1:
                return x
        for (_, ya, xa), (yb, _, xb) in zip(bands, bands[1:]):
            if ya <= y <= yb:
                return xa + (xb - xa) * (y - ya) / (yb - ya)
        return bands[-1][2]

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


def _seam_path(
    bands: list[tuple[float, float, float]],
    y_front: float,
    y_rear: float,
) -> list[tuple[float, float]]:
    """The Seam as a polyline from its front-edge crossing to its rear one."""
    points: list[tuple[float, float]] = [(bands[0][2], y_front)]
    for i, (_, y1, x) in enumerate(bands):
        last = i + 1 == len(bands)
        y = y_rear if last else min(y1, y_rear)
        points.append((x, y))
        if not last:
            points.append((bands[i + 1][2], y))
    return points


def _vertical_crossings(
    outline: list[tuple[float, float]], x: float
) -> list[tuple[float, float]]:
    """Where the vertical line at ``x`` crosses the outline ring.

    The Seam leaves the plate through its front and rear edges, so its two
    ends are the extreme crossings of that line: the lowest is the front one,
    the highest the rear one. A Seam that does not reach both edges (a closed
    loop inside the plate) is not a split and is rejected by the caller.
    """
    hits: list[tuple[float, float]] = []
    for index in range(len(outline)):
        p, q = outline[index], outline[(index + 1) % len(outline)]
        dx = q[0] - p[0]
        if abs(dx) < 1e-12:
            continue
        t = (x - p[0]) / dx
        if 0.0 <= t <= 1.0:
            hits.append((x, p[1] + t * (q[1] - p[1])))
    return hits


def _insert_points(
    outline: list[tuple[float, float]], points: list[tuple[float, float]]
) -> list[tuple[float, float]]:
    """Insert each point on the outline edge it lies on, in edge order."""
    out: list[tuple[float, float]] = []
    for index in range(len(outline)):
        p, q = outline[index], outline[(index + 1) % len(outline)]
        out.append(p)
        length = math.hypot(q[0] - p[0], q[1] - p[1])
        if length <= 1e-12:
            continue
        on_edge = []
        for point in points:
            t = ((point[0] - p[0]) * (q[0] - p[0]) + (point[1] - p[1]) * (q[1] - p[1])) / (
                length * length
            )
            cross = (q[0] - p[0]) * (point[1] - p[1]) - (q[1] - p[1]) * (point[0] - p[0])
            if abs(cross) <= 1e-7 and 1e-9 < t < 1.0 - 1e-9:
                on_edge.append((t, point))
        out.extend(point for _, point in sorted(on_edge, key=lambda item: item[0]))
    return out


def _index_of(point: tuple[float, float], ring: list[tuple[float, float]]) -> int:
    for index, vertex in enumerate(ring):
        if abs(vertex[0] - point[0]) <= 1e-9 and abs(vertex[1] - point[1]) <= 1e-9:
            return index
    raise ValueError(f"{point} is not on the plate outline")


def _chain(
    ring: list[tuple[float, float]], start: int, end: int
) -> list[tuple[float, float]]:
    out = [ring[start]]
    index = start
    while index != end:
        index = (index + 1) % len(ring)
        out.append(ring[index])
    return out


def section_outlines(
    outline: list[tuple[float, float]], seam: RowSeam, depth: float
) -> tuple[list[tuple[float, float]], list[tuple[float, float]]]:
    """Split a plate ``outline`` along ``seam`` into ``(left, right)`` polygons.

    ``depth`` is the part's extent in Y, the same value the CAD splitter takes.
    The outline may be any simple single ring -- tabs and notches included: the
    Seam leaves the plate through its front and rear edges, so the outline just
    contributes two chains between those two crossings and the Seam closes each
    Section. Pure data: the Section **solids** are cut by the CAD adapter.
    """
    outline = _ccw(list(outline))
    ys = [y for _, y in outline]
    ylo, yhi = min(ys), max(ys)
    bands = _seam_band(seam, min(ylo, -depth / 2.0), max(yhi, depth / 2.0))

    front_hits = _vertical_crossings(outline, bands[0][2])
    if not front_hits:
        raise ValueError(
            f"the Seam's front end x={bands[0][2]:.2f} does not cross the plate"
        )
    front = min(front_hits, key=lambda point: point[1])
    rear_hits = _vertical_crossings(outline, bands[-1][2])
    if not rear_hits:
        raise ValueError(
            f"the Seam's rear end x={bands[-1][2]:.2f} does not cross the plate"
        )
    rear = max(rear_hits, key=lambda point: point[1])
    if abs(front[1] - rear[1]) <= 1e-9:
        raise ValueError("the Seam does not run from the plate's front to rear")

    ring = _insert_points(outline, [front, rear])
    i_front = _index_of(front, ring)
    i_rear = _index_of(rear, ring)
    path = _seam_path(bands, front[1], rear[1])
    # Two chains between the crossings, closed by the Seam's staircase: one
    # Section walks the Seam forward, the other backward.
    first = _chain(ring, i_front, i_rear) + list(reversed(path[1:-1]))
    second = _chain(ring, i_rear, i_front) + path[1:-1]
    if _area(first) < 0.0:
        first = list(reversed(first))
    if _area(second) < 0.0:
        second = list(reversed(second))
    # The left Section is the one reaching the plate's left edge.
    if min(x for x, _ in first) <= min(x for x, _ in second):
        return first, second
    return second, first

