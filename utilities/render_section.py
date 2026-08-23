"""Render debug cutaway/section views of the case at a named connector.

Convenience tool for visually inspecting features that are hard to verify
from bare numbers — a shell connector cutout, or how a component's own
modeled connector geometry lines up with it once assembled. Slices away the
chunk of material nearest the connector along the plane that best reveals
its bore (perpendicular to the wall it exits through), and renders the
remainder with VTK (shading conventions match ``render_stl.py``), with the
specific feature of interest drawn as a second, highlight-colored actor in
the same scene — so there is no ambiguity about which shape is which.

Two modes:

``case-cutout``
    Case shell only. Highlights the exact solid ``geometry.cutouts`` bores
    out of the shell for that connector (``cutout_tool`` — the same geometry
    actually subtracted at build time, not a re-derivation).

``component-slot``
    Case shell plus the named component, placed. Highlights the connector's
    own modeled envelope (``connector.width`` x ``connector.depth`` x
    ``connector.height``, positioned and oriented exactly as
    ``Component.build()`` places its connector socket) so you can see how
    the physical part's slot lines up with the shell opening.

Requires CadQuery (source the miniforge env first).

Usage::

    python utilities/render_section.py case-cutout sbc MicroSD -o /tmp/sbc_microsd_cutout.png
    python utilities/render_section.py component-slot sbc MicroSD -o /tmp/sbc_microsd_slot.png
    python utilities/render_section.py case-cutout usb_breakout USB-A --index 3 -o /tmp/hub_usba_east.png

    # Omit the connector (or pass "all") for every port on the component at once.
    python utilities/render_section.py case-cutout usb_breakout -o /tmp/hub_all_cutouts.png
    python utilities/render_section.py component-slot usb_breakout all -o /tmp/hub_all_slots.png
"""

from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

#: Half-width (mm) of the local chunk of case kept around the connector, on
#: each horizontal axis — big enough to show the wall corner and a bit of
#: the floor for context, small enough that the cutout itself dominates the
#: frame rather than getting lost in the full tray.
_WINDOW_HALF = 30.0

#: Shading colors (0-1 RGB, matches render_stl.py's palette conventions).
_SHELL_COLOR = (0.78, 0.79, 0.82)  # cool light gray
_COMPONENT_COLOR = (0.55, 0.62, 0.58)  # muted green-gray, distinct from the shell
_HIGHLIGHT_COLOR = (0.85, 0.20, 0.15)  # bright red


def _build_pipeline(config_path: str, layout_name: str):
    from main import BuildPipeline

    pipeline = BuildPipeline(config_path=config_path, layout_name=layout_name)
    cfg = pipeline.load_config()
    components = pipeline.load_components()
    layout = pipeline.place_layout(components)
    placements = layout.placements()
    return cfg, components, placements


def _find_placement(placements, role_component) -> object:
    for placement in placements:
        if placement.component is role_component:
            return placement
    raise ValueError(f"component {role_component!r} has no placement")


def _find_connector(component, connector_type: str, index: int = 0):
    matches = [c for c in component.connectors() if c.type == connector_type]
    if not matches:
        available = sorted({c.type for c in component.connectors()})
        raise ValueError(
            f"{component.name!r} has no {connector_type!r} connector; available: {available}"
        )
    if len(matches) > 1:
        listing = ", ".join(
            f"[{i}] at ({c.x:.1f},{c.y:.1f}) facing {c.direction}" for i, c in enumerate(matches)
        )
        print(
            f"note: {len(matches)} {connector_type!r} connectors on {component.name!r} — "
            f"using index {index}: {listing}",
            file=sys.stderr,
        )
    if index >= len(matches):
        raise ValueError(f"index {index} out of range: only {len(matches)} {connector_type!r} connectors")
    return matches[index]


def _select_connectors(component, connector_type: str | None, index: int = 0) -> list:
    """Return the connector(s) to render: one match, or every connector.

    ``connector_type`` of ``None`` (or the literal ``"all"``) selects every
    connector the component declares — used for an "all the ports" overview
    render — instead of the usual single named + indexed match.
    """
    if connector_type is None or connector_type.lower() == "all":
        return list(component.connectors())
    return [_find_connector(component, connector_type, index)]


def _mean_direction(directions: list[tuple[float, float, float]]) -> tuple[float, float, float]:
    """Average several unit direction vectors (for a multi-port default view)."""
    import math

    sx = sum(d[0] for d in directions)
    sy = sum(d[1] for d in directions)
    sz = sum(d[2] for d in directions)
    mag = math.sqrt(sx * sx + sy * sy + sz * sz)
    if mag < 1e-6:
        return directions[0]
    return (sx / mag, sy / mag, sz / mag)


