"""Seam-adjacent mounting holes (ADR 0003).

A plate split into two Sections is a pair of thin strips butt-jointed at the
Seam, with nothing under the joint: it sags and cracks along it. Each Section
therefore gets two extra mounting holes within one key unit of the Seam, one in
the upper rows and one in the lower rows, so the Seam is clamped from both
sides along its length. The holes sit in the gaps between key rows, clear of
every switch and stabilizer cutout; the cyberdeck turns them into standoffs on
the Tray floor.

Pure data (no CAD, no cyberdeck imports), like the rest of the keyboard
package. ``blocked`` lets a caller veto spots (the parts buried under the
plate); a Section/group with no free spot simply gets no hole, and the caller's
own check fails on the shortfall.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass

from keyboard.geometry.seam import RowSeam, _rows, _x_span, _y_span
from keyboard.metadata import Cutout, MountingHole

#: Air between a hole's edge and any cutout's bounding box (mm).
CUTOUT_MARGIN = 0.8
#: Search step along X from the Seam (mm).
_STEP = 0.25

Blocked = Callable[[float, float, float], bool]  # (x, y, diameter) -> vetoed


@dataclass(frozen=True)
class SeamHole:
    """A Seam hole and where it belongs: ``section`` is "left"/"right", ``rows``
    is "lower"/"upper"."""

    x: float
    y: float
    diameter: float
    section: str
    rows: str

    def as_hole(self) -> MountingHole:
        return MountingHole(self.x, self.y, self.diameter)


def _gaps(cutouts: list[Cutout]) -> list[float]:
    """Y of the middle of the gap between each pair of adjacent key rows."""
    rows = _rows_by_cutouts(cutouts)
    spans = [(min(_y_span(c)[0] for c in r), max(_y_span(c)[1] for c in r)) for r in rows]
    return [(a[1] + b[0]) / 2.0 for a, b in zip(spans, spans[1:])]


def _rows_by_cutouts(cutouts: list[Cutout]) -> list[list[Cutout]]:
    class _Model:  # the row grouping only reads the cutout lists
        switch_cutouts = cutouts
        stabilizer_cutouts: list[Cutout] = []

    return _rows(_Model)  # type: ignore[arg-type]


def _clear_of_cutouts(x: float, y: float, radius: float, cutouts: list[Cutout]) -> bool:
    for cut in cutouts:
        x0, x1 = _x_span(cut)
        y0, y1 = _y_span(cut)
        nx = min(max(x, x0), x1)
        ny = min(max(y, y0), y1)
        if math.hypot(x - nx, y - ny) < radius + CUTOUT_MARGIN:
            return False
    return True


def _seam_x_near(seam: RowSeam, y: float) -> tuple[float, float]:
    """``(left, right)`` Seam X at height ``y`` (the jog's extremes at a row gap)."""
    xs = [x for y0, y1, x in seam.bands if y0 - 1e-6 <= y <= y1 + 1e-6]
    return (min(xs), max(xs)) if xs else (0.0, 0.0)


def seam_holes(
    switch_cutouts: list[Cutout],
    stabilizer_cutouts: list[Cutout],
    seam: RowSeam,
    outline_bounds: tuple[float, float, float, float],
    unit: float,
    screw_diameter: float,
    blocked: Blocked | None = None,
    edge_margin: float = 3.0,
) -> list[SeamHole]:
    """Up to four holes: per Section one in the lower rows, one in the upper.

    Each is the free spot nearest the Seam, no further than ``unit`` from it,
    in a row gap (``gaps`` between adjacent rows; the middle gap is the
    fallback for either half). ``outline_bounds`` is ``(x0, y0, x1, y1)`` of the
    plate; holes keep ``edge_margin`` inside it.
    """
    cutouts = list(switch_cutouts) + list(stabilizer_cutouts)
    gaps = _gaps(cutouts)
    if len(gaps) < 2:
        return []
    # Lower rows use the first gap, upper rows the last; the middle gap is the
    # fallback for either half.
    middle = [gaps[len(gaps) // 2]] if len(gaps) > 2 else []
    groups = (("lower", [gaps[0]] + middle), ("upper", [gaps[-1]] + middle))
    x0, y0, x1, y1 = outline_bounds
    radius = screw_diameter / 2.0
    #: A hole keeps this far from the Seam line so the cut never clips it.
    seam_gap = radius + 1.0
    found: list[SeamHole] = []
    for rows, candidates in groups:
        for section, sign in (("left", -1.0), ("right", 1.0)):
            for gy in candidates:
                sl, sr = _seam_x_near(seam, gy)
                start = sl if sign < 0 else sr
                spot = None
                offset = seam_gap
                while offset <= unit + 1e-9:
                    x = start + sign * offset
                    offset += _STEP
                    if not (x0 + edge_margin <= x <= x1 - edge_margin):
                        break
                    if not _clear_of_cutouts(x, gy, radius, cutouts):
                        continue
                    if blocked is not None and blocked(x, gy, screw_diameter):
                        continue
                    if any(math.hypot(x - h.x, gy - h.y) < 2 * screw_diameter for h in found):
                        continue
                    spot = (x, gy)
                    break
                if spot is not None:
                    found.append(SeamHole(spot[0], spot[1], screw_diameter, section, rows))
                    break
    return found


__all__ = ["CUTOUT_MARGIN", "SeamHole", "seam_holes"]
