"""Section model: the Split dataclass and the slider's per-part split config."""

import pytest

from components.keyboard_plate import KeyboardPlate
from geometry.split import check_build_volume, check_sections, split_sections
from utilities import cad_helpers
from utilities.config_loader import Split, load_config

PLATE = KeyboardPlate({
    "layout_source": "keyboard/layouts/jd40.json",
    "pitch": 19.05,
    "switch_family": "mx_alps",
    "stabilizer_family": "cherry",
    "wall_thickness": 2.0,
    "plate": {"thickness": 1.5, "wobble": 0.6, "corner_radius": 2.0},
    "keycap": {"profile": "xda"},
    "mounting": {"screw": "M2"},
})


def test_two_section_straight_split_has_one_seam():
    split = Split(sections=2, x=0.0, style="straight")
    (seam,) = split.seams()
    assert seam.x_range == (0.0, 0.0)
    assert seam.segments(100.0) == [(-50.0, 50.0, 0.0)]


def test_three_section_seams_mirror_about_the_centerline():
    split = Split(sections=3, x=40.0, style="stepped", step=4.0, steps=6)
    left, right = split.seams()
    assert left.x_range == (-44.0, -40.0)
    assert right.x_range == (40.0, 44.0)
    # A step left on one is a step right on the other.
    for (_, _, lx), (_, _, rx) in zip(left.segments(100.0), right.segments(100.0)):
        assert lx == pytest.approx(-rx)


def test_split_x_sign_is_ignored_for_three_sections():
    a = Split(sections=3, x=-40.0, style="stepped", step=4.0, steps=6).seams()
    b = Split(sections=3, x=40.0, style="stepped", step=4.0, steps=6).seams()
    assert [s.x_range for s in a] == [s.x_range for s in b]


@pytest.mark.parametrize("kwargs", [
    {"sections": 4},
    {"sections": 2, "style": "wavy"},
    {"sections": 2, "style": "stepped", "step": 0.0, "steps": 6},
    {"sections": 2, "style": "stepped", "step": 4.0, "steps": 1},
    {"sections": 2, "style": "straight", "step": 4.0},
])
def test_invalid_split_is_rejected(kwargs):
    with pytest.raises(ValueError):
        Split(**kwargs)


def test_slider_config_declares_section_splits():
    cfg = load_config("config/default.yaml")
    assert cfg.slide.split["chassis"].sections == 2
    assert cfg.slide.split["chassis"].style == "stepped"
    assert cfg.slide.split["screen_lid"].style == "stepped"
    assert cfg.slide.split["chassis"].step > 0


def test_the_keyboard_plate_split_knob_is_retired():
    """The plate splits between keys along its own Seam (ADR-0014, #9).

    A config ``keyboard_plate`` Split would be the straight ``x=0`` cut that
    passes through switch cutouts, so the knob does not exist any more.
    """
    cfg = load_config("config/default.yaml")
    assert "keyboard_plate" not in cfg.slide.split


# -- the plate Sections (ADR-0014, #9) ------------------------------------

needs_cad = pytest.mark.skipif(
    not cad_helpers.cad_available(), reason="build123d not available"
)
BUILD_VOLUME = (220.0, 220.0, 256.0)


@needs_cad
def test_plate_sections_split_the_whole_plate_losslessly():
    whole = PLATE.build()
    left, right = PLATE.plate_sections()
    assert check_sections(whole, [left, right]) == []
    assert cad_helpers.volume_mm3(left) + cad_helpers.volume_mm3(right) == (
        pytest.approx(cad_helpers.volume_mm3(whole))
    )


@needs_cad
def test_plate_sections_fit_the_build_volume():
    assert check_build_volume(
        dict(zip(("left", "right"), PLATE.plate_sections())), BUILD_VOLUME,
    ) == []


@needs_cad
def test_plate_sections_are_cut_on_the_seam_not_at_x0():
    """The stepped Seam reaches past x=0; the retired straight cut cannot."""
    left, right = PLATE.plate_sections()
    assert cad_helpers.bounding_box(left).xmax > 1.0
    assert cad_helpers.bounding_box(right).xmin < -1.0
    # And the Sections are the split of the Seam the model exposes.
    whole = PLATE.build()
    expected = split_sections(whole, [PLATE.seam], PLATE.seam_depth)
    for got, want in zip((left, right), expected):
        assert cad_helpers.volume_mm3(got) == pytest.approx(
            cad_helpers.volume_mm3(want)
        )



