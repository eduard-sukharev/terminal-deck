"""Plate outline generation.

Computes the plate outline polygon from switch centers, per-side margins, and a
corner radius, then applies the enclosure's tabs (ears) and notches. The tabs
and notches arrive as plain rectangles from the caller -- the keyboard package
never imports the enclosure (ADR-0014): it only merges the shapes it is handed
into one polygon, so the plate stays a single flat sheet.

A **tab** is a filleted rectangle growing outboard of a straight plate edge (the
M2 boss stations cannot fit inside the ring-width border). A **notch** is a
rectangle the chassis forces the sheet to give up; it bites into the outline
from an edge. Both are applied as pure polygon operations: no CAD library, and
no knowledge of what produced them.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

#: A margin per side, ``(left, right, bottom, top)`` = ``(-X, +X, -Y, +Y)`` of
#: the switch-center bounding box, or one uniform ``float`` for every side.
Margins = float | tuple[float, float, float, float]

#: A rectangle ``(x0, y0, x1, y1)`` in plate-local mm.
Rect = tuple[float, float, float, float]

#: Points closer than this are the same point (mm).
_EPS = 1e-9


@dataclass(frozen=True)
class PlateTab:
    """A filleted tab extending the plate outboard of an edge (plate-local mm).

    ``rect`` is the tab's rectangle, including the inboard overlap the union
    needs; ``fillet`` rounds its two outboard corners (0 keeps them sharp).
    """

    rect: Rect
    fillet: float = 0.0


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
        for i in range(segments + 1):
            angle = math.radians(start_deg + (end_deg - start_deg) * i / segments)
            verts.append((cx + radius * math.cos(angle), cy + radius * math.sin(angle)))
    return verts


# -- tabs and notches -----------------------------------------------------


def _area(poly: list[tuple[float, float]]) -> float:
    """Signed shoelace area (mm^2); positive when counter-clockwise."""
    return sum(
        a[0] * b[1] - b[0] * a[1] for a, b in zip(poly, poly[1:] + poly[:1])
    ) / 2.0


def _ccw(poly: list[tuple[float, float]]) -> list[tuple[float, float]]:
    return poly if _area(poly) >= 0.0 else list(reversed(poly))


def _same(a: tuple[float, float], b: tuple[float, float]) -> bool:
    return abs(a[0] - b[0]) <= _EPS and abs(a[1] - b[1]) <= _EPS


def _inside(x: float, y: float, poly: list[tuple[float, float]]) -> bool:
    """Ray-casting point-in-polygon (boundary results are unspecified)."""
    inside = False
    n = len(poly)
    j = n - 1
    for i in range(n):
        xi, yi = poly[i]
        xj, yj = poly[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
            inside = not inside
        j = i
    return inside


def _strictly_inside_rect(x: float, y: float, rect: Rect) -> bool:
    x0, y0, x1, y1 = rect
    return x0 + _EPS < x < x1 - _EPS and y0 + _EPS < y < y1 - _EPS


def _chain_inside_rect(chain: list[tuple[float, float]], rect: Rect) -> bool:
    """True when any part of ``chain`` lies strictly inside ``rect``."""
    points = chain + [
        ((a[0] + b[0]) / 2.0, (a[1] + b[1]) / 2.0)
        for a, b in zip(chain, chain[1:])
    ]
    return any(_strictly_inside_rect(x, y, rect) for x, y in points)


def _segment_hit(
    p: tuple[float, float], q: tuple[float, float],
    a: tuple[float, float], b: tuple[float, float],
) -> float | None:
    """Parameter ``t`` along ``p -> q`` where it properly crosses ``a -> b``."""
    rx, ry = q[0] - p[0], q[1] - p[1]
    sx, sy = b[0] - a[0], b[1] - a[1]
    denom = rx * sy - ry * sx
    if abs(denom) < 1e-15:
        return None
    t = ((a[0] - p[0]) * sy - (a[1] - p[1]) * sx) / denom
    u = ((a[0] - p[0]) * ry - (a[1] - p[1]) * rx) / denom
    if _EPS < t < 1.0 - _EPS and _EPS < u < 1.0 - _EPS:
        return t
    return None


def _rect_ring(rect: Rect) -> list[tuple[float, float]]:
    x0, y0, x1, y1 = rect
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def _subtract_rect(
    poly: list[tuple[float, float]], rect: Rect
) -> list[tuple[float, float]]:
    """The polygon ``poly`` with ``rect`` removed (single ring, mm).

    The rectangle must cross the boundary exactly twice, so the remainder is
    one connected ring: the part of ``poly`` outside the rectangle plus the
    part of the rectangle's boundary inside ``poly``. That is the case for every
    chassis notch (it bites in from an edge); a rectangle that would split the
    plate or punch a hole is a HARD error -- the caller's data is wrong, not
    something to guess about.
    """
    x0, y0, x1, y1 = rect
    if not (x0 < x1 and y0 < y1):
        raise ValueError(f"notch rectangle is inside out: {rect}")
    poly = _ccw(poly)
    ring = _rect_ring(rect)

    points: list[tuple[float, float]] = []
    for i in range(len(poly)):
        p, q = poly[i], poly[(i + 1) % len(poly)]
        for j in range(4):
            a, b = ring[j], ring[(j + 1) % 4]
            t = _segment_hit(p, q, a, b)
            if t is not None:
                points.append((p[0] + t * (q[0] - p[0]), p[1] + t * (q[1] - p[1])))
    points = _dedupe(points)
    if len(points) != 2:
        raise ValueError(
            f"a notch must cross the plate outline exactly twice, this one "
            f"crosses it {len(points)} times: {rect}"
        )

    with_hits = _insert_points(poly, points)
    with_rect = _insert_points(ring, points)
    i1 = _index_of(points[0], with_hits)
    i2 = _index_of(points[1], with_hits)
    chain_a = _chain(with_hits, i1, i2)
    chain_b = _chain(with_hits, i2, i1)
    # The chain with a vertex (or edge midpoint) strictly inside the rectangle
    # is the piece that gets removed; the other one is the surviving boundary.
    inside_a = _chain_inside_rect(chain_a, rect)
    inside_b = _chain_inside_rect(chain_b, rect)
    if inside_a == inside_b:
        raise ValueError(f"cannot tell the notch's inside from its outside: {rect}")
    chain_out = chain_b if inside_a else chain_a

    arc = _rect_arc(with_rect, chain_out[-1], chain_out[0], inside_poly=True, poly=poly)
    return _ccw(chain_out + arc)


def _dedupe(points: list[tuple[float, float]]) -> list[tuple[float, float]]:
    out: list[tuple[float, float]] = []
    for point in points:
        if not any(_same(point, seen) for seen in out):
            out.append(point)
    return out


def _insert_points(
    poly: list[tuple[float, float]], points: list[tuple[float, float]]
) -> list[tuple[float, float]]:
    """Insert each point into the ring edge it lies on, in edge order."""
    out: list[tuple[float, float]] = []
    for i in range(len(poly)):
        p, q = poly[i], poly[(i + 1) % len(poly)]
        on_edge = []
        for point in points:
            t = _point_on_segment(point, p, q)
            if t is not None:
                on_edge.append((t, point))
        out.append(p)
        out.extend(point for _, point in sorted(on_edge, key=lambda item: item[0]))
    return out


def _point_on_segment(
    point: tuple[float, float],
    p: tuple[float, float],
    q: tuple[float, float],
) -> float | None:
    """Parameter ``t`` of ``point`` on ``p -> q``, or ``None``."""
    cross = (q[0] - p[0]) * (point[1] - p[1]) - (q[1] - p[1]) * (point[0] - p[0])
    if abs(cross) > 1e-7:
        return None
    length = math.hypot(q[0] - p[0], q[1] - p[1])
    if length <= _EPS:
        return None
    t = ((point[0] - p[0]) * (q[0] - p[0]) + (point[1] - p[1]) * (q[1] - p[1])) / (
        length * length
    )
    return t if -1e-7 <= t <= 1.0 + 1e-7 else None


def _index_of(
    point: tuple[float, float], ring: list[tuple[float, float]]
) -> int:
    for index, vertex in enumerate(ring):
        if _same(point, vertex):
            return index
    raise ValueError(f"{point} is not on the ring")


def _chain(
    ring: list[tuple[float, float]], start: int, end: int
) -> list[tuple[float, float]]:
    """The ring vertices from ``start`` to ``end`` walking forward."""
    out = [ring[start]]
    index = start
    while index != end:
        index = (index + 1) % len(ring)
        out.append(ring[index])
    return out


def _rect_arc(
    ring: list[tuple[float, float]],
    start: tuple[float, float],
    end: tuple[float, float],
    *,
    inside_poly: bool,
    poly: list[tuple[float, float]],
) -> list[tuple[float, float]]:
    """The rectangle boundary arc from ``start`` to ``end`` (end excluded).

    The rectangle has two arcs between the two crossings; exactly one lies
    inside ``poly`` and one outside. ``inside_poly`` picks which -- the notch
    keeps the inside arc, a tab would keep the outside one.
    """
    i = _index_of(start, ring)
    j = _index_of(end, ring)
    n = len(ring)
    forward = _chain(ring, i, j)
    backward = _chain(ring, j, i)
    backward.reverse()
    for candidate in (forward, backward):
        if len(candidate) < 2:
            continue
        a, b = candidate[0], candidate[1]
        mid = ((a[0] + b[0]) / 2.0, (a[1] + b[1]) / 2.0)
        if _inside(mid[0], mid[1], poly) == inside_poly:
            return candidate[1:-1]
    # A zero-length arc (crossings on adjacent rectangle corners).
    return []


def _tab_run(
    p: tuple[float, float],
    q: tuple[float, float],
    rect: Rect,
    fillet: float,
    segments: int = 8,
) -> list[tuple[float, float]]:
    """Thin-plate tab's boundary between the crossings on a straight edge.

    ``p -> q`` is the edge's travel direction, so the run is emitted in the
    same direction and the ring stays closed. The tab's two outboard corners
    are rounded with ``fillet``.
    """
    x0, y0, x1, y1 = rect
    edge_y = p[1]
    # The tab reaches outboard past the plate edge; the rectangle also carries
    # the inboard overlap, so the longer side is the outboard one.
    outward = -1.0 if (edge_y - y0) > (y1 - edge_y) else 1.0
    y_out = y0 if outward < 0 else y1
    inward = -outward
    d = 1.0 if q[0] > p[0] else -1.0
    near, far = (x0, x1) if d > 0 else (x1, x0)
    radius = max(
        0.0,
        min(fillet, abs(far - near) / 2.0, abs(edge_y - y_out)),
    )

    run: list[tuple[float, float]] = []

    def push(point: tuple[float, float]) -> None:
        if run and _same(point, run[-1]):
            return
        run.append(point)

    push((near, edge_y))
    if radius > _EPS:
        side_y = y_out + inward * radius
        push((near, side_y))
        _arc_between(
            near + d * radius, side_y, (near, side_y), (near + d * radius, y_out),
            segments, push,
        )
        _arc_between(
            far - d * radius, side_y, (far - d * radius, y_out), (far, side_y),
            segments, push,
        )
        push((far, edge_y))
    else:
        push((near, y_out))
        push((far, y_out))
        push((far, edge_y))
    if run and _same(run[-1], q):
        run.pop()
    return run


def _arc_between(
    cx: float,
    cy: float,
    start: tuple[float, float],
    end: tuple[float, float],
    segments: int,
    push,
) -> None:
    """Emit a fillet arc of radius ``|start - centre|`` from ``start`` to ``end``.

    ``start`` is already on the ring, so it is not emitted again. The short
    sweep is the fillet: anything more would wrap the arc around the tab.
    """
    a0 = math.atan2(start[1] - cy, start[0] - cx)
    a1 = math.atan2(end[1] - cy, end[0] - cx)
    delta = (a1 - a0 + math.pi) % (2.0 * math.pi) - math.pi
    radius = math.hypot(start[0] - cx, start[1] - cy)
    for i in range(1, segments + 1):
        angle = a0 + delta * i / segments
        push((cx + radius * math.cos(angle), cy + radius * math.sin(angle)))


def _apply_tab(
    poly: list[tuple[float, float]], tab: PlateTab, segments: int = 8
) -> list[tuple[float, float]]:
    """Grow ``poly`` by one filleted tab straddling a straight edge."""
    poly = _ccw(poly)
    x0, y0, x1, y1 = tab.rect
    if not (x0 < x1 and y0 < y1):
        raise ValueError(f"tab rectangle is inside out: {tab.rect}")
    for i in range(len(poly)):
        p, q = poly[i], poly[(i + 1) % len(poly)]
        if abs(p[1] - q[1]) > _EPS:
            continue
        if not (y0 + _EPS < p[1] < y1 - _EPS):
            continue
        lo, hi = min(p[0], q[0]), max(p[0], q[0])
        if lo > x0 + _EPS or hi < x1 - _EPS:
            continue
        run = _tab_run(p, q, tab.rect, tab.fillet, segments)
        out: list[tuple[float, float]] = []
        for index in range(len(poly)):
            out.append(poly[index])
            if index == i:
                out.extend(run)
        return _ccw(out)
    raise ValueError(
        f"the tab {tab.rect} does not straddle a straight plate edge: the "
        "outline cannot attach it"
    )


def attach_features(
    outline: list[tuple[float, float]],
    tabs=(),
    notches=(),
) -> list[tuple[float, float]]:
    """Merge ``tabs`` into and cut ``notches`` out of a plate ``outline``.

    ``tabs`` are :class:`PlateTab` (or ``(rect, fillet)`` pairs), ``notches``
    are ``(x0, y0, x1, y1)`` rectangles; all plate-local mm. Pure data: the
    caller decides what the shapes mean (ADR-0014).
    """
    poly = _ccw(list(outline))
    for rect in notches:
        poly = _subtract_rect(poly, tuple(float(v) for v in rect))
    for tab in tabs:
        if not isinstance(tab, PlateTab):
            rect, fillet = tab
            tab = PlateTab(tuple(float(v) for v in rect), float(fillet))
        poly = _apply_tab(poly, tab)
    return poly


__all__ = ["Margins", "PlateTab", "Rect", "attach_features", "generate_outline"]
