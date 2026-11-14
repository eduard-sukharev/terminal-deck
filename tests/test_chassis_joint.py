"""The chassis Tray <-> Deck band joint (ADR-0012).

Data-level assertions (stations, band, screw, stations clear of components)
plus shape-level checks that the Tray and the Deck really meet at the Parting
plane, carry the screw holes and the scallops, and rejoin into the whole.
"""

import math

import pytest

from case.chassis import Chassis
from utilities import fasteners
from case.slider_frame import SliderFrame
from components.slide import compute_slide_budget
from layouts import make_layout
from main import BuildPipeline
from utilities import cad_helpers as ch
from utilities.slider_validation import BUILD_VOLUME


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
def solids(data):
    config, _, frame, _ = data
    chassis = Chassis(config, frame)
    return chassis.build_tray(), chassis.build_deck()


def _material_at(shape, x, y, z):
    probe = ch.translate(ch.box_centered(0.4, 0.4, 0.4), x, y, z)
    return ch.volume_mm3(ch.intersect(shape, probe))


def _width_at(shape, z):
    slab = ch.translate(ch.box_centered(1000.0, 1000.0, 0.01), 0.0, 0.0, z)
    return ch.bounding_box_mm(ch.intersect(shape, slab))[0]


# -- data ----------------------------------------------------------------
def test_twelve_stations_four_corners_six_sides_two_ends(data):
    """ADR-0015 adds one long-wall station per side, on the centreline."""
    _, budget, _, _ = data
    joint = budget.chassis_joint
    assert joint.station_count == 12
    assert len(joint.corner_stations) == 4
    assert len(joint.side_stations) == 6
    assert len(joint.end_stations) == 2
    centres = {(round(s.x, 6), round(s.y, 6)) for s in joint.stations}
    assert len(centres) == 12
    centreline = [s for s in joint.stations if abs(s.x) < 1e-9]
    assert len(centreline) == 2
    assert {round(s.y, 6) for s in centreline} == {
        round(-joint.depth / 2.0 + joint.side_inset, 6),
        round(joint.depth / 2.0 - joint.side_inset, 6),
    }


def test_stations_mirror_about_both_centreplanes(data):
    """The long walls and the corners mirror both ways.

    The two short-side stations cannot: the narrow case leaves no band beside
    the keyboard, so they sit in the free band *behind* it, which only exists
    at one end. They mirror about the X centreplane alone.
    """
    _, budget, _, _ = data
    joint = budget.chassis_joint
    wall_points = {
        (round(s.x, 6), round(s.y, 6))
        for s in joint.stations
        if not s.is_end
    }
    for x, y in wall_points:
        assert (-x, y) in wall_points
        assert (x, -y) in wall_points
        assert (-x, -y) in wall_points
    end_points = {(round(s.x, 6), round(s.y, 6)) for s in joint.end_stations}
    assert len(end_points) == 2
    for x, y in end_points:
        assert (-x, y) in end_points
        assert y > 0.0


def test_parting_plane_and_band_are_derived(data):
    config, budget, frame, _ = data
    joint = budget.chassis_joint
    draft = math.tan(math.radians(config.draft.angle))
    assert joint.parting_z == pytest.approx(frame.parting_z)
    assert joint.parting_z == pytest.approx(
        min(
            config.parting.max,
            max(config.parting.min, config.parting.front_wall_fraction * budget.chassis_top),
        )
    )
    # The band is split evenly around the Parting plane.
    assert joint.band_z0 == pytest.approx(joint.parting_z - joint.band / 2.0)
    assert joint.band_z1 == pytest.approx(joint.parting_z + joint.band / 2.0)
    assert joint.band_z1 < budget.chassis_top - config.wall_thickness
    # The Deck (and therefore the band across the joint) is prismatic at the
    # closed-face width; only the Tray below band_z0 is drafted.
    assert joint.band_width == pytest.approx(budget.width)
    assert joint.base_width == pytest.approx(
        budget.width - 2.0 * draft * joint.band_z0
    )
    assert frame.chassis_base_width == pytest.approx(joint.base_width)
    assert frame.chassis_band_width == pytest.approx(joint.band_width)


def test_screw_reaches_the_insert(data):
    _, budget, _, _ = data
    joint = budget.chassis_joint
    assert joint.screw.name == "M3x18"
    assert joint.grip == pytest.approx(joint.parting_z - joint.countersink.depth)
    assert joint.screw.engagement >= float(joint.screw.size.lstrip("M"))
    assert joint.screw.engagement <= joint.insert_depth


def test_column_is_a_frustum_inside_the_floor_skin(data):
    config, budget, _, _ = data
    joint = budget.chassis_joint
    minimum = config.material.minimum_feature
    # The countersink lives in the 2 mm floor, *below* the column's base, so it
    # does not bound the column: the screw shank does, and the floor's skin
    # bounds the countersink itself.
    shank = fasteners.screw(joint.screw.size).clearance
    for station in joint.stations:
        assert 0.0 < station.base_boss <= station.boss
        assert station.base_boss >= shank + 2.0 * minimum - 1e-6
        # The column's outer surface stays inside the Tray's floor skin.
        assert station.base_distance >= station.base_boss / 2.0 + minimum - 1e-6
        # The countersink keeps a printable skin to the outer face.
        assert (
            station.base_distance - joint.countersink.diameter / 2.0
            >= minimum - 1e-6
        )


