"""The Tray's end-wall base taper (ADR-0019, ADR-0027).

The Tray's X walls are vertical (the accessory rail's face) and its front/rear
walls are vertical too, but they leave the table at the band stations' axes --
the face at the table is inset by `side_inset`, so it passes through the
long-wall screws' axes -- and runs up to the joint band. The taper is a draft:
the cavity follows the outer face, so the wall keeps its thickness. These tests
pin the pure data (height, inset, angle, pad, stop, the runs of full taper) and
the solid (both faces on the data's lines, the wall's thickness preserved, the
pads swallowing the columns).
"""

import math

import pytest

from case.chassis import Chassis
from case.slider_frame import SliderFrame
from components.slide import compute_slide_budget
from geometry.base_taper import (
    base_taper,
    build_cutter,
    build_fill,
    cone_lip_z,
    lip_chamfer_limit,
)
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
    # ADR-0027: the reach at the table is the stations' own axis distance, and
    # the angle off vertical follows from it over the taper's height.
    assert taper.inset == pytest.approx(joint.side_inset)
    assert taper.angle == pytest.approx(
        math.degrees(math.atan2(taper.inset, taper.height))
    )
    # "Taper + band": the taper runs from the table up to the band's bottom,
    # so it stops one half-band (3 mm) below the Parting plane.
    assert taper.height == pytest.approx(joint.band_z0)
    assert joint.parting_z - taper.height == pytest.approx(joint.band / 2.0)
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
    corners = [s for s in wall_stations if s.is_corner]
    assert len(wall_stations) == 10
    assert len(corners) == 4
    # ADR-0022: only the corners carry a pad; the side stations are through.
    assert len(taper.stations) == 4
    # The pad stops the taper before the access cone mouth (ADR-0021).
    assert taper.pad_radius == pytest.approx(
        max(s.mouth_radius for s in corners) + minimum
    )
    assert taper.stop_radius == pytest.approx(
        taper.pad_radius + config.chassis_joint.taper_runout
    )
    for station in corners:
        assert taper.pad_radius >= station.mouth_radius + minimum - 1e-9
        # The pad must swallow the station's column.
        assert taper.stop_radius >= station.boss / 2.0 + minimum - 1e-9
        assert taper.in_pad(station.x, station.y)
        assert taper.in_pad(station.x + taper.pad_radius, station.y)
        assert not taper.in_pad(station.x + taper.stop_radius + 0.1, station.y)
    for station in wall_stations:
        if station.is_corner:
            continue
        # The taper passes through: no pad, no suppression circle.
        assert not taper.in_pad(station.x, station.y)


def test_the_taper_opens_through_the_side_stations(data):
    """ADR-0027: at the table the taper face reaches the stations' axes."""
    config, budget, _, _ = data
    taper = budget.base_taper
    joint = budget.chassis_joint
    minimum = config.material.minimum_feature
    wall_y = taper.half_depth - joint.side_inset
    for station in joint.stations:
        if abs(abs(station.y) - wall_y) > 1e-9 or station.is_corner:
            continue
        # The face at the table passes through the axis: the outboard half of
        # the cone mouth is cut away, the inboard half remains as the rim.
        assert station.margin - taper.inset == pytest.approx(0.0)
        # The pocket's pier survives: the ring at the taper's top only grows
        # with height, so its minimum over the taper is at the top.
        assert station.margin - joint.recess.pocket_radius >= 2.0 * minimum


def test_the_stop_circles_leave_real_taper_runs(data):
    _, budget, _, _ = data
    taper = budget.base_taper
    # ADR-0022: only the corner pads stop the taper, so each wall is a single
    # full-width run between the corner pads' stops.
    assert len(taper.segments) == 1
    for x0, x1 in taper.segments:
        assert x1 - x0 > 10.0
        # Both ends sit inside the wall's straight part, not on the corner
        # chop, and every pad's stop circle stays outside the run.
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
    # the cutter took) and ends at the taper's top. It reaches the prismatic
    # cavity face (one wall inside the Tray's outer depth), never the outer
    # face: it restores the cavity side of the draft only.
    box = ch.bounding_box(fill)
    assert box.zmin == pytest.approx(taper.wall, abs=0.05)
    assert box.zmax == pytest.approx(taper.height, abs=0.05)
    assert box.ymax == pytest.approx(taper.half_depth - taper.wall, abs=0.05)
    assert box.ymin == pytest.approx(-(taper.half_depth - taper.wall), abs=0.05)
    # Mid-run the wedge reaches the cavity face: from the drafted inner line
    # out to the prismatic cavity plane, at every height below the crossing.
    for z in (taper.wall + 0.5, taper.height / 2.0):
        y = taper.inner_face_y(z) + taper.wall / 2.0
        assert _material_at(fill, 70.0, y, z) > 0
        assert _material_at(
            fill, 70.0, taper.half_depth - taper.wall - 0.15, z
        ) > 0


