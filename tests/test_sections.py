"""Section model: the Split dataclass and the slider's per-part split config."""

import pytest

from utilities.config_loader import Split, load_config


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
    assert cfg.slide.split["keyboard_plate"].style == "straight"
    assert cfg.slide.split["chassis"].step > 0
