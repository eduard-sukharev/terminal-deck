"""The printed accessory rail and its washer pucks (ADR-0020).

Two kinds of assertion: the station features the Tray cuts (a pad per M4
station, a square pocket for the puck and a clearance bore through the wall,
braced by 45 degree gussets) and the two printed parts themselves. The rail is
a **blank** for now -- the picatinny profile comes later -- so what is pinned is
the interface: the width across the wall, the counterbored M4 holes on the
bridge centres, and the puck's nut pocket.
"""

import pytest

from case.chassis import Chassis
from case.slider_frame import SliderFrame
from components.accessory_rail import (
    build_rail,
    build_rail_washer,
    place_rail,
    place_rail_washer,
)
from components.slide import compute_slide_budget
from geometry.rail_mounts import rail_mounts
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
    return config, budget, frame


@pytest.fixture(scope="module")
def mounts(data):
    config, budget, _ = data
    return rail_mounts(config, budget.chassis_joint)


@pytest.fixture(scope="module")
def tray(data):
    config, _, frame = data
    return Chassis(config, frame).build_tray()


@pytest.fixture(scope="module")
def rail(mounts):
    return build_rail(mounts)


@pytest.fixture(scope="module")
def washer(mounts):
    return build_rail_washer(mounts)


def _material_at(shape, x, y, z, size=0.4):
    probe = ch.translate(ch.box_centered(size, size, size), x, y, z)
    return ch.volume_mm3(ch.intersect(shape, probe))


# ── The Tray's station features ────────────────────────────────────────


def test_each_station_has_a_solid_pad_inside_its_pocket_ring(mounts, tray):
    for station in mounts.stations:
        x = station.side * (station.x_pad_in + 0.15)
        y = station.y + station.pocket_side / 2.0 + 0.2
        assert _material_at(tray, x, y, station.z, size=0.2) > 0.0
        # The pad runs from the floor to the Parting plane.
        assert _material_at(tray, x, y, 0.5 * (mounts.wall + station.z)) > 0.0
        top = station.z + station.pocket_side / 2.0 + 0.5
        assert _material_at(tray, x, y, top, size=0.2) > 0.0


def test_the_pocket_is_open_for_the_puck(mounts, tray):
    for station in mounts.stations:
        x = station.side * station.x_pad_in + station.side * 0.4
        assert _material_at(tray, x, station.y, station.z, size=0.2) == pytest.approx(0)
        # The pocket's floor behind the puck is solid -- probed off the screw
        # axis, where the M4 bore runs.
        floor = station.side * (station.pocket_floor + 0.15)
        off_axis = station.y + station.pocket_side / 4.0
        assert _material_at(tray, floor, off_axis, station.z, size=0.2) > 0.0


def test_the_m4_bore_runs_through_the_wall(mounts, tray):
    for station in mounts.stations:
        for depth in (0.5, 1.0, 1.5):
            x = station.side * (station.pocket_floor + depth * mounts.wall / 2.0)
            assert _material_at(tray, x, station.y, station.z, size=0.25) == pytest.approx(
                0
            )


def test_the_gussets_reach_the_floor_and_stop_at_their_run(data, mounts, tray):
    config, _, _ = data
    minimum = config.material.minimum_feature
    station = mounts.stations[0]
    run = station.gusset_run
    x = station.side * (station.x_pad_in + station.pad_depth / 2.0)
    edge = station.y + station.pad_width / 2.0
    z = config.wall_thickness + minimum + 0.3
    # On the slope, one minimum feature above the floor, the rib is solid.
    assert _material_at(tray, x, edge + 0.5 * run, z) > 0.0
    # Past the tip it is the plain wall again (the band column starts 1.2 mm
    # further out, so the probe stops short of it).
    assert (
        _material_at(tray, x, edge + run - minimum + 0.3, z, size=0.2)
        == pytest.approx(0)
    )


def test_the_tray_still_stops_at_the_parting_plane(data, mounts, tray):
    _, budget, _ = data
    bounds = ch.bounding_box_mm(tray)
    assert bounds[2] == pytest.approx(budget.chassis_joint.parting_z, abs=1e-6)