def test_the_fill_bridges_the_corner_pads(data):
    _, budget, _, _ = data
    taper = budget.base_taper
    fill = build_fill(taper)
    # The fill is NOT clipped on the pads: it reaches the prismatic cavity face
    # everywhere, so inside a pad it meets the shell (which keeps the full face
    # because the pad suppresses the cutter) and the two fuse into one wall.
    # Clipping it here was what opened a full-height slot between the drafted
    # run and the pad -- the rectangular notch beside the corner boss.
    cavity_face = taper.half_depth - taper.wall
    for x, _ in taper.stations:
        # A point in the pad, one wall inside the pad's full face.
        assert _material_at(fill, x, cavity_face - 0.4, taper.height / 2.0) > 0


def test_the_tray_keeps_its_full_width_and_tapers_its_end_walls(data, tray):
    config, budget, frame, _ = data
    taper = budget.base_taper
    half = frame.depth / 2.0
    wall = taper.wall
    # The X silhouette is vertical at every height (the rail's face).
    for z in (0.5, taper.height + 0.5, frame.parting_z - 0.5):
        assert _width_at(tray, z) == pytest.approx(frame.width, abs=0.05)
    # Between the corner pads both faces sit on the data's lines, and the wall
    # keeps its thickness between them -- the draft, not a thinning chamfer.
    # The probe sits mid-run, clear of the side stations' cones (the taper
    # passes through them now).
    joint = budget.chassis_joint
    wall_y = taper.half_depth - joint.side_inset
    side_xs = [
        abs(s.x)
        for s in joint.stations
        if abs(abs(s.y) - wall_y) < 1e-9 and not s.is_corner
    ]
    x = (max(side_xs) + taper.segments[0][1]) / 2.0
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
    # At a through-station the taper opens into the cone: no pier ring is left
    # at the table, the opening flares straight into the cavity.
    side = next(
        s
        for s in joint.stations
        if abs(abs(s.y) - wall_y) < 1e-9 and not s.is_corner
    )
    sy = math.copysign(half - 0.4, side.y)
    assert _material_at(
        tray, side.x, sy, taper.height / 2.0
    ) == pytest.approx(0)
    # ...while the head pocket's pier is intact just below the band.
    assert _material_at(
        tray, side.x, sy, taper.height - 0.05
    ) > 0
    # Inside a corner pad the face is at the full depth even at the base.
    corner = next(
        s
        for s in joint.stations
        if abs(abs(s.y) - wall_y) < 1e-9 and s.is_corner
    )
    cy = math.copysign(half - 0.4, corner.y)
    assert _material_at(tray, corner.x, cy, taper.height / 2.0) > 0


def test_the_tray_wall_is_unbroken_at_the_corner_pad_shoulder(data, tray):
    """No slot between the drafted run and the corner pad (the old notch)."""
    _, budget, _, _ = data
    taper = budget.base_taper
    # Walk the shoulder across each corner pad: just outside its stop circle,
    # on it, and just inside it. The wall's whole thickness is solid all the
    # way -- the fill bridges the lateral offset between the drafted panel and
    # the pad, so the wall is one piece. Clipping the fill at the pad instead
    # opened a full-height air slot here: the rectangular notch beside the
    # corner boss.
    for z in (taper.wall + 0.5, taper.height / 2.0):
        mid = (taper.inner_face_y(z) + taper.face_y(z)) / 2.0
        for sx, sy in taper.stations:
            y = math.copysign(mid, sy)
            for off in (-0.6, 0.0, 0.4):
                x = sx - math.copysign(taper.stop_radius - off, sx)
                assert _material_at(tray, x, y, z, 0.3) > 0, (x, y, z)


# -- ADR-0025 / ADR-0027: the cone edges take the chamfer ------------------
def test_through_stations_are_the_wall_stations_without_corners(data):
    _, budget, _, _ = data
    taper = budget.base_taper
    joint = budget.chassis_joint
    wall = taper.wall_stations(joint)
    through = taper.through_stations(joint)
    assert len(wall) == 10 and len(through) == 6
    assert not any(s.is_corner for s in through)
    assert {s for s in wall if s.is_corner} == set(wall) - set(through)


def test_the_lip_sits_between_the_table_and_the_pocket_neck(data):
    _, budget, _, _ = data
    taper = budget.base_taper
    joint = budget.chassis_joint
    for station in taper.through_stations(joint):
        z_lip = cone_lip_z(
            taper, joint.recess, station.mouth_radius, station.margin
        )
        # Reaching the station axes pushes the lip up to ~9.1 mm, but it stays
        # well below the pocket's neck.
        assert 0.0 < z_lip < joint.recess.z_neck


def test_the_lip_leaves_room_for_the_bed_chamfer(data):
    config, budget, _, _ = data
    taper = budget.base_taper
    joint = budget.chassis_joint
    chamfer = config.edges.bed_chamfer
    for station in taper.through_stations(joint):
        limit = lip_chamfer_limit(
            taper,
            joint.recess,
            station.mouth_radius,
            station.margin,
            config.material.minimum_feature,
        )
        # The 45 degree chamfer runs about its leg up the lip, so the limit is
        # the room left below the pocket's neck minus one minimum feature.
        assert limit >= chamfer
        assert limit == pytest.approx(
            joint.recess.z_neck
            - config.material.minimum_feature
            - cone_lip_z(
                taper, joint.recess, station.mouth_radius, station.margin
            )
        )
