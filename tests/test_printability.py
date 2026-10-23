"""Bed face and overhang checks per Section (ADR 0003)."""

import pytest

from utilities import cad_helpers

pytestmark = pytest.mark.skipif(
    not cad_helpers.cad_available(), reason="build123d not available"
)

from geometry.printability import (  # noqa: E402
    BED_DOWN, PrintOrientation, bed_face_area, check_bed_face, overhang_faces,
)
from utilities.validation import ValidationReport  # noqa: E402


def _tray():
    outer = cad_helpers.box_centered(60, 40, 20)
    cavity = cad_helpers.translate(cad_helpers.box_centered(56, 36, 20), 0, 0, 2)
    return cad_helpers.cut(outer, cavity)


def test_a_flat_floor_gives_a_bed_face():
    assert bed_face_area(_tray(), BED_DOWN) == pytest.approx(60 * 40)


def test_an_open_tray_flipped_has_only_a_rim_bed_face():
    # Open side down: the rim is the bed face (60*40 - 56*36).
    area = bed_face_area(_tray(), PrintOrientation((0, 0, 1)))
    assert area == pytest.approx(60 * 40 - 56 * 36)


def test_a_ball_has_no_bed_face():
    import build123d as b3d

    assert bed_face_area(b3d.Solid.make_sphere(10), BED_DOWN) == 0.0


def test_bed_face_check_is_hard():
    ok, bad = ValidationReport(), ValidationReport()
    check_bed_face("tray", _tray(), BED_DOWN, 100.0, ok)
    import build123d as b3d

    check_bed_face("ball", b3d.Solid.make_sphere(10), BED_DOWN, 100.0, bad)
    assert ok.passed
    assert [c.name for c in bad.failures] == ["bed-face:ball"]


def test_a_tiny_bed_face_is_not_enough():
    bad = ValidationReport()
    check_bed_face("tray", _tray(), PrintOrientation((0, 0, 1)), 1.0e4, bad)
    assert not bad.passed


def test_an_open_tray_has_no_overhang_floor_down():
    assert overhang_faces(_tray(), BED_DOWN) == []


def test_a_flat_roof_is_an_overhang():
    roof = cad_helpers.union(
        cad_helpers.box_centered(10, 10, 10),
        cad_helpers.translate(cad_helpers.box_centered(30, 10, 2), 0, 0, 4),
    )
    found = overhang_faces(roof, BED_DOWN)
    assert sum(f.area for f in found) == pytest.approx(2 * 10 * 10)  # two wings of 10 x 10
    assert all(f.angle_from_vertical > 45.0 for f in found)


def test_a_45_degree_chamfer_is_not_an_overhang():
    import build123d as b3d

    cone = b3d.Solid.make_cone(10, 30, 10)  # flares 63 degrees from vertical
    # A cone narrowing downward overhangs; one widening downward (a 45 degree flare) does not.
    assert overhang_faces(b3d.Solid.make_cone(20, 10, 10), BED_DOWN) == []
    assert overhang_faces(cone, BED_DOWN)
