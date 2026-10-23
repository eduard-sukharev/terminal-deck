"""Merged boss: a boss standing close to a wall is fused into it (ADR 0003).

A boss, column, standoff or lug whose outer surface is closer than
``2 * wall`` to a wall face cannot print as a free post: the sliver of air
between it and the wall is unprintable. It is merged instead — a hull from
the boss to the wall (to both walls in a corner) — and the wall becomes part
of its sleeve, so its bore may sit closer to the wall than a free boss's.

Classification and limits are pure data; only :func:`build_hull` needs the
CAD library. Battery cradles are exempt (solid blocks, no bore to protect).
"""

from __future__ import annotations

from dataclasses import dataclass

from utilities import cad_helpers

WALLS: tuple[str, ...] = ("left", "right", "rear", "front")


@dataclass(frozen=True)
class WallBounds:
    """Interior wall faces of a shell (mm): X from ``x0`` to ``x1``, Y from
    ``y0`` (rear) to ``y1`` (front)."""

    x0: float
    x1: float
    y0: float
    y1: float


def merge_walls(
    cx: float, cy: float, radius: float, bounds: WallBounds, wall: float, rule
) -> tuple[str, ...]:
    """Walls a boss of outer ``radius`` at ``(cx, cy)`` is merged into.

    A wall counts when the gap between the boss's outer surface and the wall's
    inner face is below ``rule.threshold_factor * wall``. Empty means free.
    """
    limit = rule.threshold_factor * wall
    gaps = {
        "left": (cx - radius) - bounds.x0,
        "right": bounds.x1 - (cx + radius),
        "rear": (cy - radius) - bounds.y0,
        "front": bounds.y1 - (cy + radius),
    }
    return tuple(name for name in WALLS if gaps[name] < limit - 1e-9)


def min_bore_gap(wall: float, rule) -> float:
    """Closest a Merged boss's bore edge may come to the wall's inner face (mm).

    That leaves ``wall + rule.bore_margin`` between bore and outer skin.
    """
    return rule.bore_margin


def bore_center_limits(
    bore_radius: float, bounds: WallBounds, rule
) -> tuple[float, float, float, float]:
    """``(x_min, x_max, y_min, y_max)`` the bore centre may take (mm)."""
    gap = rule.bore_margin
    return (
        bounds.x0 + bore_radius + gap,
        bounds.x1 - bore_radius - gap,
        bounds.y0 + bore_radius + gap,
        bounds.y1 - bore_radius - gap,
    )


def build_hull(
    cx: float, cy: float, radius: float, height: float, walls: tuple[str, ...],
    bounds: WallBounds, overlap: float, z0: float = 0.0,
):
    """Solid filling the gap between a boss and its walls, ``z0`` up ``height``.

    Plan view: for each wall a slab as wide as the boss, from the boss axis to
    the wall face (plus ``overlap`` into the wall so the union is a real
    overlap); in a corner the block between the axis and both walls. The boss
    cylinder itself is added by the caller.
    """
    face = {"left": bounds.x0, "right": bounds.x1, "rear": bounds.y0, "front": bounds.y1}
    pieces = []

    def slab(xa: float, xb: float, ya: float, yb: float):
        box = cad_helpers.box_centered(abs(xb - xa), abs(yb - ya), height)
        return cad_helpers.translate(box, (xa + xb) / 2.0, (ya + yb) / 2.0, z0 + height / 2.0)

    for name in walls:
        if name in ("left", "right"):
            sign = -1.0 if name == "left" else 1.0
            edge = face[name] + sign * overlap
            pieces.append(slab(cx, edge, cy - radius, cy + radius))
        else:
            sign = -1.0 if name == "rear" else 1.0
            edge = face[name] + sign * overlap
            pieces.append(slab(cx - radius, cx + radius, cy, edge))
    if len(walls) == 2 and not set(walls) <= {"left", "right"} and not set(walls) <= {"rear", "front"}:
        x_wall = next(w for w in walls if w in ("left", "right"))
        y_wall = next(w for w in walls if w in ("rear", "front"))
        xs = face[x_wall] + (-overlap if x_wall == "left" else overlap)
        ys = face[y_wall] + (-overlap if y_wall == "rear" else overlap)
        pieces.append(slab(cx, xs, cy, ys))
    if not pieces:
        return None
    return cad_helpers.union(pieces[0], *pieces[1:])