# -- geometry ------------------------------------------------------------
def test_tray_and_deck_meet_at_the_parting_plane(data, solids):
    _, _, frame, _ = data
    tray, deck = solids
    tray_box = ch.bounding_box(tray)
    deck_box = ch.bounding_box(deck)
    assert tray_box.zmin == pytest.approx(0.0, abs=0.01)
    assert tray_box.zmax == pytest.approx(frame.parting_z, abs=0.01)
    assert deck_box.zmin == pytest.approx(frame.parting_z, abs=0.01)
    assert deck_box.zmax == pytest.approx(frame.chassis_top, abs=0.01)
    # The silhouette is continuous across the joint: the prismatic band is the
    # closed-face width on both sides of the plane.
    assert _width_at(tray, frame.parting_z - 0.005) == pytest.approx(
        frame.chassis_band_width, abs=0.01
    )
    assert _width_at(deck, frame.parting_z + 0.005) == pytest.approx(
        frame.chassis_band_width, abs=0.01
    )


def test_tray_is_tapered_then_prismatic_and_the_deck_is_prismatic(data, solids):
    config, _, frame, _ = data
    tray, deck = solids
    # Tray: drafted from the base to band_z0, prismatic from band_z0 to the
    # Parting plane.
    assert _width_at(tray, 0.5) == pytest.approx(
        frame.chassis_base_width
        + 2.0 * ch.draft_inset(config.draft.angle, 0.5),
        abs=0.05,
    )
    assert _width_at(tray, frame.chassis_band_z0 + 0.5) == pytest.approx(
        frame.width, abs=0.05
    )
    assert _width_at(tray, frame.chassis_band_z0 - 0.5) < frame.width - 0.05
    # Deck: one prismatic block, with no flare back out toward the face.
    for z in (frame.parting_z + 0.5, frame.chassis_top / 2.0 + 5.0, frame.chassis_top - 0.5):
        assert _width_at(deck, z) == pytest.approx(frame.width, abs=0.05)


def test_tray_and_deck_are_valid_and_rejoin(solids):
    tray, deck = solids
    assert tray.is_valid and deck.is_valid
    assert len(tray.solids()) == 1 and len(deck.solids()) == 1
    whole = ch.make_compound([tray, deck])
    assert ch.volume_mm3(whole) == pytest.approx(
        ch.volume_mm3(tray) + ch.volume_mm3(deck), rel=1e-6
    )


def test_every_station_has_a_screw_hole_through_the_tray(data, solids):
    _, budget, frame, _ = data
    joint = budget.chassis_joint
    tray, _ = solids
    z = frame.parting_z / 2.0
    for station in joint.stations:
        assert _material_at(tray, station.x, station.y, z) == pytest.approx(0)
        # The column around the hole stays solid (tested at a safe radius
        # just outside the countersink cone).
        offset = joint.countersink.diameter / 2.0 + 0.7
        px = station.x + station.normal[0] * offset
        py = station.y + station.normal[1] * offset
        assert _material_at(tray, px, py, z) > 0


def test_every_station_has_an_insert_hole_in_the_deck(data, solids):
    _, budget, frame, _ = data
    joint = budget.chassis_joint
    _, deck = solids
    z = frame.parting_z + joint.insert_depth / 2.0
    for station in joint.stations:
        assert _material_at(deck, station.x, station.y, z) == pytest.approx(0)


def test_scallops_cut_each_half_of_the_band(data, solids):
    _, budget, frame, _ = data
    joint = budget.chassis_joint
    tray, deck = solids
    # A vertical (front/rear) station: the wall does not shear, so the cut is
    # exactly one scallop_depth deep on both halves.
    station = next(s for s in joint.side_stations if s.y > 0.0)
    outer_y = station.y + station.surface
    floor_y = outer_y - joint.scallop_depth
    for part, z in (
        (tray, frame.parting_z - joint.scallop_height / 2.0),
        (deck, frame.parting_z + joint.scallop_height / 2.0),
    ):
        assert _material_at(part, station.x, outer_y - 0.2, z) == pytest.approx(0)
        assert _material_at(part, station.x, floor_y - 0.4, z) > 0


def test_tray_and_deck_sections_fit_and_rejoin(data, solids):
    config, _, frame, _ = data
    wall = config.wall.thickness
    from geometry.split import split_part

    for part, name in zip(solids, ("chassis_tray", "chassis_deck")):
        sections = split_part(part, config.slide.split[name], frame.depth, wall)
        assert sum(ch.volume_mm3(s) for s in sections) == pytest.approx(
            ch.volume_mm3(part), rel=1e-3
        )
        for section in sections:
            x, y, z = ch.bounding_box_mm(section)
            assert x <= BUILD_VOLUME[0] + 1e-6
            assert y <= BUILD_VOLUME[1] + 1e-6
            assert z <= BUILD_VOLUME[2] + 1e-6
