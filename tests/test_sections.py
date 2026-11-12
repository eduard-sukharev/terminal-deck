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

