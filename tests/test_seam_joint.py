"""Screw joints across the Seam (ADR 0003)."""

import pytest

from utilities import cad_helpers

pytestmark = pytest.mark.skipif(
    not cad_helpers.cad_available(), reason="build123d not available"
)

from geometry.seam_joint import add_joints, joint_spec, lug_footprint, plan_joints  # noqa: E402
from geometry.split import check_sections, split_sections  # noqa: E402
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
def test_jointed_tray_still_splits_into_connected_sections(seam):
    spec = joint_spec("M2")
    tray = add_joints(_tray(), seam, DEPTH, WALL, spec, floor_top=-HEIGHT / 2 + WALL)
    sections = split_sections(tray, [seam], DEPTH)
    assert check_sections(tray, sections) == []


def test_each_section_receives_part_of_every_lug():
    seam = Seam(0.0, 4.0, 6)
    spec = joint_spec("M2")
    plain = _tray()
    jointed = add_joints(plain, seam, DEPTH, WALL, spec, floor_top=-HEIGHT / 2 + WALL)
    pl, pr = split_sections(plain, [seam], DEPTH)
    jl, jr = split_sections(jointed, [seam], DEPTH)
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


FLOOR_TOP = -HEIGHT / 2 + WALL


def test_planned_sites_are_two_per_seam_front_and_rear_first():
    seam = Seam(0.0, 4.0, 6)
    sites = plan_joints(seam, DEPTH, WALL, joint_spec("M2"), FLOOR_TOP)
    assert len(sites) == 2
    assert sites[0][1] < 0 < sites[1][1]


def test_a_keepout_over_a_site_moves_the_lug_to_the_next_site():
    seam = Seam(0.0, 4.0, 6)
    spec = joint_spec("M2")
    first = plan_joints(seam, DEPTH, WALL, spec, FLOOR_TOP)
    rect = lug_footprint(spec, *first[0][:2], WALL, first[0][2])
    moved = plan_joints(seam, DEPTH, WALL, spec, FLOOR_TOP, keepouts=[rect])
    assert first[0] not in moved
    assert len(moved) == 2


def test_lugs_keep_a_clearance_from_keepouts():
    seam = Seam(0.0, 4.0, 6)
    spec = joint_spec("M2")
    first = plan_joints(seam, DEPTH, WALL, spec, FLOOR_TOP)
    x0, x1, y0, y1 = lug_footprint(spec, *first[0][:2], WALL, first[0][2])
    near = (x1 + 0.5, x1 + 3.0, y0, y1)  # 0.5 mm off the lug
    assert plan_joints(seam, DEPTH, WALL, spec, FLOOR_TOP, keepouts=[near])[0] == first[0]
    assert plan_joints(seam, DEPTH, WALL, spec, FLOOR_TOP, clearance=1.0, keepouts=[near])[0] != first[0]


def test_too_few_clear_sites_fails():
    seam = Seam(0.0, 0.0, 1)
    wall_to_wall = (-WIDTH, WIDTH, -DEPTH, DEPTH)
    with pytest.raises(ValueError):
        plan_joints(seam, DEPTH, WALL, joint_spec("M2"), FLOOR_TOP, keepouts=[wall_to_wall])
