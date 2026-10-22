"""Screw joints across the Seam (US28)."""

import pytest

from utilities import cad_helpers

pytestmark = pytest.mark.skipif(
    not cad_helpers.cad_available(), reason="build123d not available"
)

from geometry.seam_joint import add_joints, joint_spec  # noqa: E402
from geometry.split import check_halves, split_halves  # noqa: E402
from utilities.config_loader import Seam  # noqa: E402

WIDTH, DEPTH, HEIGHT, WALL = 120.0, 80.0, 20.0, 2.0


def _tray():
    outer = cad_helpers.box_centered(WIDTH, DEPTH, HEIGHT)
    cavity = cad_helpers.translate(
        cad_helpers.box_centered(WIDTH - 2 * WALL, DEPTH - 2 * WALL, HEIGHT),
        0, 0, WALL,
    )
    return cad_helpers.cut(outer, cavity)


@pytest.mark.parametrize("seam", [Seam(0.0, 0.0, 1), Seam(0.0, 4.0, 6)])
def test_jointed_tray_still_splits_into_connected_halves(seam):
    spec = joint_spec("M2")
    tray = add_joints(_tray(), seam, DEPTH, WALL, spec, floor_top=-HEIGHT / 2 + WALL)
    left, right = split_halves(tray, seam, DEPTH)
    assert check_halves(tray, left, right) == []


def test_each_half_receives_part_of_every_lug():
    seam = Seam(0.0, 4.0, 6)
    spec = joint_spec("M2")
    plain = _tray()
    jointed = add_joints(plain, seam, DEPTH, WALL, spec, floor_top=-HEIGHT / 2 + WALL)
    pl, pr = split_halves(plain, seam, DEPTH)
    jl, jr = split_halves(jointed, seam, DEPTH)
    assert jl.volume > pl.volume
    assert jr.volume > pr.volume


def test_lug_is_bored_on_both_sides_of_the_seam():
    seam = Seam(0.0, 0.0, 1)
    spec = joint_spec("M2")
    solid = _tray()
    unbored = add_joints(solid, seam, DEPTH, WALL, spec, floor_top=-HEIGHT / 2 + WALL)
    probe_l = cad_helpers.translate(
        cad_helpers.rotate_y(cad_helpers.cylinder_centered(0.5, 1.0), 90),
        -1.0, -(DEPTH / 2 - WALL - spec.size / 2), -HEIGHT / 2 + WALL + spec.size / 2,
    )
    probe_r = cad_helpers.translate(probe_l, 2.0, 0, 0)
    for probe in (probe_l, probe_r):
        assert cad_helpers.volume_mm3(cad_helpers.intersect(unbored, probe)) == pytest.approx(0, abs=1e-6)
