"""Behaviour of the left/right Half splitter (ADR 0001)."""

import pytest

from utilities import cad_helpers

pytestmark = pytest.mark.skipif(
    not cad_helpers.cad_available(), reason="build123d not available"
)

from geometry.split import check_build_volume, split_halves  # noqa: E402
from utilities.config_loader import Seam  # noqa: E402

WIDTH, DEPTH, HEIGHT = 236.0, 118.0, 20.0


def _slab():
    return cad_helpers.box_centered(WIDTH, DEPTH, HEIGHT)


@pytest.mark.parametrize("seam", [
    Seam(x=0.0, step=0.0, steps=1),
    Seam(x=0.0, step=4.0, steps=6),
    Seam(x=-15.0, step=3.0, steps=5),
])
def test_halves_rejoin_without_gap_or_overlap(seam):
    whole = _slab()
    left, right = split_halves(whole, seam, DEPTH)
    assert left.volume + right.volume == pytest.approx(whole.volume, rel=1e-9)
    assert cad_helpers.volume_mm3(cad_helpers.intersect(left, right)) == pytest.approx(0, abs=1e-6)
    assert cad_helpers.volume_mm3(cad_helpers.union(left, right)) == pytest.approx(whole.volume, rel=1e-9)


def test_each_half_is_one_connected_solid():
    left, right = split_halves(_slab(), Seam(x=0.0, step=4.0, steps=6), DEPTH)
    assert cad_helpers.solid_count(left) == 1
    assert cad_helpers.solid_count(right) == 1


def test_stepped_seam_is_not_a_straight_cut():
    straight = split_halves(_slab(), Seam(x=0.0, step=0.0, steps=1), DEPTH)[0]
    stepped = split_halves(_slab(), Seam(x=0.0, step=4.0, steps=6), DEPTH)[0]
    assert cad_helpers.face_count(stepped) > cad_helpers.face_count(straight)


def test_halves_fit_the_build_volume():
    left, right = split_halves(_slab(), Seam(x=0.0, step=4.0, steps=6), DEPTH)
    assert check_build_volume({"left": left, "right": right}) == []


def test_unsplit_wide_part_fails_build_volume():
    assert check_build_volume({"whole": _slab()})


def test_step_must_be_positive_count_when_stepping():
    with pytest.raises(ValueError):
        Seam(x=0.0, step=4.0, steps=0)
