"""Slider data skeleton (issue #3).

One high seam: config -> components -> ``slider`` layout -> slide budget ->
slider validation report. These tests assert the derived numbers and the
report, not private helpers.
"""

import dataclasses

import pytest

from components.keycap_set import CAP_PLATE_GAP
from components.rp2040_keyboard import Rp2040Keyboard
from components.slide import compute_slide_budget
from keyboard import register_keycap
from layouts import make_layout
from main import BuildPipeline
from utilities import fasteners
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
    """The chassis footprint is centred on the origin (coordinate contract).

    The keyboard's front edge sits one derived Well margin behind the chassis
    front (ADR-0014: the margin falls out of the face-height budget, so the
    recipe reads it from the budget, not from config).
    """
    _, config, components, _, placements = _data()
    keyboard = next(p for p in placements if p.component is components["keyboard"])
    budget = _budget(config, components)
    # Keyboard front edge minus the Well margin is the chassis front.
    chassis_front = keyboard.box[1] - budget.well_front_margin
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
    assert budget.rod_x_bounds is not None
    assert budget.usable_half == pytest.approx(budget.well.plate_width / 2.0)
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
    # The keyboard plate is the wider content now (ADR-0014: the plate grew to
    # bear on the Well ring), so it drives the width; the display is only the
    # fallback content reference here.
    assert budget.well.plate_width >= display.width
    assert budget.width == pytest.approx(budget.well.plate_width + 2.0 * budget.side_pod)
    # The side bezel drops from the old 30 mm pod to a few mm.
    assert budget.width < 250.0
    assert budget.width - budget.well.plate_width < 12.0


# ── Welled plate (ADR-0014) ────────────────────────────────────────────


def test_wobble_is_one_config_constant():
    """The wobble allowance comes from keyboard.plate.wobble, one copy only."""
    _, config, components, _, _ = _data()
    budget = _budget(config, components)

    assert config.keyboard.plate_wobble == pytest.approx(0.6)
    assert config.keyboard.plate_wobble == config.keyboard.plate["wobble"]
    assert budget.well.wobble == config.keyboard.plate_wobble


def test_cutout_and_plate_follow_the_keycap_footprint():
    """Cutout = keycap + wobble per side; plate = Cutout + one wall per side."""
    _, config, components, _, _ = _data()
    budget = _budget(config, components)
    well = budget.well
    wobble = config.keyboard.plate_wobble
    wall = config.wall_thickness

    # The real keycap base footprint, read from the keyboard geometry model --
    # not a number repeated here.
    keycap_w, keycap_d, tallest = components["keyboard"].keycap_envelope()
    assert (well.keycap_width, well.keycap_depth) == pytest.approx((keycap_w, keycap_d))
    assert well.tallest_keycap == pytest.approx(tallest)
    # 228.05 x 75.65 is the measured base footprint of the XDA keycap set.
    assert (well.keycap_width, well.keycap_depth) == pytest.approx((228.05, 75.65))

    assert well.cutout == pytest.approx((keycap_w + 2 * wobble, keycap_d + 2 * wobble))
    assert well.plate == pytest.approx(
        (well.cutout_width + 2 * wall, well.cutout_depth + 2 * wall)
    )
    # The plate border is the Well wall plus the wobble: wall + wobble each
    # side (the ADR's `edge_margin`, measured from the keycap edge).
    assert well.ring == pytest.approx(wall)
    assert well.edge_margin == pytest.approx(wall + wobble)
    assert (well.plate_width - well.keycap_width) / 2.0 == pytest.approx(wall + wobble)
    assert (well.plate_depth - well.keycap_depth) / 2.0 == pytest.approx(wall + wobble)


def test_a_thicker_wall_grows_the_plate_not_the_cutout():
    """The Cutout is the keycap vocabulary; the wall only thickens the plate."""
    _, config, components, _, _ = _data()
    thin = _budget(config, components)
    thick_wall = dataclasses.replace(config.wall, thickness=1.8)
    thick = _budget(dataclasses.replace(config, wall=thick_wall), components)

    assert thick.well.cutout == pytest.approx(thin.well.cutout)
    assert thick.well.plate_width == pytest.approx(
        thin.well.plate_width + 2.0 * (1.8 - config.wall_thickness)
    )
    assert thick.well.plate_depth == pytest.approx(
        thin.well.plate_depth + 2.0 * (1.8 - config.wall_thickness)
    )


