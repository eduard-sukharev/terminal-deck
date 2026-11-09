"""First-generation slider case geometry (issue #3).

The case must be a closed solid inside the derived budget, split into two
printable Sections that add back to the whole, with the guide hardware in the
right place. These are shape-level assertions, not a golden-master volume.
"""

import pytest

from case.chassis import Chassis
from case.screen_lid import ScreenLid
from case.slider_frame import SliderFrame
from components.slide import build_guide_rod, build_linear_bearing, compute_slide_budget
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
    return config, components, budget, frame


@pytest.fixture(scope="module")
def solids(data):
    config, _, _, frame = data
    chassis = Chassis(config, frame).build()
    lid = ScreenLid(config, frame).build()
    return chassis, lid


def test_chassis_bbox_matches_the_budget(data, solids):
    _, _, budget, frame = data
    chassis, _ = solids
    x, y, z = ch.bounding_box_mm(chassis)
    assert x == pytest.approx(budget.width, abs=0.1)
    assert y == pytest.approx(budget.chassis_height, abs=0.1)
    # The Bearing clamps rise above the Deck to the rod axis.
    assert z == pytest.approx(frame.clamp_top, abs=0.1)
    assert ch.volume_mm3(chassis) > 0


def test_screen_lid_bbox_matches_the_budget(data, solids):
    _, _, budget, frame = data
    _, lid = solids
    x, y, z = ch.bounding_box_mm(lid)
    assert x == pytest.approx(budget.width, abs=0.1)
    assert y == pytest.approx(budget.lid_height, abs=0.1)
    assert z == pytest.approx(frame.lid_thickness, abs=0.1)
    assert ch.volume_mm3(lid) > 0


def test_chassis_sections_rejoin(solids):
    chassis, _ = solids
    left, right = ch.split_x(chassis)
    assert ch.volume_mm3(left) + ch.volume_mm3(right) == pytest.approx(
        ch.volume_mm3(chassis), rel=1e-3
    )


def test_screen_lid_sections_rejoin(solids):
    _, lid = solids
    left, right = ch.split_x(lid)
    assert ch.volume_mm3(left) + ch.volume_mm3(right) == pytest.approx(
        ch.volume_mm3(lid), rel=1e-3
    )


def test_sections_fit_the_build_volume(solids):
    chassis, lid = solids
    for part in (chassis, lid):
        left, right = ch.split_x(part)
        for section in (left, right):
            x, y, z = ch.bounding_box_mm(section)
            assert x <= BUILD_VOLUME[0] + 1e-6
            assert y <= BUILD_VOLUME[1] + 1e-6
            assert z <= BUILD_VOLUME[2] + 1e-6


def test_guide_hardware(data):
    config, _, budget, _ = data
    rod = build_guide_rod(config.slide.rod.diameter, budget.rod_usable)
    x, y, z = ch.bounding_box_mm(rod)
    assert x == pytest.approx(config.slide.rod.diameter, abs=0.01)
    assert y == pytest.approx(budget.rod_usable, abs=0.01)
    assert z == pytest.approx(config.slide.rod.diameter, abs=0.01)

    bearing = build_linear_bearing(
        config.slide.bearing.outer_diameter,
        config.slide.bearing.bore,
        config.slide.bearing.length,
    )
    bx, by, bz = ch.bounding_box_mm(bearing)
    assert bx == pytest.approx(config.slide.bearing.outer_diameter, abs=0.01)
    assert by == pytest.approx(config.slide.bearing.length, abs=0.01)
    assert bz == pytest.approx(config.slide.bearing.outer_diameter, abs=0.01)
    # Hollow: the bushing is its outer cylinder minus the bore.
    import math

    outer_volume = math.pi * (config.slide.bearing.outer_diameter / 2.0) ** 2 * config.slide.bearing.length
    bore_volume = math.pi * (config.slide.bearing.bore / 2.0) ** 2 * config.slide.bearing.length
    assert ch.volume_mm3(bearing) == pytest.approx(
        outer_volume - bore_volume, rel=0.01
    )
