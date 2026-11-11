"""The screen lid's Bezel <-> Back band joint (ADR-0011).

Data-level assertions only: the station pattern, the corner posts outboard of
the Rod clamps, and the insert/screw sizing that the CAD builds from.
"""

import dataclasses

import pytest

from components.slide import compute_slide_budget
from layouts import make_layout
from main import BuildPipeline


def _data():
    pipeline = BuildPipeline("config/default.yaml", layout_name="slider")
    config = pipeline.load_config()
    components = pipeline.load_components()
    layout = make_layout("slider", components, config=config)
    budget = compute_slide_budget(config, components)
    return pipeline, config, components, budget, layout.placements()


def test_eight_stations_two_per_side_and_four_corners():
    _, _, _, budget, _ = _data()
    joint = budget.lid_joint
    assert joint.station_count == 8
    assert len(joint.corner_stations) == 4
    assert len(joint.edge_stations) == 4
    corners = {(round(s.x, 6), round(s.y, 6)) for s in joint.corner_stations}
    assert len(corners) == 4  # all four quadrants, one each
    edges = {(round(s.x, 6), round(s.y, 6)) for s in joint.edge_stations}
    assert len(edges) == 4
    # Two per long side, mirrored about the centreline.
    assert len({round(s.x, 6) for s in joint.edge_stations}) == 2
    assert {round(s.y, 6) for s in joint.edge_stations} == {
        round(s.y, 6) for s in joint.corner_stations
    }


def test_stations_are_inside_the_band_and_clear_of_the_clamps():
    _, config, _, budget, _ = _data()
    joint = budget.lid_joint
    for station in joint.stations:
        # The insert is fully inside the lid's plan, with the boss margin to
        # the outer face.
        assert abs(station.x) + joint.insert_hole / 2.0 <= budget.width / 2.0
        assert abs(station.y) + joint.insert_hole / 2.0 <= budget.lid_height / 2.0
        # No station lands under a Rod clamp.
        for center_y in budget.rod_clamp_y:
            clamp_x = abs(station.x) - budget.rod_x
            clamp_y = abs(station.y - center_y)
            clear = max(
                abs(clamp_x) - budget.rod_clamp_width / 2.0,
                clamp_y - budget.rod_clamp_length / 2.0,
            )
            assert clear >= config.slide.joint.corner_clearance - 1e-9


def test_corner_post_is_wide_enough_for_the_insert():
    _, config, _, budget, _ = _data()
    joint = budget.lid_joint
    assert joint.corner_post_width >= (
        joint.insert_hole + 2.0 * config.slide.joint.boss_margin
    )
    # The post starts outboard of the Rod clamp and reaches the cavity wall.
    assert joint.post_x[0] <= joint.post_x[1]
    assert joint.post_y[0] < joint.post_y[1]
    for station in joint.corner_stations:
        assert abs(station.x) < joint.post_x[1] + joint.insert_hole
        assert joint.post_y[0] < abs(station.y) < joint.post_y[1]


def test_band_holds_the_insert_and_counts_toward_the_lid_thickness():
    _, config, _, budget, _ = _data()
    joint = budget.lid_joint
    assert joint.band >= joint.insert_depth + config.material.minimum_feature
    # The band sits between the Back plate and the tapered Bezel.
    assert joint.band == config.slide.joint.band


def test_countersunk_screw_passes_the_back_and_engages_the_insert():
    _, config, _, budget, _ = _data()
    joint = budget.lid_joint
    assert joint.screw.size == config.slide.joint.screw
    # Grip: from the countersink's seat to the joint plane.
    assert joint.grip == pytest.approx(
        config.slide.lid_back - joint.countersink.depth
    )
    # At least one thread diameter of engagement, and not bottoming out.
    assert joint.screw.engagement >= float(joint.screw.size.lstrip("M"))
    assert joint.screw.engagement <= joint.insert_depth


def test_corner_posts_grow_the_envelope_without_moving_the_rods():
    """The corner posts add width outboard of the clamps, not under them."""
    _, config, components, budget, _ = _data()
    narrow_config = dataclasses.replace(
        config,
        slide=dataclasses.replace(
            config.slide,
            joint=dataclasses.replace(config.slide.joint, corner_post=0.0),
        ),
    )
    narrow = compute_slide_budget(narrow_config, components)
    assert budget.width - narrow.width == pytest.approx(
        2.0 * config.slide.joint.corner_post
    )
    # `usable_half` is the clamp corridor from the shell's inner face, so the
    # envelope can grow outward without moving the guide hardware.
    assert budget.usable_half == pytest.approx(narrow.usable_half)
    assert budget.rod_x == pytest.approx(narrow.rod_x)