def test_the_well_carries_the_plate_seam():
    """The Well is one source for the plate: the Deck reads its mount stations.

    The plate's Seam is a keyboard artifact, but the Deck's insert bosses and
    the plate's ears are one pattern, so the budget hands it on rather than
    letting each builder re-derive (or, worse, assume) the split.
    """
    _, config, components, _, _ = _data()
    budget = _budget(config, components)
    seam = components["keyboard"].plate_model().seam

    assert budget.well.seam == seam
    # The path's ends are what the mount stations straddle (#18): the front is
    # on the centreline, the rear is the spacebar row's gap.
    bands = budget.well.seam.segments(budget.well.plate_depth)
    assert bands[0][2] == pytest.approx(0.0)
    assert bands[-1][2] == pytest.approx(-50.584375)


def test_plate_z_is_slaved_to_the_tallest_keycap():
    """The plate sits one cap stack below the Deck top (ADR-0014)."""
    _, config, components, _, _ = _data()
    budget = _budget(config, components)
    well = budget.well

    assert well.plate_thickness == pytest.approx(
        config.keyboard.plate_thickness
    )
    assert well.plate_bottom == pytest.approx(
        budget.chassis_top - well.tallest_keycap - CAP_PLATE_GAP
        - well.plate_thickness
    )
    assert well.plate_top == pytest.approx(well.plate_bottom + well.plate_thickness)
    # The Well descends from the Deck's top face to the plate's top face.
    assert well.well_depth == pytest.approx(budget.chassis_top - well.plate_top)
    assert well.well_depth > 0.0
    assert budget.plate_z == pytest.approx(well.plate_bottom)


def test_the_parting_plane_never_cuts_the_well():
    """`parting_z <= plate_bottom` is HARD (ADR-0014, ADR-0012)."""
    _, config, components, _, _ = _data()
    budget = _budget(config, components)
    assert budget.parting_below_plate
    assert (
        budget.chassis_joint.parting_z
        <= budget.well.plate_bottom + 1e-9
    )


def test_well_front_margin_falls_out_of_the_face_budget():
    """The margin is the 140 mm budget's remainder, not a pinned config value."""
    _, config, components, _, _ = _data()
    budget = _budget(config, components)
    slide = config.slide

    bearing_stack = (
        slide.bearing.per_rod * slide.bearing.length
        + (slide.bearing.per_rod - 1) * slide.clamp_wall
    )
    lid_stack = (
        slide.travel_clearance
        + bearing_stack
        + 2.0 * (slide.rod_clamp.length + slide.rod_clamp.clearance)
        + 2.0 * slide.rod.end_support
        + slide.top_bezel
    )
    # The front lip's floor: the narrowest Deck material that still hosts an M2
    # boss merged to the Well ring's outer face.
    insert = fasteners.heat_insert(config.keyboard.mounting["screw"])
    boss_lip = (
        config.merged_boss.bore_margin
        + insert.printed_hole_diameter
        + config.chassis_joint.boss_margin
    )
    assert budget.well.boss_lip_required == pytest.approx(boss_lip)
    assert budget.well_front_margin >= config.wall_thickness + boss_lip - 1e-9
    # Inside that floor the margin is exactly what the face limit leaves.
    assert budget.well_front_margin == pytest.approx(
        config.slide.face_height_limit - lid_stack - budget.well.plate_depth
    )
    assert budget.keyboard_top == pytest.approx(
        budget.well_front_margin + budget.well.plate_depth
    )
    assert budget.closed_face_height == pytest.approx(budget.keyboard_top + lid_stack)
    assert budget.within_face_limit
    assert budget.face_flush


def test_the_front_and_rear_lips_host_the_plate_bosses():
    """The Well's bosses live in the lips; the lips must be wide enough."""
    _, config, components, _, _ = _data()
    budget = _budget(config, components)
    well = budget.well

    assert well.front_lip == pytest.approx(
        budget.well_front_margin - config.wall_thickness
    )
    assert well.rear_lip == pytest.approx(budget.rear_band)
    assert well.front_lip >= well.boss_lip_required - 1e-9
    assert well.rear_lip >= well.boss_lip_required - 1e-9
    assert well.front_lip_slack >= 0.0