# ── The printed rail blank ─────────────────────────────────────────────


def test_the_rail_is_the_configured_blank(mounts, rail):
    thickness, length, across = ch.bounding_box_mm(rail)
    assert thickness == pytest.approx(mounts.height)
    assert length == pytest.approx(mounts.length)
    assert across == pytest.approx(mounts.width)


def test_the_rail_holes_are_on_the_station_offsets(mounts, rail):
    for offset in mounts.station_offsets:
        # Clearance bore through the blank.
        assert _material_at(rail, 0.0, offset, 0.0, size=0.25) == pytest.approx(0)
        # Counterbore behind the head, on the outer face.
        depth = mounts.head_recess.depth
        pocket_x = mounts.height / 2.0 - depth / 2.0
        assert _material_at(rail, pocket_x, offset, 0.0, size=0.25) == pytest.approx(0)
        # The web under the head is intact.
        web_x = mounts.height / 2.0 - depth - 0.15
        assert _material_at(rail, web_x, offset + mounts.head_recess.pocket_diameter / 2.0 + 0.3, 0.0) > 0.0


def test_the_rail_overhangs_the_wall_by_half_its_width(mounts):
    assert mounts.width > mounts.wall
    assert (mounts.width - mounts.wall) / 2.0 == pytest.approx(9.6)


def test_the_placed_rail_sits_against_the_wall(mounts):
    for side in (-1, 1):
        box = ch.bounding_box(place_rail(mounts, side))
        near = box.xmin if side > 0 else -box.xmax
        far = box.xmax if side > 0 else -box.xmin
        assert near == pytest.approx(mounts.x_outer, abs=1e-6)
        assert far == pytest.approx(mounts.x_outer + mounts.height, abs=1e-6)
        assert box.zmin == pytest.approx(mounts.stations[0].z - mounts.width / 2.0)
        assert box.zmax == pytest.approx(mounts.stations[0].z + mounts.width / 2.0)


# ── The printed washer puck ────────────────────────────────────────────


def test_the_puck_is_a_square_washer(mounts, washer):
    thickness, across, tall = ch.bounding_box_mm(washer)
    assert thickness == pytest.approx(mounts.puck_thickness)
    assert across == pytest.approx(mounts.puck_width)
    assert tall == pytest.approx(mounts.puck_width)
    box = ch.bounding_box(washer)
    assert box.xmin == pytest.approx(0.0, abs=1e-6)
    assert box.xmax == pytest.approx(mounts.puck_thickness, abs=1e-6)


def test_the_puck_pocket_and_bore(mounts, washer):
    # The nut pocket opens on the cavity side and leaves the floor intact.
    pocket_x = mounts.puck_thickness - mounts.protrusion
    assert _material_at(washer, pocket_x, 0.0, 0.0, size=0.25) == pytest.approx(0)
    # The rim beside the bore carries the nut, so the floor is still a floor.
    rim_y = mounts.puck_pocket / 2.0 + 0.3
    assert _material_at(washer, mounts.puck_floor / 2.0, rim_y, 0.0, size=0.2) > 0.0
    # The bore through the floor.
    assert _material_at(washer, mounts.puck_floor / 2.0, 0.0, 0.0, size=0.2) == pytest.approx(0)


def test_each_washer_seats_in_its_station_pocket(mounts, tray):
    for station in mounts.stations:
        placed = place_rail_washer(mounts, station)
        box = ch.bounding_box(placed)
        if station.side > 0:
            near, far = box.xmin, box.xmax
        else:
            near, far = -box.xmax, -box.xmin
        # The plain face bears on the pocket floor; the puck protrudes one fit.
        assert far == pytest.approx(station.pocket_floor, abs=1e-6)
        assert near == pytest.approx(
            station.pocket_floor - mounts.puck_thickness, abs=1e-6
        )
        assert station.pocket_floor - near - station.pocket_depth == pytest.approx(
            mounts.protrusion, abs=1e-6
        )
        # No overlap with the Tray: the puck sits in the open pocket.
        overlap = ch.volume_mm3(ch.intersect(tray, placed))
        assert overlap == pytest.approx(0, abs=1e-3)
