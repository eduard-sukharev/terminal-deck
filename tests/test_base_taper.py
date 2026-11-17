"""The Tray's end-wall base taper (ADR-0019).

The Tray's X walls are vertical (the accessory rail's face) and its front/rear
walls are vertical too, but they leave the table with a 15 degree base taper
that runs up to the joint band and dies into a pad around every band station.
The taper is a draft: the cavity follows the outer face, so the wall keeps its
thickness. These tests pin the pure data (height, inset, pad, stop, the runs
of full taper) and the solid (both faces on the data's lines, the wall's
thickness preserved, the pads swallowing the columns).
"""

import math

import pytest

from case.chassis import Chassis
from case.slider_frame import SliderFrame
from components.slide import compute_slide_budget
from geometry.base_taper import base_taper, build_cutter, build_fill
from layouts import make_layout
from main import BuildPipeline
from utilities import cad_helpers as ch


@pytest.fixture(scope="module")
def data():
    pipeline = BuildPipeline("config/default.yaml", layout_name="slider")
    config = pipeline.load_config()
    components = pipeline.load_components()
    placements = make_layout("slider", components, config=config).placements()
    budget = compute_slide_budget(config, components)
    frame = SliderFrame.from_data(config, budget, components, placements)
    return config, budget, frame, placements


@pytest.fixture(scope="module")
def tray(data):
    config, _, frame, _ = data
    return Chassis(config, frame).build_tray()


def _material_at(shape, x, y, z, size=0.4):
    probe = ch.translate(ch.box_centered(size, size, size), x, y, z)
    return ch.volume_mm3(ch.intersect(shape, probe))


def _width_at(shape, z):
    slab = ch.translate(ch.box_centered(1000.0, 1000.0, 0.01), 0.0, 0.0, z)
    return ch.bounding_box_mm(ch.intersect(shape, slab))[0]


# -- data ----------------------------------------------------------------
def test_the_taper_runs_from_the_table_to_the_band(data):
    config, budget, _, _ = data
    taper = budget.base_taper
    joint = budget.chassis_joint
    assert taper.angle == pytest.approx(config.chassis_joint.taper_angle)
    # "Taper + band": the taper runs from the table up to the band's bottom,
    # so it stops one half-band (3 mm) below the Parting plane.
    assert taper.height == pytest.approx(joint.band_z0)
    assert joint.parting_z - taper.height == pytest.approx(joint.band / 2.0)
    assert taper.inset == pytest.approx(
        math.tan(math.radians(taper.angle)) * taper.height
    )
    # The base is a couple of millimetres deeper than a chamfer-scale taper:
    # the wall is drafted, not trimmed, so the inset may pass the wall.
    assert taper.inset > config.wall_thickness


def test_the_taper_is_a_draft_the_cavity_follows(data):
    _, budget, _, _ = data
    taper = budget.base_taper
    # The inner face runs on the same line, one wall further in, over the same
    # height -- so the wall keeps its thickness everywhere on the taper.
    for z in (0.0, taper.wall, taper.height / 2.0, taper.height):
        assert taper.inner_face_y(z) == pytest.approx(
            taper.face_y(z) - taper.wall
        )
    assert taper.inner_face_y(taper.height) == pytest.approx(
        taper.half_depth - taper.wall
    )


def test_the_pads_keep_the_head_recesses_their_ring(data):
    config, budget, _, _ = data
    taper = budget.base_taper
    joint = budget.chassis_joint
    minimum = config.material.minimum_feature
    wall_y = taper.half_depth - joint.side_inset
    wall_stations = [
        s for s in joint.stations if abs(abs(s.y) - wall_y) < 1e-9
    ]
    assert len(wall_stations) == 10
    # The pad stops the taper before the access cone mouth (ADR-0021).
    assert taper.pad_radius == pytest.approx(
        max(s.mouth_radius for s in wall_stations) + minimum
    )
    assert taper.stop_radius == pytest.approx(
        taper.pad_radius + config.chassis_joint.taper_runout
    )
    for station in wall_stations:
        assert (
            taper.pad_radius >= station.mouth_radius + minimum - 1e-9
        )
        # The tapered cavity would leave the station's column proud of the
        # outer face; the pad (the taper's suppression circle) must swallow it.
        assert taper.stop_radius >= station.boss / 2.0 + minimum - 1e-9
        assert taper.in_pad(station.x, station.y)
        assert taper.in_pad(station.x + taper.pad_radius, station.y)
        assert not taper.in_pad(station.x + taper.stop_radius + 0.1, station.y)


