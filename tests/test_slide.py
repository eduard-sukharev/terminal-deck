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
    # The USB hub is an external module on the accessory rail, not a chassis part.
    assert "USB Hub" not in names
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


def test_case_draft_is_configured_and_inside_the_requested_range():
    _, config, components, _, _ = _data()
    assert 5.0 <= config.draft.angle <= 10.0
    budget = _budget(config, components)
    assert budget.draft_allowance > 0.0
    # The guide hardware is inboard, under the display, so the side pod is the
    # wall, the shell clearance and the draft inset of the tapered lid wall --
    # no hardware, no `component_gap`, no `joint.corner_post`.
    assert budget.side_pod == pytest.approx(
        config.wall_thickness + config.clearance.shell + budget.draft_allowance
    )
    assert budget.usable_half == pytest.approx(
        max(components["keyboard"].size().width, components["display"].size().width)
        / 2.0
    )
    assert budget.hardware_width == pytest.approx(
        budget.clamp_width + 2.0 * config.slide.slot_clearance
    )
    assert budget.clamp_body_width == pytest.approx(budget.clamp_width)


def test_width_derives_from_the_content_and_the_drafted_cavity():
    """The width is the content plus the drafted side wall, nothing more."""
    _, config, components, _, _ = _data()
    display = components["display"].size()
    budget = _budget(config, components)

    # Every term of the side pod is derived: the draft inset follows the
    # display's top height inside the tapered lid cavity.
    assert 0.0 < budget.draft_allowance < 3.0
    assert budget.width == pytest.approx(display.width + 2.0 * budget.side_pod)
    # The side bezel drops from the old 30 mm pod to a few mm.
    assert budget.width < 250.0
    assert budget.width - display.width < 12.0


def test_rod_x_is_bounded_by_the_post_the_seat_and_the_display():
    """The stance is derived from the three features it must clear."""
    _, config, components, _, _ = _data()
    budget = _budget(config, components)
    bounds = budget.rod_x_bounds

    # 1. the lid's band corner post must still hold the insert outboard of the
    #    Rod clamp; 2. the Deck's seat must clear the chassis band's corner
    #    boss; 3. the moving head must stay under the display.
    assert bounds.post == pytest.approx(
        budget.width / 2.0
        - config.wall_thickness
        - budget.rod_clamp_width / 2.0
        - config.slide.joint.corner_clearance
        - (budget.lid_joint.insert_hole + 2.0 * config.slide.joint.boss_margin)
    )
    seat_half = (
        budget.clamp_width / 2.0
        + config.slide.bearing_clamp.seat_fit
        + config.slide.bearing_clamp.seat_wall
    )
    assert bounds.seat == pytest.approx(
        budget.width / 2.0
        - config.chassis_joint.station_inset
        - config.chassis_joint.boss / 2.0
        - config.material.minimum_feature
        - seat_half
    )
    assert bounds.head == pytest.approx(
        components["display"].size().width / 2.0 - budget.clamp_width / 2.0
    )
    assert budget.rod_x <= min(bounds.post, bounds.seat, bounds.head) + 1e-9
    assert budget.rod_x == pytest.approx(
        min(bounds.post, bounds.seat, bounds.head) - config.slide.rod.side_margin
    )
    # The rods moved from beside the display (±125) to under it.
    assert budget.rod_x < components["display"].size().width / 2.0


def test_display_cavity_follows_the_head_the_guard_and_the_sag():
    """The lid thickness is what the moving head and the guard need."""
    _, config, components, _, _ = _data()
    budget = _budget(config, components)
    display = components["display"].size()
    guard = config.slide.fpc_guard

    assert budget.head_crown == pytest.approx(
        budget.rod_raise + budget.clamp_width / 2.0
    )
    assert budget.display_cavity == pytest.approx(
        budget.head_crown
        + config.slide.component_gap
        + guard.sag_allowance
        + guard.total
    )
    assert budget.lid_thickness == pytest.approx(
        config.slide.lid_back
        + budget.display_cavity
        + display.height
        + config.slide.lid_front
        + config.clearance.shell
        - config.bezel.recess
    )
    assert budget.thickness == pytest.approx(
        budget.chassis_top + config.slide.lid_clearance + budget.lid_thickness
    )
    # The cavity is deeper than the driver sitting at the back panel, so the
    # display is carried by the stack, not by the old 5 mm driver allowance.
    assert budget.display_cavity > config.slide.driver_gap + components["driver"].size().height
    # Still inside the 140 mm HARD face limit (the budget is Z, not Y).
    assert budget.thickness < config.slide.face_height_limit