def _component_solid(placement):
    """Return a component's solid transformed to its world placement."""
    from utilities import cq_helpers

    solid = placement.component.build()
    if placement.rotation:
        solid = cq_helpers.rotate_z(solid, placement.rotation)
    if placement.flip_x:
        solid = cq_helpers.rotate_x(solid, 180.0)
    return cq_helpers.translate(solid, placement.x, placement.y, placement.z)


def _connector_slot_solid(placement, connector):
    """Return the connector's own modeled envelope, placed in world space.

    Reconstructs the box each ``Component.build()`` unions in for a boxy
    connector socket (``box_centered(connector.width, connector.depth,
    connector.height)`` centered at the connector's local position) — the
    same convention every component in this codebase follows (see e.g.
    ``OrangePiZero2W.build()``'s socket list) — then carries it through the
    placement's rotation/flip/translate, exactly like ``_component_solid``.
    """
    from utilities import cq_helpers

    box = cq_helpers.box_centered(connector.width, connector.depth, connector.height)
    box = cq_helpers.translate(box, connector.x, connector.y, connector.z)
    if placement.rotation:
        box = cq_helpers.rotate_z(box, placement.rotation)
    if placement.flip_x:
        box = cq_helpers.rotate_x(box, 180.0)
    return cq_helpers.translate(box, placement.x, placement.y, placement.z)


def _keep_box(bbox, cx: float, cy: float, window_half: float, z_pad: float = 5.0):
    """A local window box centered on the connector, full case height.

    Kept as a small chunk around ``(cx, cy)`` (the wall corner plus a bit of
    floor) rather than one half of the whole case, so the cutout dominates
    the frame instead of getting lost in the full tray.
    """
    from utilities import cq_helpers

    x0, x1 = cx - window_half, cx + window_half
    y0, y1 = cy - window_half, cy + window_half
    z0, z1 = bbox.zmin - z_pad, bbox.zmax + z_pad
    box = cq_helpers.box_centered(x1 - x0, y1 - y0, z1 - z0)
    return cq_helpers.translate(box, (x0 + x1) / 2.0, (y0 + y1) / 2.0, (z0 + z1) / 2.0)


def _keep_box_multi(bbox, xs: list[float], ys: list[float], margin: float, z_pad: float = 5.0):
    """A window box spanning every point in ``xs``/``ys`` plus ``margin``.

    Generalizes :func:`_keep_box` to several connectors at once (e.g. "every
    port on this component") — kept region is their combined footprint, not
    a fixed radius around one point.
    """
    from utilities import cq_helpers

    x0, x1 = min(xs) - margin, max(xs) + margin
    y0, y1 = min(ys) - margin, max(ys) + margin
    z0, z1 = bbox.zmin - z_pad, bbox.zmax + z_pad
    box = cq_helpers.box_centered(x1 - x0, y1 - y0, z1 - z0)
    return cq_helpers.translate(box, (x0 + x1) / 2.0, (y0 + y1) / 2.0, (z0 + z1) / 2.0)


def _default_view(direction: tuple[float, float, float], twist: float = 35.0) -> tuple[float, float]:
    """Camera (elev, azim) that looks in from outside the connector's wall.

    ``azim`` points the camera along the connector's own outward direction
    (matching ``render_stl``'s position = center + dist*(cosE cosA, cosE
    sinA, sinE) convention), offset by ``twist`` degrees for a 3/4 view
    instead of a flat face-on one.
    """
    import math

    dx, dy, _dz = direction
    azim = math.degrees(math.atan2(dy, dx)) + twist
    return 28.0, azim


def _export_stl(shape, path: Path) -> Path:
    from utilities import cq_helpers

    cq = cq_helpers.require_cq()
    cq.exporters.export(shape, str(path), exportType="STL")
    return path