def test_the_stop_circles_leave_real_taper_runs(data):
    _, budget, _, _ = data
    taper = budget.base_taper
    assert len(taper.segments) == 4
    for x0, x1 in taper.segments:
        assert x1 - x0 > 10.0
        # Both ends sit inside the wall's straight part, not on the corner
        # chop, and every station's stop circle stays outside the run.
        assert -taper.wall_half_x < x0 < x1 < taper.wall_half_x
        for sx, _ in taper.stations:
            assert not (x0 < abs(sx) < x1)
    # The runs are symmetric about the centreline.
    assert taper.segments[0][0] == pytest.approx(-taper.segments[-1][1])
    assert taper.segments[0][1] == pytest.approx(-taper.segments[-1][0])


def test_the_face_leans_out_over_the_chamfer_only(data):
    _, budget, _, _ = data
    taper = budget.base_taper
    assert taper.inset_at(0.0) == pytest.approx(taper.inset)
    assert taper.inset_at(taper.height / 2.0) == pytest.approx(taper.inset / 2.0)
    assert taper.inset_at(taper.height) == pytest.approx(0.0)
    assert taper.inset_at(taper.height + 5.0) == pytest.approx(0.0)
    assert taper.base_depth == pytest.approx(taper.depth - 2.0 * taper.inset)


# -- solid ---------------------------------------------------------------
def test_the_cutter_removes_a_wedge_on_both_end_walls(data):
    _, budget, _, _ = data
    taper = budget.base_taper
    cutter = build_cutter(taper)
    # The wedge reaches down past the table (clean trim) and nothing above the
    # taper's top.
    box = ch.bounding_box(cutter)
    assert box.zmax == pytest.approx(taper.height, abs=0.05)
    assert box.zmin == pytest.approx(-0.2, abs=0.05)
    assert box.ymax == pytest.approx(taper.half_depth + 0.2, abs=0.05)
    assert box.ymin == pytest.approx(-taper.half_depth - 0.2, abs=0.05)


def test_the_fill_spans_the_wall_from_the_floor_to_the_taper_top(data):
    _, budget, _, _ = data
    taper = budget.base_taper
    fill = build_fill(taper)
    # The fill starts at the floor's top (it must not restore the floor edge
    # the cutter took) and ends at the taper's top, inside the nominal wall.
    box = ch.bounding_box(fill)
    assert box.zmin == pytest.approx(taper.wall, abs=0.05)
    assert box.zmax == pytest.approx(taper.height, abs=0.05)
    assert box.ymax == pytest.approx(taper.half_depth, abs=0.05)
    assert box.ymin == pytest.approx(-taper.half_depth, abs=0.05)


def test_the_tray_keeps_its_full_width_and_tapers_its_end_walls(data, tray):
    config, budget, frame, _ = data
    taper = budget.base_taper
    half = frame.depth / 2.0
    wall = taper.wall
    # The X silhouette is vertical at every height (the rail's face).
    for z in (0.5, taper.height + 0.5, frame.parting_z - 0.5):
        assert _width_at(tray, z) == pytest.approx(frame.width, abs=0.05)
    # Between the pads both faces sit on the data's lines, and the wall keeps
    # its thickness between them -- the draft, not a thinning chamfer.
    x = sum(taper.segments[1]) / 2.0
    for z in (0.5, taper.wall + 0.5, taper.height / 2.0, taper.height - 0.5):
        face = taper.face_y(z)
        # The built outer face sits on the data's line to within a probe's
        # width, from the table to the taper's top.
        assert _material_at(tray, x, face - 0.15, z, 0.2) > 0
        assert _material_at(tray, x, face + 0.15, z, 0.2) == pytest.approx(0)
    for z in (taper.wall + 0.5, taper.height / 2.0, taper.height - 0.5):
        face = taper.face_y(z)
        inner = taper.inner_face_y(z)
        # Above the floor the cavity follows the same line, one wall in, and
        # the wall between the faces is solid: the thickness never thins.
        assert _material_at(tray, x, inner - 0.15, z, 0.2) == pytest.approx(0)
        assert _material_at(tray, x, inner + 0.15, z, 0.2) > 0
        assert _material_at(tray, x, (face + inner) / 2.0, z, 0.6) > 0
    # Above the taper the full depth is back, on both faces.
    assert _material_at(tray, x, half - 0.4, taper.height + 0.5) > 0
    assert _material_at(tray, x, half - wall - 0.4, taper.height + 0.5) == 0
    # Inside a pad the face is at the full depth even at the base.
    station = next(
        s
        for s in budget.chassis_joint.stations
        if abs(abs(s.y) - (half - budget.chassis_joint.side_inset)) < 1e-9
    )
    assert _material_at(tray, station.x, half - 0.4, taper.height / 2.0) > 0