def test_a_wider_keycap_profile_moves_the_cutout_and_the_plate():
    """A different keycap footprint re-derives the Cutout and the plate."""
    _, config, components, _, _ = _data()
    budget = _budget(config, components)
    before = budget.well

    @register_keycap("test_wide")
    class WideKeycap:
        """A wider profile at the same height: only its numbers matter here."""

        def base_size(self) -> float:
            return 20.0

        def top_diameter(self) -> float:
            return 16.0

        def height(self) -> float:
            return 9.0

        def segments(self) -> int:
            return 16

        def base_chamfer(self) -> float:
            return 1.0

    flat = config.keyboard.plate or {}
    other = Rp2040Keyboard({
        "layout_source": config.keyboard.layout_source,
        "switch_family": config.keyboard.switch_family,
        "stabilizer_family": config.keyboard.stabilizer_family,
        "wall_thickness": config.wall_thickness,
        "plate": flat,
        "mounting": config.keyboard.mounting or {},
        "pitch": config.keyboard.pitch,
        "keycap": {"profile": "test_wide", "enabled": True},
    })
    other_components = dict(components)
    other_components["keyboard"] = other
    # Same plate Z as the default build (the controller stack sets it).
    other.set_plate_raise(before.plate_bottom)
    after_budget = _budget(config, other_components)
    after = after_budget.well

    assert after.keycap_width > before.keycap_width
    assert after.cutout_width == pytest.approx(
        after.keycap_width + 2.0 * config.keyboard.plate_wobble
    )
    assert after.cutout_depth == pytest.approx(
        after.keycap_depth + 2.0 * config.keyboard.plate_wobble
    )
    assert after.plate_width == pytest.approx(
        after.cutout_width + 2.0 * config.wall_thickness
    )
    # Wider, not taller: the plate and the Deck top stay where they were.
    assert after.tallest_keycap == pytest.approx(before.tallest_keycap)
    assert after_budget.chassis_top == pytest.approx(budget.chassis_top)
    assert after.plate_bottom == pytest.approx(before.plate_bottom)


def test_a_taller_keycap_lifts_the_deck_not_the_plate():
    """A taller cap deepens the Well: the Deck top rises, the plate stays."""
    _, config, components, _, _ = _data()
    budget = _budget(config, components)
    before = budget.well

    @register_keycap("test_taller")
    class TallerKeycap:
        """Slightly taller (still inside the Parting's headroom)."""

        def base_size(self) -> float:
            return 18.5

        def top_diameter(self) -> float:
            return 15.0

        def height(self) -> float:
            return 9.1

        def segments(self) -> int:
            return 16

        def base_chamfer(self) -> float:
            return 1.0

    flat = config.keyboard.plate or {}
    other = Rp2040Keyboard({
        "layout_source": config.keyboard.layout_source,
        "switch_family": config.keyboard.switch_family,
        "stabilizer_family": config.keyboard.stabilizer_family,
        "wall_thickness": config.wall_thickness,
        "plate": flat,
        "mounting": config.keyboard.mounting or {},
        "pitch": config.keyboard.pitch,
        "keycap": {"profile": "test_taller", "enabled": True},
    })
    # The plate stays on its standoff: the taller cap is absorbed above it.
    other.set_plate_raise(before.plate_bottom)
    other_components = dict(components)
    other_components["keyboard"] = other
    after_budget = _budget(config, other_components)
    after = after_budget.well

    assert after.tallest_keycap > before.tallest_keycap
    assert after.plate_bottom == pytest.approx(before.plate_bottom)
    assert after_budget.chassis_top > budget.chassis_top
    assert after.well_depth == pytest.approx(
        after_budget.chassis_top - after.plate_top
    )
    assert after_budget.parting_below_plate