def _render_scene(actors_and_colors, out_path: Path, elev: float, azim: float) -> Path:
    """Render several (stl_path, rgb_color) actors into one shaded PNG.

    Camera/lighting recipe mirrors ``render_stl.render`` (fixed world-space
    key/fill/rim lights, parallel projection fitted to the combined bounds)
    so debug section renders read consistently with the plain part renders.
    """
    import math

    import vtk

    renderer = vtk.vtkRenderer()
    renderer.SetBackground(1.0, 1.0, 1.0)

    all_bounds = None
    for stl_path, color in actors_and_colors:
        reader = vtk.vtkSTLReader()
        reader.SetFileName(str(stl_path))
        reader.Update()
        mapper = vtk.vtkPolyDataMapper()
        mapper.SetInputConnection(reader.GetOutputPort())
        actor = vtk.vtkActor()
        actor.SetMapper(mapper)
        prop = actor.GetProperty()
        prop.SetColor(*color)
        prop.SetInterpolationToPhong()
        prop.SetDiffuse(0.8)
        prop.SetAmbient(0.3)
        prop.SetSpecular(0.2)
        prop.SetSpecularPower(20.0)
        renderer.AddActor(actor)

        b = reader.GetOutput().GetBounds()
        all_bounds = b if all_bounds is None else tuple(
            (min if i % 2 == 0 else max)(all_bounds[i], b[i]) for i in range(6)
        )

    for pos, intensity, diffuse in (
        ((-0.5, -0.4, 0.75), 0.9, (1.0, 0.99, 0.96)),
        ((0.6, -0.3, 0.4), 0.35, (0.92, 0.94, 1.0)),
        ((0.2, 0.7, -0.4), 0.2, (0.95, 0.96, 1.0)),
    ):
        light = vtk.vtkLight()
        light.SetPositional(0)
        light.SetPosition(*pos)
        light.SetFocalPoint(0.0, 0.0, 0.0)
        light.SetIntensity(intensity)
        light.SetDiffuseColor(*diffuse)
        renderer.AddLight(light)

    center = [(all_bounds[i] + all_bounds[i + 1]) / 2.0 for i in (0, 2, 4)]
    cam = renderer.GetActiveCamera()
    cam.SetFocalPoint(*center)
    a, e = math.radians(azim), math.radians(elev)
    dist = 3.0 * math.sqrt(sum((all_bounds[2 * i + 1] - all_bounds[2 * i]) ** 2 for i in range(3)))
    cam.SetPosition(
        center[0] + dist * math.cos(e) * math.cos(a),
        center[1] + dist * math.cos(e) * math.sin(a),
        center[2] + dist * math.sin(e),
    )
    cam.SetViewUp(0.0, 0.0, 1.0)
    cam.ParallelProjectionOn()
    renderer.ResetCamera()
    renderer.ResetCameraClippingRange()

    window = vtk.vtkRenderWindow()
    window.SetSize(1920, 1080)
    window.SetOffScreenRendering(1)
    window.SetMultiSamples(8)
    window.AddRenderer(renderer)
    window.Render()

    image = vtk.vtkWindowToImageFilter()
    image.SetInput(window)
    image.SetInputBufferTypeToRGBA()
    image.ReadFrontBufferOff()
    image.Update()

    out_path = out_path.with_suffix(".png")
    writer = vtk.vtkPNGWriter()
    writer.SetFileName(str(out_path))
    writer.SetInputConnection(image.GetOutputPort())
    writer.Write()
    window.Finalize()

    from utilities.render_stl import _crop_to_fit

    _crop_to_fit(out_path, margin_frac=0.06)
    return out_path


def _cutouts_for(assy, placement, connectors, component_role: str, connector_type: str | None):
    """Return ``(connector, cutout)`` pairs for every connector that produces one."""
    pairs = []
    for connector in connectors:
        cutout = assy.connector_cutout(placement, connector)
        if cutout is not None:
            pairs.append((connector, cutout))
    if not pairs:
        label = connector_type or "any"
        raise ValueError(
            f"{component_role}.{label} produces no shell cutout(s) "
            "(internal connector, or out of reach of any wall)"
        )
    return pairs


def render_case_cutout(
    component_role: str,
    connector_type: str | None,
    out_path: Path,
    config_path: str = "config/default.yaml",
    layout_name: str = "compact",
    elev: float | None = None,
    azim: float | None = None,
    index: int = 0,
) -> Path:
    """Cutaway of the case shell alone, with one or all connector cutouts highlighted.

    ``connector_type=None`` (or ``"all"``) selects every cutout-producing
    connector on the component — an overview of all its ports at once.
    """
    from assemblies.assembly import Assembly
    from case.base import Base
    from geometry.cutouts import cutout_tool
    from utilities import cq_helpers

    cfg, components, placements = _build_pipeline(config_path, layout_name)
    assy = Assembly(placements, cfg)
    component = components[component_role]
    placement = _find_placement(placements, component)
    connectors = _select_connectors(component, connector_type, index)
    pairs = _cutouts_for(assy, placement, connectors, component_role, connector_type)
    cutouts = [c for _connector, c in pairs]

    base = Base(assy, cfg, keyboard=components["keyboard"])
    shell = base.build_bottom()
    highlights = [
        cutout_tool(c, cfg.wall_thickness, chamfer=cfg.corners.cutout_chamfer) for c in cutouts
    ]

    bbox = shell.val().BoundingBox()
    xs, ys = [c["x"] for c in cutouts], [c["y"] for c in cutouts]
    keep_box = (
        _keep_box(bbox, xs[0], ys[0], _WINDOW_HALF)
        if len(cutouts) == 1
        else _keep_box_multi(bbox, xs, ys, _WINDOW_HALF)
    )
    shell_cut = shell.intersect(keep_box)
    highlight_cut = cq_helpers.make_compound([h.intersect(keep_box) for h in highlights])
    if elev is None or azim is None:
        default_elev, default_azim = _default_view(_mean_direction([c["direction"] for c in cutouts]))
        elev = default_elev if elev is None else elev
        azim = default_azim if azim is None else azim

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        shell_stl = _export_stl(shell_cut, tmp / "shell.stl")
        highlight_stl = _export_stl(highlight_cut, tmp / "highlight.stl")
        return _render_scene(
            [(shell_stl, _SHELL_COLOR), (highlight_stl, _HIGHLIGHT_COLOR)],
            out_path, elev, azim,
        )


