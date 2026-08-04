"""Render STL parts to shaded, tightly-framed PNG views.

Uses VTK (real depth-buffered OpenGL renderer) with a light kit for proper
key/fill shading — no matplotlib z-sort artifacts, no flat fill. For docs and
quick checks only; the authoritative outputs are the STEP/STL/SVG exports.

The camera is fitted to the model (``vtkRenderer.ResetCamera``) and the final
image is cropped to the rendered silhouette, so the part fills ~90%+ of the
frame and the output is at least 1920x1080 px.

Guidance on angles: view flat rectangular parts axis-aligned (``--azim -90``
keeps the long axis horizontal — an oblique azim of a wide flat part projects
to a parallelogram whose frame is only ~50% filled) and steep enough to see
the interior (``--elev 45-55``). Long thin parts (e.g. the hinge rod) only
fill the frame end-on (``--elev 0 --azim 0``).

Usage::

    python utilities/render_stl.py generated/stl/cyberdeck_base.stl -o /tmp/base.png
    python utilities/render_stl.py generated/stl/cyberdeck_base.stl -o /tmp/base.png --elev 55 --azim -90
    python utilities/render_stl.py generated/stl/cyberdeck_hinge.stl -o /tmp/hinge.png --elev 0 --azim 0
"""

from __future__ import annotations

import argparse
import math
from pathlib import Path

import numpy as np
import vtk
from vtk.util import numpy_support

#: Minimum output resolution (pixels) on each side.
MIN_WIDTH, MIN_HEIGHT = 1920, 1080

_BACKGROUND = np.array([1.0, 1.0, 1.0], dtype=float)  # white


def render(stl_path: Path, out_path: Path, elev: float = 45.0, azim: float = -90.0) -> Path:
    """Render one STL mesh to a shaded, tightly-framed PNG and return its path."""
    # Reader + geometry.
    reader = vtk.vtkSTLReader()
    reader.SetFileName(str(stl_path))
    reader.Update()
    poly = reader.GetOutput()

    mapper = vtk.vtkPolyDataMapper()
    mapper.SetInputConnection(reader.GetOutputPort())

    actor = vtk.vtkActor()
    actor.SetMapper(mapper)
    prop = actor.GetProperty()
    prop.SetColor(0.78, 0.79, 0.82)  # cool light gray
    prop.SetInterpolationToPhong()
    prop.SetDiffuse(0.8)
    prop.SetAmbient(0.28)
    prop.SetSpecular(0.25)
    prop.SetSpecularPower(24.0)

    renderer = vtk.vtkRenderer()
    renderer.SetBackground(*_BACKGROUND)
    renderer.SetBackgroundAlpha(0.0)
    renderer.AddActor(actor)

    # Fixed world-space lights (independent of the camera) so faces read as 3D
    # from every viewing angle — a camera-relative key light would make
    # top-down views of flat parts look uniformly lit.
    key = vtk.vtkLight()
    key.SetPositional(0)  # directional (parallel) light
    key.SetPosition(-0.5, -0.4, 0.75)  # upper-front-left
    key.SetFocalPoint(0.0, 0.0, 0.0)
    key.SetIntensity(0.9)
    key.SetDiffuseColor(1.0, 0.99, 0.96)
    renderer.AddLight(key)

    fill = vtk.vtkLight()
    fill.SetPositional(0)
    fill.SetPosition(0.6, -0.3, 0.4)
    fill.SetFocalPoint(0.0, 0.0, 0.0)
    fill.SetIntensity(0.35)
    fill.SetDiffuseColor(0.92, 0.94, 1.0)
    renderer.AddLight(fill)

    rim = vtk.vtkLight()
    rim.SetPositional(0)
    rim.SetPosition(0.2, 0.7, -0.4)  # from behind the part
    rim.SetFocalPoint(0.0, 0.0, 0.0)
    rim.SetIntensity(0.2)
    rim.SetDiffuseColor(0.95, 0.96, 1.0)
    renderer.AddLight(rim)

    # Camera: fit to the model, +Z up, viewed from (azim, elev).
    bounds = poly.GetBounds()
    center = [(bounds[i] + bounds[i + 1]) / 2.0 for i in (0, 2, 4)]
    cam = renderer.GetActiveCamera()
    cam.SetFocalPoint(*center)
    a = math.radians(azim)
    e = math.radians(elev)
    dist = 3.0 * math.sqrt(sum((bounds[2 * i + 1] - bounds[2 * i]) ** 2 for i in range(3)))
    cam.SetPosition(
        center[0] + dist * math.cos(e) * math.cos(a),
        center[1] + dist * math.cos(e) * math.sin(a),
        center[2] + dist * math.sin(e),
    )
    cam.SetViewUp(0.0, 0.0, 1.0)
    cam.ParallelProjectionOn()
    renderer.ResetCamera()  # refit distance so the part fills the frame
    renderer.ResetCameraClippingRange()

    window = vtk.vtkRenderWindow()
    window.SetSize(MIN_WIDTH, MIN_HEIGHT)
    window.SetOffScreenRendering(1)
    window.SetMultiSamples(8)
    window.AddRenderer(renderer)

    window.Render()
    renderer.SetBackground(*_BACKGROUND)

    # Draw into the frame buffer again so the background is applied.
    window.Render()

    image = vtk.vtkWindowToImageFilter()
    image.SetInput(window)
    image.SetScale(1)
    image.SetInputBufferTypeToRGBA()
    image.ReadFrontBufferOff()
    image.Update()

    writer = vtk.vtkPNGWriter()
    out_path = out_path.with_suffix(".png")
    writer.SetFileName(str(out_path))
    writer.SetInputConnection(image.GetOutputPort())
    writer.Write()

    window.Finalize()

    _crop_to_fit(out_path, margin_frac=0.02)
    return out_path