def test_guard_covers_the_ribbon_and_the_slot_band():
    """The guard's planform is derived from the ribbon and the head's sweep."""
    _, config, components, _, _ = _data()
    budget = _budget(config, components)
    display = components["display"].size()
    guard = config.slide.fpc_guard
    x0, y0, x1, y1 = budget.guard_planform

    # The ribbon: the display's FPC exits the east short edge, centred in Y.
    ribbon_half = config.display.flex.width / 2.0
    assert y0 <= -ribbon_half - guard.margin + 1e-9
    assert y1 >= ribbon_half + guard.margin - 1e-9
    # The slot band the head sweeps: the guard spans it with margin.
    slot_x0 = budget.rod_x - budget.hardware_width / 2.0
    slot_x1 = budget.rod_x + budget.hardware_width / 2.0
    assert x0 <= slot_x0 - guard.margin + 1e-9
    assert x1 >= slot_x1 + guard.margin - 1e-9
    # The west end starts at the driver's FPC connector, the east end stays
    # inside the display's shadow (so it never pierces the lid wall).
    assert x0 == pytest.approx(
        components["driver"].offset_x
        + components["driver"].width / 2.0
        + guard.fit
    )
    assert x1 <= display.width / 2.0
    assert x1 <= budget.width / 2.0 - config.wall_thickness


def test_slide_budget_defaults():
    config, components, *_, = _data()[1:]
    budget = _budget(config, components)
    keyboard = components["keyboard"]

    assert budget.bearing_model == "LM6UU"
    assert budget.travel == pytest.approx(
        config.slide.well_front_margin
        + keyboard.size().depth
        + config.slide.travel_clearance
    )
    assert budget.closed_face_height <= config.slide.face_height_limit
    assert budget.within_face_limit
    assert budget.open_face_height > budget.closed_face_height
    assert budget.thickness < config.slide.face_height_limit
    # The guides are inboard, so the width is the display plus a thin drafted
    # wall -- not the old 292 mm side-pod envelope. Each half still fits the
    # 220 mm bed.
    assert 230.0 <= budget.width <= 250.0
    assert budget.width / 2.0 <= 220.0
    assert budget.slot_fits


def test_second_bearing_breaks_the_face_height_budget():
    _, config, components, _, _ = _data()
    two = dataclasses.replace(
        config.slide,
        bearing=dataclasses.replace(config.slide.bearing, per_rod=2),
    )
    budget = _budget(dataclasses.replace(config, slide=two), components)
    assert not budget.within_face_limit
    assert budget.closed_face_height > config.slide.face_height_limit


def test_chassis_matches_the_lid_depth():
    """The closed lid must not overhang the chassis at the rear.

    The lid's guide span is fixed by the mechanism, so the chassis grows to
    the closed face instead: the two halves share one depth.
    """
    _, config, components, _, _ = _data()
    budget = _budget(config, components)
    assert budget.chassis_height == pytest.approx(budget.lid_height)
    assert budget.face_flush
    assert budget.rear_band == pytest.approx(
        budget.rear_band_min + budget.rear_band_extension
    )
    assert budget.rear_band_extension > 0.0


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
        "slide-display-guide-clear",
        "slide-rod-clamp-clear",
        "slide-fpc-guard-stack",
        "slide-fpc-guard-cover",
        "slide-chassis-seat-clear",
        "slide-lid-joint-post-inboard",
    ):
        assert name in by_name, name
        assert by_name[name].passed, by_name[name].message


def test_display_clearance_is_a_z_check_against_the_guard():
    """A display placed 1 mm low must fail the Z clearance, not pass silently."""
    _, config, components, _, placements = _data()
    budget = _budget(config, components)
    sagged = [
        dataclasses.replace(p, z=p.z - 1.0)
        if "display" in p.component.name.lower()
        else p
        for p in placements
    ]
    report = run_slider_checks(budget, config, sagged)
    assert "slide-display-guide-clear" in {c.name for c in report.failures}


def test_guard_stack_check_fails_when_the_channel_is_too_shallow():
    """The channel must swallow the measured ribbon stack."""
    _, config, components, _, placements = _data()
    tight = dataclasses.replace(
        config.slide,
        fpc_guard=dataclasses.replace(config.slide.fpc_guard, recess=0.2),
    )
    config2 = dataclasses.replace(config, slide=tight)
    placements2 = make_layout("slider", components, config=config2).placements()
    report = run_slider_checks(_budget(config2, components), config2, placements2)
    assert "slide-fpc-guard-stack" in {c.name for c in report.failures}


def test_clamp_corridor_check_catches_a_wide_rear_band():
    """A rear-band part pushed into a side pod must fail the clamp check."""
    _, config, components, _, placements = _data()
    budget = _budget(config, components)
    moved = [
        dataclasses.replace(p, x=p.x + budget.usable_half + 10.0)
        if p.component.name == "Orange Pi Zero 2W"
        else p
        for p in placements
    ]
    report = run_slider_checks(budget, config, moved)
    assert "slide-clamp-clear" in {c.name for c in report.failures}


def test_slide_config_loads_from_its_topic():
    _, config, *_ = _data()
    assert "slide" in config.topics
    assert config.slide.bearing.model == "LM6UU"
    assert config.slide.bearing.length > 0
    assert config.slide.chain.bend_radius >= 30.0
