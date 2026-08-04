"""SVG export for the keyboard plate.

Produces a 2D SVG of the plate outline and cutouts for visual verification.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from keyboard.metadata import KeyboardGeometryModel


def export_svg(model: KeyboardGeometryModel, path: str | Path) -> None:
    """Write a 2D SVG of the keyboard plate.

    Parameters
    ----------
    model : KeyboardGeometryModel
        The geometry model to export.
    path : str or Path
        Output file path.
    """
    if not model.plate_outline:
        return

    xs = [p[0] for p in model.plate_outline]
    ys = [p[1] for p in model.plate_outline]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    w = max_x - min_x
    h = max_y - min_y
    pad = 10.0

    lines: list[str] = []
    lines.append(f'<svg xmlns="http://www.w3.org/2000/svg" '
                 f'viewBox="{min_x - pad} {min_y - pad} {w + 2 * pad} {h + 2 * pad}">')

    def _polygon(verts, cls: str, label: str = ""):
        pts = " ".join(f"{v[0]},{v[1]}" for v in verts)
        lines.append(f'  <polygon class="{cls}" points="{pts}" />')

    lines.append('<style>'
                 '.outline { fill: none; stroke: #000; stroke-width: 0.5; }'
                 '.cutout { fill: #ccc; stroke: #999; stroke-width: 0.2; }'
                 '.hole { fill: #fff; stroke: #999; stroke-width: 0.2; }'
                 '</style>')

    _polygon(model.plate_outline, "outline")
    for cut in model.switch_cutouts:
        _polygon(cut.vertices, "cutout")
    for cut in model.stabilizer_cutouts:
        _polygon(cut.vertices, "cutout")
    for hole in model.mounting_holes:
        r = hole.diameter / 2.0
        lines.append(f'  <circle class="hole" cx="{hole.x}" cy="{hole.y}" r="{r}" />')

    lines.append("</svg>")

    with open(path, "w") as f:
        f.write("\n".join(lines))
