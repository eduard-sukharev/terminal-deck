"""Edge treatment: concave joints, bed-face chamfer (ADR 0003)."""

import pytest

from utilities import cad_helpers

pytestmark = pytest.mark.skipif(
    not cad_helpers.cad_available(), reason="build123d not available"
)

from geometry.edge_treatment import (  # noqa: E402
    bed_chamfer, concave_edges, relieve_concave_joints,
)
from geometry.printability import BED_DOWN, PrintOrientation  # noqa: E402
from utilities.validation import ValidationReport  # noqa: E402

WALL = 2.0


def _tray():
    outer = cad_helpers.translate(cad_helpers.box_centered(60, 40, 20), 0, 0, 10)
    cavity = cad_helpers.translate(cad_helpers.box_centered(56, 36, 20), 0, 0, 12)
    return cad_helpers.cut(outer, cavity)


def _tray_with_boss():
    boss = cad_helpers.translate(cad_helpers.cylinder_centered(6, 12), 10, 5, 2 + 6)
    return cad_helpers.union(_tray(), boss)


def test_an_open_tray_has_its_floor_perimeter_as_concave_edges():
    edges = concave_edges(_tray())
    # Floor meets four walls (4 edges) and the four wall-wall corners (4 verticals).
    assert len(edges) == 8
    horizontal = [e for e in edges if e.horizontal(BED_DOWN)]
    assert len(horizontal) == 4


def test_a_boss_adds_a_circular_floor_joint():
    assert len(concave_edges(_tray_with_boss())) == 8 + 1


def test_a_box_has_no_concave_edges():
    assert concave_edges(cad_helpers.box_centered(10, 10, 10)) == []


def test_relief_adds_material_at_each_concave_joint():
    tray = _tray_with_boss()
    report = ValidationReport()
    treated = relieve_concave_joints(tray, BED_DOWN, WALL * 0.5, report)
    assert treated.volume > tray.volume
    assert cad_helpers.solid_count(treated) == 1
    assert report.warnings == []


def test_relief_volume_matches_a_chamfer_of_the_requested_size():
    # Four floor-wall edges chamfered at 1 mm: 0.5 * 1 * 1 mm^2 each along the
    # straight run; verticals/fillets add a little. Bound it rather than pin it.
    tray = _tray()
    treated = relieve_concave_joints(tray, BED_DOWN, 1.0, ValidationReport())
    added = treated.volume - tray.volume
    perimeter = 2 * (56 + 36)
    assert 0.4 * perimeter < added < 0.7 * perimeter


def test_horizontal_joints_are_chamfered_not_filleted():
    # A fillet on a floor joint adds less than a 45 degree chamfer of equal size.
    tray = _tray()
    chamfered = relieve_concave_joints(tray, BED_DOWN, 1.0, ValidationReport())
    flat_added = chamfered.volume - tray.volume
    assert flat_added > 0
    faces_that_are_planar_and_slanted = [
        f for f in cad_helpers.faces(chamfered)
        if cad_helpers.is_planar(f) and 0.1 < abs(cad_helpers.face_normal(f)[2]) < 0.9
    ]
    assert len(faces_that_are_planar_and_slanted) >= 4


def test_an_edge_that_does_not_fit_is_skipped_with_a_soft_warning(monkeypatch):
    tray = _tray_with_boss()
    bad_key = next(e for e in concave_edges(tray) if not e.vertical(BED_DOWN)).info.key
    real = cad_helpers.chamfer_edges

    def picky(shape, infos, size):
        if any(i.key == bad_key for i in infos):
            raise ValueError("does not fit")
        return real(shape, infos, size)

    monkeypatch.setattr(cad_helpers, "chamfer_edges", picky)
    report = ValidationReport()
    treated = relieve_concave_joints(tray, BED_DOWN, 1.0, report)
    assert report.passed              # SOFT: never fails the build
    assert len(report.warnings) == 1  # only the one edge is skipped...
    assert "skipped" in report.warnings[0]
    assert treated.volume > tray.volume  # ...the rest are still treated


def test_a_real_tight_spot_does_not_abort_the_treatment():
    # A 1 mm chamfer on a fin thinner than the chamfer: whatever OCC does, the
    # call returns a valid solid and never raises.
    sliver = cad_helpers.union(
        cad_helpers.box_centered(30, 30, 0.4),
        cad_helpers.translate(cad_helpers.box_centered(0.4, 30, 5), 0, 0, 2.5),
    )
    treated = relieve_concave_joints(sliver, BED_DOWN, 1.0, ValidationReport())
    assert treated.is_valid and treated.volume >= sliver.volume


def test_bed_chamfer_trims_the_bed_face_outer_edge():
    plate = cad_helpers.box_centered(40, 30, 6)
    chamfered = bed_chamfer(plate, BED_DOWN, 0.5, ValidationReport())
    assert chamfered.volume == pytest.approx(plate.volume - 0.5 * 0.5 * 0.5 * 2 * (40 + 30), rel=1e-3)
    bb = cad_helpers.bounding_box(chamfered)
    assert bb.zmin == pytest.approx(-3.0)


def test_bed_chamfer_follows_the_declared_orientation():
    plate = cad_helpers.box_centered(40, 30, 6)
    up = bed_chamfer(plate, PrintOrientation((0, 0, 1)), 0.5, ValidationReport())
    down = bed_chamfer(plate, BED_DOWN, 0.5, ValidationReport())
    assert up.volume == pytest.approx(down.volume, rel=1e-6)
    # Mirror images: the chamfered edges are at opposite ends of Z.
    top_faces = [f for f in cad_helpers.faces(up) if cad_helpers.face_center(f)[2] > 2.9 and cad_helpers.face_area(f) > 1000]
    assert top_faces and cad_helpers.face_area(top_faces[0]) < 40 * 30
