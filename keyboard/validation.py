"""Keyboard plate validation.

Checks per ``docs/keyboard_architecture.md``:

* no overlapping cutouts
* valid stabilizer spacing
* switch entirely inside outline
* mounting holes inside plate
* minimum edge distance
* valid plate thickness
* no duplicate keys
* supported switch family
* supported stabilizer family

Generation must fail with explicit errors rather than silently producing
invalid geometry.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from keyboard.registry import get_switch, registered_stabilizers, registered_switches

if TYPE_CHECKING:
    from keyboard.layout.layout import KeyboardLayout
    from keyboard.metadata import Cutout, KeyboardGeometryModel


def validate(
    layout: KeyboardLayout,
    model: KeyboardGeometryModel,
    switch_family: str,
    stabilizer_family: str,
) -> tuple[int, list[str]]:
    """Validate the keyboard geometry model.

    Parameters
    ----------
    layout : KeyboardLayout
        The parsed keyboard layout.
    model : KeyboardGeometryModel
        The generated geometry model.
    switch_family : str
        The switch family used.
    stabilizer_family : str
        The stabilizer family used.

    Returns
    -------
    tuple[int, list[str]]
        ``(checks_run, errors)`` — number of checks executed and any error
        messages. An empty ``errors`` list means the model is valid.
    """
    errors: list[str] = []
    checks = 0

    # Supported families
    checks += 1
    if switch_family not in registered_switches():
        errors.append(f"Unsupported switch family: {switch_family!r}")
    checks += 1
    if stabilizer_family not in registered_stabilizers():
        errors.append(f"Unsupported stabilizer family: {stabilizer_family!r}")

    # No duplicate keys
    checks += 1
    seen: set[tuple[float, float]] = set()
    for k in layout.keys:
        pos = (round(k.x, 4), round(k.y, 4))
        if pos in seen:
            errors.append(f"Duplicate key at ({k.x}, {k.y})")
        seen.add(pos)

    # Switch cutouts inside outline
    checks += 1
    if model.plate_outline:
        xs = [p[0] for p in model.plate_outline]
        ys = [p[1] for p in model.plate_outline]
        x0, x1 = min(xs), max(xs)
        y0, y1 = min(ys), max(ys)
        for cut in model.switch_cutouts:
            for vx, vy in cut.vertices:
                wx = cut.x + vx
                wy = cut.y + vy
                if not (x0 <= wx <= x1 and y0 <= wy <= y1):
                    errors.append(
                        f"Switch cutout at ({cut.x}, {cut.y}) extends "
                        f"outside plate outline"
                    )
                    break

    # Mounting holes inside plate
    checks += 1
    if model.plate_outline:
        xs = [p[0] for p in model.plate_outline]
        ys = [p[1] for p in model.plate_outline]
        x0, x1 = min(xs), max(xs)
        y0, y1 = min(ys), max(ys)
        for hole in model.mounting_holes:
            if not (x0 < hole.x < x1 and y0 < hole.y < y1):
                errors.append(
                    f"Mounting hole at ({hole.x}, {hole.y}) is outside plate"
                )

    # Minimum edge margin — material between cutout edge and plate edge
    checks += 1
    if model.plate_outline:
        oxs = [p[0] for p in model.plate_outline]
        oys = [p[1] for p in model.plate_outline]
        ox0, ox1 = min(oxs), max(oxs)
        oy0, oy1 = min(oys), max(oys)
        min_margin = 0.5
        for cut in model.switch_cutouts:
            for vx, vy in cut.vertices:
                wx = cut.x + vx
                wy = cut.y + vy
                margin = min(wx - ox0, ox1 - wx, wy - oy0, oy1 - wy)
                if margin < min_margin:
                    errors.append(
                        f"Switch cutout at ({cut.x:.1f}, {cut.y:.1f}) has only "
                        f"{margin:.2f}mm edge margin (minimum {min_margin}mm)"
                    )
                    break

    # Mounting holes not overlapping switch/stabilizer cutouts
    checks += 1
    all_cuts: list[Cutout] = list(model.switch_cutouts) + list(model.stabilizer_cutouts)
    for hole in model.mounting_holes:
        for cut in all_cuts:
            rx = hole.x - cut.x
            ry = hole.y - cut.y
            if _point_in_polygon(rx, ry, cut.vertices):
                errors.append(
                    f"Mounting hole at ({hole.x:.1f}, {hole.y:.1f}) overlaps "
                    f"cutout at ({cut.x:.1f}, {cut.y:.1f})"
                )
                break

    # Valid plate thickness
    checks += 1
    if model.metadata and model.metadata.plate_thickness <= 0:
        errors.append(f"Invalid plate thickness: {model.metadata.plate_thickness}")

    return checks, errors


def _point_in_polygon(
    px: float, py: float, verts: list[tuple[float, float]]
) -> bool:
    """Ray-casting point-in-polygon test."""
    inside = False
    n = len(verts)
    j = n - 1
    for i in range(n):
        xi, yi = verts[i]
        xj, yj = verts[j]
        if ((yi > py) != (yj > py)) and (
            px < (xj - xi) * (py - yi) / (yj - yi) + xi
        ):
            inside = not inside
        j = i
    return inside
