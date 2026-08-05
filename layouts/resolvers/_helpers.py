"""Shared helpers for constraint resolvers."""

from __future__ import annotations

from typing import Any

from layouts.base import Placement


def estimate_enclosure(
    current: dict[str, Placement],
    components: dict[str, Any],
    config: Any,
    hint_width: float | None = None,
    hint_depth: float | None = None,
    hint_height: float | None = None,
) -> tuple[float, float, float]:
    """Estimate enclosure outer dimensions from current placements + config.

    Returns ``(width, depth, height)`` in mm (outer envelope including walls).
    Falls back to a reasonable default when no placements exist.
    """
    wall = getattr(config, "wall_thickness", 2.0)
    clearance = getattr(getattr(config, "clearance", None), "shell", 0.35)

    if hint_width is not None and hint_depth is not None:
        return (hint_width, hint_depth, hint_height or 60.0)

    if not current:
        return (240.0, 140.0, 40.0)

    xs: list[float] = []
    ys: list[float] = []
    zs: list[float] = []
    for name, placement in current.items():
        comp = components.get(name)
        if comp is None:
            continue
        box = comp.size()
        xs.extend([placement.x - box.width / 2, placement.x + box.width / 2])
        ys.extend([placement.y - box.depth / 2, placement.y + box.depth / 2])
        zs.extend([placement.z, placement.z + box.height])

    width = max(xs) - min(xs) + 2 * (clearance + wall)
    depth = max(ys) - min(ys) + 2 * (clearance + wall)
    height = max(zs) - min(zs) + 2 * (clearance + wall)
    return (width, depth, height)


def interior_bounds(
    enclosure_w: float, enclosure_d: float, wall: float
) -> tuple[float, float, float, float]:
    """Return ``(left, right, rear, front)`` of the enclosure interior."""
    iw = enclosure_w - 2 * wall
    id_ = enclosure_d - 2 * wall
    return (-iw / 2, iw / 2, -id_ / 2, id_ / 2)


def edge_position(
    comp_x: float, comp_y: float,
    comp_w: float, comp_d: float,
    edge: str,
) -> tuple[float, float]:
    """Return the world-frame position of a component's edge midpoint."""
    if edge == "front":
        return (comp_x, comp_y + comp_d / 2)
    elif edge == "rear":
        return (comp_x, comp_y - comp_d / 2)
    elif edge == "left":
        return (comp_x - comp_w / 2, comp_y)
    elif edge == "right":
        return (comp_x + comp_w / 2, comp_y)
    else:
        raise ValueError(f"unknown edge: {edge!r}")


def align_edges(
    subj_w: float, subj_d: float,
    target_x: float, target_y: float,
    target_w: float, target_d: float,
    subj_edge: str, target_edge: str,
    offset: float = 0.0,
) -> tuple[float, float]:
    """Compute subject position so *subj_edge* aligns to *target_edge*.

    Parameters
    ----------
    subj_w, subj_d : float
        Subject component width and depth.
    target_x, target_y : float
        Target component center position.
    target_w, target_d : float
        Target component width and depth.
    subj_edge, target_edge : str
        Edge names (``"front"``, ``"rear"``, ``"left"``, ``"right"``).
    offset : float
        Extra gap. Positive = outward from subject.

    Returns
    -------
    tuple[float, float]
        ``(subject_x, subject_y)``.
    """
    tx, ty = edge_position(target_x, target_y, target_w, target_d, target_edge)

    if subj_edge == "front":
        return (tx, ty - subj_d / 2 + offset)
    elif subj_edge == "rear":
        return (tx, ty + subj_d / 2 + offset)
    elif subj_edge == "left":
        return (tx + subj_w / 2 + offset, ty)
    elif subj_edge == "right":
        return (tx - subj_w / 2 + offset, ty)
    else:
        raise ValueError(f"unknown subject edge: {subj_edge!r}")


__all__ = [
    "estimate_enclosure",
    "interior_bounds",
    "edge_position",
    "align_edges",
]
