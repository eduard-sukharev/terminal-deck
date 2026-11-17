"""Render the keyboard switch plate as a high-contrast 2D SVG/PNG.

Pure-data render (no CAD library): draws the plate outline, switch cutouts,
stabilizer cutouts, and mounting holes from the generated geometry model.
Uses ``fill-rule="evenodd"`` so cutouts show as holes. For vision-model QA.

Usage::

    python utilities/render_plate_svg.py -o generated/plate_top.svg
    python utilities/render_plate_svg.py -o /tmp/plate_top.png --png
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from keyboard import generate, parse_layout  # noqa: E402
from keyboard.metadata import Cutout  # noqa: E402
from utilities.config_loader import load_config  # noqa: E402


def _svg_points(vertices: list[tuple[float, float]]) -> str:
    return " ".join(f"{x:.2f},{y:.2f}" for x, y in vertices)


def _polygon_path(vertices: list[tuple[float, float]]) -> str:
    return "M " + _svg_points(vertices) + " Z"


def render_svg(
    layout_source: str,
    out_path: Path,
    *,
    wobble: float,
    wall: float,
    plate_thickness: float,
    pitch: float = 19.05,
    switch_family: str = "mx_alps",
    stabilizer_family: str = "cherry",
    keycap_profile: str = "xda",
    corner_radius: float = 2.0,
    plate_color: str = "#2B3A67",
    hole_color: str = "#FFFFFF",
    switch_color: str = "#FFFFFF",
    stabilizer_color: str = "#F4C430",
    scale: float = 1.0,
) -> str:
    """Write the plate SVG and return its XML string.

    ``wobble``, ``wall`` and ``plate_thickness`` have no defaults on purpose:
    they come from the config (``keyboard.plate.wobble``,
    ``wall.thickness``, ``keyboard.plate.thickness``), the one source the
    build derives the Well and the plate from.
    """
    with open(layout_source, encoding="utf-8") as handle:
        raw = json.load(handle)
    layout = parse_layout(raw, pitch)
    model = generate(
        layout,
        switch_family=switch_family,
        stabilizer_family=stabilizer_family,
        plate_thickness=plate_thickness,
        wall=wall,
        wobble=wobble,
        keycap_profile=keycap_profile,
        corner_radius=corner_radius,
    )

    outline = model.plate_outline
    xs = [p[0] for p in outline]
    ys = [p[1] for p in outline]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)

    pad = 8.0
    width = (max_x - min_x + 2 * pad) * scale
    height = (max_y - min_y + 2 * pad) * scale

    def world(cx: float, cy: float) -> tuple[float, float]:
        return (
            (cx - min_x + pad) * scale,
            (height - (cy - min_y + pad) * scale),
        )

    def cutout_path(cut: Cutout) -> str:
        verts = [(v[0] + cut.x, v[1] + cut.y) for v in cut.vertices]
        return _polygon_path([world(x, y) for x, y in verts])

    body = _polygon_path([world(x, y) for x, y in outline])
    switch_paths = [cutout_path(c) for c in model.switch_cutouts]
    stab_paths = [cutout_path(c) for c in model.stabilizer_cutouts]

    hole_elems = []
    for h in model.mounting_holes:
        hx, hy = world(h.x, h.y)
        hole_elems.append(
            f'<circle cx="{hx:.2f}" cy="{hy:.2f}" r="{h.diameter / 2:.2f}" fill="{hole_color}" stroke="#E74C3C" stroke-width="1.2"/>'
        )

    def clip_group(elements: list[str]) -> str:
        return '<g fill-rule="evenodd">' + "".join(
            f'<path d="{p}" fill="{plate_color}"/>' for p in elements
        ) + "</g>"

    def fill_group(elements: list[str], color: str) -> str:
        return '<g>' + "".join(
            f'<path d="{p}" fill="{color}" fill-rule="evenodd"/>' for p in elements
        ) + "</g>"

    switch_group = fill_group(switch_paths, switch_color)
    stab_group = fill_group(stab_paths, stabilizer_color)
    body_path = f'<path d="{body}" fill="{plate_color}" stroke="#10182F" stroke-width="1.2"/>'

    # The plate splits between keys along this Seam (ADR-0014, #9).
    seam_path = ""
    if model.seam is not None:
        seam_points = " L ".join(
            f"{x:.2f},{y:.2f}"
            for x, y in (
                world(sx, sy)
                for sx, sy in model.seam.polyline(model.metadata.height)
            )
        )
        seam_path = (
            f'<path d="M {seam_points}" fill="none" stroke="#E74C3C" '
            'stroke-width="1.6" stroke-dasharray="6 3"/>'
        )

    xml = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width:.1f}" height="{height:.1f}" viewBox="0 0 {width:.1f} {height:.1f}">
  <rect x="0" y="0" width="{width:.1f}" height="{height:.1f}" fill="#E8EAF0"/>
  {body_path}
  {switch_group}
  {stab_group}
  {seam_path}
  {'\n  '.join(hole_elems)}
</svg>
"""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(xml, encoding="utf-8")
    return xml


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--layout", default="keyboard/layouts/jd40.json")
    parser.add_argument("-o", "--out", default="generated/plate_top.svg")
    parser.add_argument("--png", action="store_true", help="also convert to PNG via inkscape")
    parser.add_argument("--pitch", type=float, default=None,
                        help="switch pitch (default: config.keyboard.pitch)")
    parser.add_argument("--wall", type=float, default=None,
                        help="Well ring / plate border per side (default: config.wall.thickness)")
    parser.add_argument("--wobble", type=float, default=None,
                        help="keycap wobble per side (default: keyboard.plate.wobble)")
    parser.add_argument("--scale", type=float, default=1.0)
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="print 'wrote …' lines (quiet by default)")
    args = parser.parse_args(argv)

    # The Well and the plate are derived from the config; the tool reads the
    # same values instead of carrying its own 0.6 / 2.0 defaults.
    config = load_config()
    out = Path(args.out)
    xml = render_svg(
        args.layout,
        out,
        wobble=config.keyboard.plate_wobble if args.wobble is None else args.wobble,
        wall=config.wall_thickness if args.wall is None else args.wall,
        plate_thickness=config.keyboard.plate_thickness,
        pitch=config.keyboard.pitch if args.pitch is None else args.pitch,
        scale=args.scale,
    )
    if args.verbose:
        print(f"wrote {out}  ({len(xml)} bytes)")
    if args.png:
        png = out.with_suffix(".png")
        subprocess.run(
            ["inkscape", str(out), "--export-type=png", "--export-filename", str(png)],
            check=True,
            capture_output=True,
        )
        if args.verbose:
            print(f"wrote {png}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
