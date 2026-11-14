"""Behaviour of the Section splitter (ADR 0003)."""

import pytest

from utilities import cad_helpers

pytestmark = pytest.mark.skipif(
    not cad_helpers.cad_available(), reason="build123d not available"
)

from geometry.split import check_build_volume, check_sections, split_sections  # noqa: E402
from utilities.config_loader import Seam, Split  # noqa: E402

WIDTH, DEPTH, HEIGHT = 236.0, 118.0, 20.0

THREE = Split(sections=3, x=40.0, style="stepped", step=4.0, steps=6).seams(DEPTH)
TWO_STRAIGHT = Split(sections=2, x=0.0, style="straight").seams(DEPTH)
TWO_STEPPED = Split(sections=2, x=-15.0, style="stepped", step=3.0, steps=5).seams(DEPTH)


def _slab():
    return cad_helpers.box_centered(WIDTH, DEPTH, HEIGHT)


@pytest.mark.parametrize("seams", [TWO_STRAIGHT, TWO_STEPPED, THREE])
def test_sections_rejoin_without_gap_or_overlap(seams):
    whole = _slab()
    sections = split_sections(whole, seams, DEPTH)
    assert len(sections) == len(seams) + 1
    assert sum(s.volume for s in sections) == pytest.approx(whole.volume, rel=1e-9)
    assert check_sections(whole, sections) == []


@pytest.mark.parametrize("seams", [TWO_STRAIGHT, THREE])
def test_each_section_is_one_connected_solid(seams):
    for section in split_sections(_slab(), seams, DEPTH):
        assert cad_helpers.solid_count(section) == 1


def test_three_sections_are_ordered_left_to_right():
    left, center, right = split_sections(_slab(), THREE, DEPTH)
    assert cad_helpers.bounding_box(left).xmax <= cad_helpers.bounding_box(center).xmin + 4.0 + 1e-6
    assert cad_helpers.bounding_box(center).xmax <= cad_helpers.bounding_box(right).xmin + 4.0 + 1e-6
    assert cad_helpers.bounding_box(left).xmin < cad_helpers.bounding_box(center).xmin


def test_three_sections_of_a_stepped_pair_are_mirror_images():
    left, center, right = split_sections(_slab(), THREE, DEPTH)
    assert left.volume == pytest.approx(right.volume, rel=1e-9)


def test_stepped_seam_is_not_a_straight_cut():
    straight = split_sections(_slab(), TWO_STRAIGHT, DEPTH)[0]
    stepped = split_sections(_slab(), TWO_STEPPED, DEPTH)[0]
    assert cad_helpers.face_count(stepped) > cad_helpers.face_count(straight)


def test_sections_fit_the_build_volume():
    named = dict(zip("lcr", split_sections(_slab(), THREE, DEPTH)))
    assert check_build_volume(named) == []


def test_unsplit_wide_part_fails_build_volume():
    assert check_build_volume({"whole": _slab()})


def test_disconnected_section_is_reported():
    # Two detached islands on the left of the Seam: that Section is 2 solids.
    part = cad_helpers.union(
        cad_helpers.translate(cad_helpers.box_centered(5, 5, 5), -90, 0, 0),
        cad_helpers.translate(cad_helpers.box_centered(5, 5, 5), -60, 0, 0),
    )
    sections = split_sections(part, TWO_STRAIGHT, DEPTH)
    assert any("connected" in e for e in check_sections(part, sections))


def test_step_must_be_positive_count_when_stepping():
    with pytest.raises(ValueError):
        Seam.stepped(0.0, 4.0, 0, DEPTH)
