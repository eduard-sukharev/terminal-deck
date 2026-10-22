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
