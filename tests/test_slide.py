"""Slider data skeleton (issue #3).

One high seam: config -> components -> ``slider`` layout -> slide budget ->
slider validation report. These tests assert the derived numbers and the
report, not private helpers.
"""

import dataclasses

import pytest

from components.slide import compute_slide_budget
from layouts import make_layout
from main import BuildPipeline
from utilities.slider_validation import run_slider_checks
from utilities.validation import ValidationReport, check_collisions


def _data():
    pipeline = BuildPipeline("config/default.yaml", layout_name="slider")
    config = pipeline.load_config()
    components = pipeline.load_components()
    layout = make_layout("slider", components, config=config)
    return pipeline, config, components, layout, layout.placements()


def _budget(config, components):
    return compute_slide_budget(config, components)


# ── layout ─────────────────────────────────────────────────────────────


def test_slider_layout_places_the_core_parts():
    _, _, _, layout, placements = _data()
    names = {p.component.name for p in placements}
    assert "40% Keyboard (RP2040)" in names
    assert "Orange Pi Zero 2W" in names
    assert "USB Hub" in names
    assert 'Display 8.8" 1920x480' in names
    assert "HDMI Driver Board" in names
    assert "RP2040-Zero" in names
    # The battery is an external accessory in the slider: not a chassis part.
    assert "Battery" not in names
    assert layout.constraint_report().passed


def test_slider_layout_has_no_collisions():
    _, _, _, _, placements = _data()
    report = ValidationReport()
    check_collisions(placements, report)
    assert report.passed, report.summary()


def test_keyboard_faces_the_user():
    """The keyboard's local +Y (spacebar side) must face the user at -Y."""
    _, _, components, _, placements = _data()
    keyboard = next(p for p in placements if p.component is components["keyboard"])
    assert keyboard.rotation == 180.0


def test_slider_layout_is_centred_on_the_chassis():
    """The chassis footprint is centred on the origin (coordinate contract)."""
    _, config, components, _, placements = _data()
    keyboard = next(p for p in placements if p.component is components["keyboard"])
    budget = _budget(config, components)
    # Keyboard front edge minus the front margin is the chassis front.
    chassis_front = keyboard.box[1] - config.slide.well_front_margin
    assert chassis_front == pytest.approx(-budget.chassis_height / 2.0, abs=1e-6)


# ── budget ─────────────────────────────────────────────────────────────


def test_slide_budget_defaults():
    config, components, *_, = _data()[1:]
    budget = _budget(config, components)
    keyboard = components["keyboard"]

    assert budget.bearing_model == "LM6LUU"
    assert budget.travel == pytest.approx(
        config.slide.well_front_margin
        + keyboard.size().depth
        + config.slide.travel_clearance
    )
    assert budget.closed_face_height <= config.slide.face_height_limit
    assert budget.within_face_limit
    assert budget.open_face_height > budget.closed_face_height
    assert budget.thickness < config.slide.face_height_limit
    assert 250.0 <= budget.width <= 275.0


def test_second_bearing_breaks_the_face_height_budget():
    _, config, components, _, _ = _data()
    two = dataclasses.replace(
        config.slide,
        bearing=dataclasses.replace(config.slide.bearing, per_rod=2),
    )
    budget = _budget(dataclasses.replace(config, slide=two), components)
    assert not budget.within_face_limit
    assert budget.closed_face_height > config.slide.face_height_limit


def test_open_pose_adds_the_travel():
    _, config, components, _, _ = _data()
    budget = _budget(config, components)
    assert budget.open_face_height == pytest.approx(
        max(budget.chassis_height, budget.lid_height + budget.travel)
    )


# ── validation ─────────────────────────────────────────────────────────


def test_slider_checks_pass_by_default():
    _, config, components, _, placements = _data()
    report = run_slider_checks(_budget(config, components), config, placements)
    assert report.passed, report.summary()
    assert report.goals["closed-face-height"] == pytest.approx(
        _budget(config, components).closed_face_height
    )


def test_slider_checks_fail_on_oversize_bearing():
    _, config, components, _, placements = _data()
    two = dataclasses.replace(
        config.slide,
        bearing=dataclasses.replace(config.slide.bearing, per_rod=2),
    )
    config2 = dataclasses.replace(config, slide=two)
    report = run_slider_checks(_budget(config2, components), config2, placements)
    assert not report.passed
    names = {check.name for check in report.failures}
    assert "slide-budget" in names


def test_slider_checks_fail_without_lid_clearance():
    _, config, components, _, _ = _data()
    tight = dataclasses.replace(config.slide, lid_clearance=0.0)
    config2 = dataclasses.replace(config, slide=tight)
    placements = make_layout("slider", components, config=config2).placements()
    report = run_slider_checks(_budget(config2, components), config2, placements)
    assert not report.passed
    assert "slide-keycap-clearance" in {c.name for c in report.failures}


def test_sections_fit_the_build_volume():
    _, config, components, _, placements = _data()
    report = run_slider_checks(_budget(config, components), config, placements)
    fit = next(c for c in report.checks if c.name == "slide-section-fit")
    assert fit.passed, fit.message


def test_slider_checks_cover_placement_geometry():
    """The placement-derived checks exist and pass for the default layout."""
    _, config, components, _, placements = _data()
    report = run_slider_checks(_budget(config, components), config, placements)
    by_name = {c.name: c for c in report.checks}
    for name in (
        "slide-clamp-clear",
        "slide-sweep-clear",
        "slide-keycap-clearance",
        "slide-rear-band-fit",
        "slide-display-fit",
    ):
        assert name in by_name, name
        assert by_name[name].passed, by_name[name].message


def test_clamp_corridor_check_catches_a_wide_rear_band():
    """A rear-band part pushed into a side pod must fail the clamp check."""
    _, config, components, _, placements = _data()
    moved = [
        dataclasses.replace(p, x=p.x + 30.0)
        if p.component.name == "Orange Pi Zero 2W"
        else p
        for p in placements
    ]
    report = run_slider_checks(_budget(config, components), config, moved)
    assert "slide-clamp-clear" in {c.name for c in report.failures}


def test_slide_config_loads_from_its_topic():
    _, config, *_ = _data()
    assert "slide" in config.topics
    assert config.slide.bearing.model == "LM6LUU"
    assert config.slide.bearing.length > 0
    assert config.slide.chain.bend_radius >= 30.0