# -- the eared/notched plate Sections (ADR-0014, issue #14) ---------------


def _well_plate():
    """The slider's plate with its Well-mount pattern injected."""
    from components.slide import compute_slide_budget
    from geometry.well_mounts import PlateFrame, well_mounts
    from main import BuildPipeline

    pipeline = BuildPipeline()
    config = pipeline.load_config()
    components = pipeline.load_components()
    placements = pipeline.place_layout(components).placements()
    keep = components["keyboard"]
    placement = next(p for p in placements if p.component is keep)
    budget = compute_slide_budget(config, components)
    frame = PlateFrame.from_placement(
        placement,
        width=budget.well.plate_width,
        depth=budget.well.plate_depth,
    )
    mounts = well_mounts(config, budget, frame=frame)
    plate = components["keyboard"]._plate
    plate.set_well_mounts(mounts)
    return plate, mounts, frame, budget


@needs_cad
def test_eared_plate_sections_rejoin_and_each_ear_lands_on_one_section():
    from keyboard.validation import _point_in_polygon

    plate, mounts, frame, budget = _well_plate()
    whole = plate.build()
    left, right = plate.plate_sections()
    assert check_sections(whole, [left, right]) == []
    assert cad_helpers.volume_mm3(left) + cad_helpers.volume_mm3(right) == (
        pytest.approx(cad_helpers.volume_mm3(whole))
    )

    # Every ear is still connected to exactly one Section: a probe in the ear
    # (beside its clearance hole) is material in one Section and absent in the
    # other. Which one is the data model's own answer.
    left_poly, right_poly = plate.section_outlines
    probe = cad_helpers.box_centered(0.4, 0.4, 0.6)
    for mount in mounts.mounts:
        x, y = mount.plate_xy
        px, py = x + 1.75, y
        shape = cad_helpers.translate(probe, px, py, 0.75)
        volumes = [
            cad_helpers.volume_mm3(cad_helpers.intersect(section, shape))
            for section in (left, right)
        ]
        expected = 0 if _point_in_polygon(px, py, left_poly) else 1
        assert volumes[expected] > 0.0, f"{mount.name}: ear not in its Section"
        assert volumes[1 - expected] == pytest.approx(0.0, abs=1e-6), (
            f"{mount.name}: ear split across Sections"
        )


@needs_cad
def test_the_placed_plate_carries_material_and_a_hole_under_every_deck_boss():
    """Assembly probe (issue #19): the plate, placed, under the Deck's bosses.

    The bare plate is placed by the keyboard's own frame, then probed at each
    Deck boss's plan point (the world frame the Deck builds in). A Ø1 probe at
    the boss axis must pass through the plate's Ø2.20 clearance hole, and a
    small probe in the ear ring around it must find plate material -- i.e. the
    bottom-up screw has something to clamp.
    """
    plate, mounts, frame, budget = _well_plate()
    whole = plate.build()
    placed = cad_helpers.rotate_z(whole, frame.rotation)
    placed = cad_helpers.translate(
        placed, frame.cx, frame.cy, budget.well.plate_bottom
    )
    z = budget.well.plate_bottom + budget.well.plate_thickness / 2.0
    through = cad_helpers.cylinder_centered(1.0, budget.well.plate_thickness + 2.0)
    ring = cad_helpers.cylinder_centered(0.6, budget.well.plate_thickness + 2.0)
    for mount in mounts.mounts:
        # The clearance hole is clear right through the plate.
        hole = cad_helpers.translate(
            through, mount.world_xy[0], mount.world_xy[1], z + 1.0
        )
        assert cad_helpers.volume_mm3(
            cad_helpers.intersect(placed, hole)
        ) == pytest.approx(0.0, abs=1e-6), f"{mount.name}: no clearance hole"
        # Plate material under the boss, in the ear around the hole.
        for dx, dy in ((1.75, 0.0), (-1.75, 0.0), (0.0, 1.75), (0.0, -1.75)):
            local = (mount.plate_xy[0] + dx, mount.plate_xy[1] + dy)
            wx, wy = frame.local_to_world(*local)
            probe = cad_helpers.translate(ring, wx, wy, z)
            assert cad_helpers.volume_mm3(
                cad_helpers.intersect(placed, probe)
            ) > 0.0, f"{mount.name}: no plate material under the boss"
