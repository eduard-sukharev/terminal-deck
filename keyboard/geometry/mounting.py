"""Mounting hole generation.

Computes mounting hole positions from the plate outline and configuration.
"""

from __future__ import annotations

from keyboard.metadata import MountingHole


def generate_mounting_holes(
    outline: list[tuple[float, float]],
    edge_offset: float = 5.0,
    screw_diameter: float = 2.0,
) -> list[MountingHole]:
    """Generate mounting holes near the plate corners.

    Parameters
    ----------
    outline : list[tuple[float, float]]
        Plate outline polygon vertices.
    edge_offset : float
        Distance from the plate edge to hole center (mm).
    screw_diameter : float
        Screw hole diameter (mm).

    Returns
    -------
    list[MountingHole]
        Mounting hole positions.
    """
    if not outline:
        return []

    xs = [p[0] for p in outline]
    ys = [p[1] for p in outline]
    x0, x1 = min(xs), max(xs)
    y0, y1 = min(ys), max(ys)

    return [
        MountingHole(x0 + edge_offset, y0 + edge_offset, screw_diameter),
        MountingHole(x1 - edge_offset, y0 + edge_offset, screw_diameter),
        MountingHole(x1 - edge_offset, y1 - edge_offset, screw_diameter),
        MountingHole(x0 + edge_offset, y1 - edge_offset, screw_diameter),
    ]