def _crop_to_fit(path: Path, margin_frac: float = 0.02) -> None:
    """Crop ``path`` to the rendered silhouette and upscale to >= min size."""
    from PIL import Image

    img = Image.open(path).convert("RGB")
    arr = np.asarray(img)
    background = (arr >= 248).all(axis=2)
    ys, xs = np.where(~background)
    if len(xs) == 0:
        return
    x0, x1 = xs.min(), xs.max()
    y0, y1 = ys.min(), ys.max()
    mx = int((x1 - x0) * margin_frac) + 1
    my = int((y1 - y0) * margin_frac) + 1
    x0, x1 = max(0, x0 - mx), min(img.width, x1 + mx)
    y0, y1 = max(0, y0 - my), min(img.height, y1 + my)
    img = img.crop((x0, y0, x1, y1))

    scale = max(MIN_WIDTH / img.width, MIN_HEIGHT / img.height, 1.0)
    if scale > 1.0:
        img = img.resize(
            (round(img.width * scale), round(img.height * scale)),
            Image.LANCZOS,
        )
    img.save(path)


def fill_fraction(path: Path) -> float:
    """Fraction of non-background pixels in a rendered PNG (for QA)."""
    from PIL import Image

    arr = np.asarray(Image.open(path).convert("RGB"))
    background = (arr >= 248).all(axis=2)
    return (arr.size // 3 - int(background.sum())) / (arr.size // 3)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stl", type=Path, help="STL mesh to render")
    parser.add_argument("-o", "--out", type=Path, default=Path("/tmp/render.png"), help="output PNG")
    parser.add_argument("--elev", type=float, default=45.0)
    parser.add_argument("--azim", type=float, default=-90.0)
    args = parser.parse_args(argv)
    path = render(args.stl, args.out, elev=args.elev, azim=args.azim)
    fill = fill_fraction(path)
    from PIL import Image

    w, h = Image.open(path).size
    print(f"{path}  {w}x{h}  fill={fill:.0%}")
    if w < MIN_WIDTH or h < MIN_HEIGHT:
        print(f"warning: below {MIN_WIDTH}x{MIN_HEIGHT}")
    if fill < 0.8:
        print(f"warning: fill {fill:.0%} < 80% (try a different --elev/--azim)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