def render_component_slot(
    component_role: str,
    connector_type: str | None,
    out_path: Path,
    config_path: str = "config/default.yaml",
    layout_name: str = "compact",
    elev: float | None = None,
    azim: float | None = None,
    index: int = 0,
) -> Path:
    """Cutaway of the case shell + the named component, one or all slots highlighted.

    ``connector_type=None`` (or ``"all"``) selects every cutout-producing
    connector on the component — an overview of all its ports at once.
    """
    from assemblies.assembly import Assembly
    from case.base import Base
    from utilities import cq_helpers

    cfg, components, placements = _build_pipeline(config_path, layout_name)
    assy = Assembly(placements, cfg)
    component = components[component_role]
    placement = _find_placement(placements, component)
    connectors = _select_connectors(component, connector_type, index)
    pairs = _cutouts_for(assy, placement, connectors, component_role, connector_type)
    cutouts = [c for _connector, c in pairs]

    base = Base(assy, cfg, keyboard=components["keyboard"])
    shell = base.build_bottom()
    component_solid = _component_solid(placement)
    highlights = [_connector_slot_solid(placement, connector) for connector, _c in pairs]

    bbox = shell.val().BoundingBox()
    xs, ys = [c["x"] for c in cutouts], [c["y"] for c in cutouts]
    keep_box = (
        _keep_box(bbox, xs[0], ys[0], _WINDOW_HALF)
        if len(cutouts) == 1
        else _keep_box_multi(bbox, xs, ys, _WINDOW_HALF)
    )
    shell_cut = shell.intersect(keep_box)
    component_cut = component_solid.intersect(keep_box)
    highlight_cut = cq_helpers.make_compound([h.intersect(keep_box) for h in highlights])
    if elev is None or azim is None:
        default_elev, default_azim = _default_view(_mean_direction([c["direction"] for c in cutouts]))
        elev = default_elev if elev is None else elev
        azim = default_azim if azim is None else azim

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        shell_stl = _export_stl(shell_cut, tmp / "shell.stl")
        component_stl = _export_stl(component_cut, tmp / "component.stl")
        highlight_stl = _export_stl(highlight_cut, tmp / "highlight.stl")
        return _render_scene(
            [
                (shell_stl, _SHELL_COLOR),
                (component_stl, _COMPONENT_COLOR),
                (highlight_stl, _HIGHLIGHT_COLOR),
            ],
            out_path, elev, azim,
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("mode", choices=["case-cutout", "component-slot"])
    parser.add_argument("component", help="component role key, e.g. sbc, usb_breakout")
    parser.add_argument(
        "connector", nargs="?", default=None,
        help="connector type, e.g. MicroSD, USB-A, Power. Omit (or pass 'all') for every port on the component",
    )
    parser.add_argument("-o", "--out", type=Path, default=Path("/tmp/section.png"))
    parser.add_argument("--config", default="config/default.yaml")
    parser.add_argument("--layout", default="compact")
    parser.add_argument("--elev", type=float, default=None, help="default: auto, facing the connector's wall")
    parser.add_argument("--azim", type=float, default=None, help="default: auto, facing the connector's wall")
    parser.add_argument(
        "--index", type=int, default=0,
        help="which matching connector to use when a component has more than one of the same type (default: 0)",
    )
    args = parser.parse_args(argv)

    fn = render_case_cutout if args.mode == "case-cutout" else render_component_slot
    path = fn(
        args.component, args.connector, args.out,
        config_path=args.config, layout_name=args.layout,
        elev=args.elev, azim=args.azim, index=args.index,
    )
    print(f"{path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
