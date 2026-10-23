"""Section model: per-part split config, mirrored Seams, target names (ADR 0003)."""

import pytest

from utilities.config_loader import Seam, Split, build_config, load_config
from utilities.targets import SECTION_NAMES, requested_sections, resolve_targets


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


def test_default_config_declares_section_splits():
    cfg = load_config("config/default.yaml")
    assert cfg.split["tray"].sections == 3
    assert cfg.split["lid_shell"].sections == 3
    assert cfg.split["deck"].sections == 2 and cfg.split["deck"].style == "straight"
    assert cfg.split["bezel"].sections == 2 and cfg.split["bezel"].style == "straight"
    assert cfg.split["deck"].x == 0.0 and cfg.split["bezel"].x == 0.0
    # Tray and Lid shell Seams are tuned per part (see config/default.yaml).
    assert cfg.split["tray"].x > 0 and cfg.split["lid_shell"].x > 0


def test_section_names():
    assert SECTION_NAMES["base_bottom"] == ("left", "center", "right")
    assert SECTION_NAMES["lid_shell"] == ("left", "center", "right")
    assert SECTION_NAMES["base_top"] == ("left", "right")
    assert SECTION_NAMES["lid_bezel"] == ("left", "right")
    assert SECTION_NAMES["keyboard_plate"] == ("left", "right")


def test_center_target_resolves_to_its_part():
    buckets, _ = resolve_targets(["base_bottom_center", "lid_shell_center"], set())
    assert buckets == {"base_bottom", "lid_shell"}


def test_center_target_on_a_two_section_part_is_unknown():
    with pytest.raises(ValueError, match="unknown target"):
        resolve_targets(["base_top_center"], set())


def test_center_section_alone_narrows_the_export():
    assert requested_sections(["base_bottom_center"]) == {"base_bottom_center"}
    assert requested_sections(["base_bottom_center", "base"]) == set()