def test_a_cap_beyond_the_parting_headroom_is_rejected():
    """Only ~0.15 mm of headroom: a much taller cap must fail, not fit.

    The Parting plane sits at half the Deck top, so a deck that grows for the
    caps pushes the plane up into the Well. That is a HARD violation
    (ADR-0014), so the budget refuses instead of shrinking the Well.
    """
    _, config, components, _, _ = _data()

    @register_keycap("test_too_tall")
    class TooTallKeycap:
        def base_size(self) -> float:
            return 18.5

        def top_diameter(self) -> float:
            return 15.0

        def height(self) -> float:
            return 12.0

        def segments(self) -> int:
            return 16

        def base_chamfer(self) -> float:
            return 1.0

    flat = config.keyboard.plate or {}
    other = Rp2040Keyboard({
        "layout_source": config.keyboard.layout_source,
        "switch_family": config.keyboard.switch_family,
        "stabilizer_family": config.keyboard.stabilizer_family,
        "wall_thickness": config.wall_thickness,
        "plate": flat,
        "mounting": config.keyboard.mounting or {},
        "pitch": config.keyboard.pitch,
        "keycap": {"profile": "test_too_tall", "enabled": True},
    })
    other_components = dict(components)
    other_components["keyboard"] = other
    with pytest.raises(ValueError, match="Parting"):
        _budget(config, other_components)


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

    assert budget.bearing_model == "LM6UU"
    assert budget.travel == pytest.approx(
        budget.well_front_margin
        + budget.well.plate_depth
        + config.slide.travel_clearance
    )
    assert budget.closed_face_height <= config.slide.face_height_limit
    assert budget.within_face_limit
    assert budget.open_face_height > budget.closed_face_height
    assert budget.thickness < config.slide.face_height_limit
    # The keyboard plate drives the width now (ADR-0014), plus a thin drafted
    # wall -- not the old 292 mm side-pod envelope. Each half still fits the
    # 220 mm bed.
    assert 230.0 <= budget.width <= 250.0
    assert budget.width / 2.0 <= 220.0
    assert budget.slot_fits


def test_second_bearing_breaks_the_face_height_budget():
    """The extra bearing is absorbed by the front margin, then the face fails.

    The margin cannot shrink below the front lip's floor (it has to host the
    plate's M2 boss), so past that point the closed face grows instead and the
    HARD 140 mm check fails -- it is never weakened to keep the bearing.
    """
    _, config, components, _, _ = _data()
    two = dataclasses.replace(
        config.slide,
        bearing=dataclasses.replace(config.slide.bearing, per_rod=2),
    )
    budget = _budget(dataclasses.replace(config, slide=two), components)
    assert budget.well_front_margin == pytest.approx(
        config.wall_thickness + budget.well.boss_lip_required
    )
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


# The front long-wall band stations (geometry/chassis_joint.py) sit
# `side_inset` (4.5 mm) from the front wall and grow to a Ø7.80 boss, so they
# reach 8.4 mm inboard. ADR-0014 moves the keyboard 2.35 mm forward (the front
# margin falls from 10.0 to 7.65), leaving the plate's front border 0.75 mm
# inside that reach. The accepted fix -- notches in the plate border plus a
# scallop that cannot pierce the Well ring -- is ticket T1b/T3, not this
# derivation. The check stays in the report (and fails) until then.
KNOWN_PLATE_BORDER_CLASH = "slide-chassis-joint-clear"


def test_slider_checks_pass_by_default():
    _, config, components, _, placements = _data()
    report = run_slider_checks(_budget(config, components), config, placements)
    # Every check passes except the known front band-station clash above; any
    # other failure still fails this test.
    failures = {check.name for check in report.failures}
    assert failures <= {KNOWN_PLATE_BORDER_CLASH}, report.summary()
    assert report.goals["closed-face-height"] == pytest.approx(
        _budget(config, components).closed_face_height
    )


@pytest.mark.xfail(
    strict=True,
    reason="front band stations reach 8.4 mm inboard; the plate border starts "
    "at 7.65 (ADR-0014) -- notches/scallop are T1b/T3 (#10)",
)
def test_front_band_stations_clear_the_plate_border():
    _, config, components, _, placements = _data()
    report = run_slider_checks(_budget(config, components), config, placements)
    check = next(c for c in report.checks if c.name == KNOWN_PLATE_BORDER_CLASH)
    assert check.passed, check.message


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
        "slide-guide-stance",
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
