"""Edge treatment: concave joints, bed-face chamfer (ADR 0003)."""

import math

import pytest

from utilities import cad_helpers

pytestmark = pytest.mark.skipif(
    not cad_helpers.cad_available(), reason="build123d not available"
)

from geometry.edge_treatment import (  # noqa: E402
    bed_chamfer, boss_base_edges, chamfer_cone_cut, column_junction_edges,
    concave_edges, cone_cut_edges, fillet_boss_bases, fillet_junctions,
    merge_column_walls, rect_base_edges, rect_junction_edges,
    relieve_concave_joints, web_base_edges, web_junction_edges,
)
from geometry.printability import BED_DOWN, PrintOrientation  # noqa: E402
from utilities.validation import ValidationReport  # noqa: E402

WALL = 2.0


def _plate_with_conical_hole():
    plate = cad_helpers.translate(
        cad_helpers.box_centered(40, 40, 10), 0, 0, 5
    )  # z 0..10
    cone = cad_helpers.translate(
        cad_helpers.frustum_centered(12, 6, 14), 0, 0, 5
    )  # wider at the bed
    return cad_helpers.cut(plate, cone)


def test_cone_cut_edges_split_the_bed_rim_from_the_interior_ring():
    rims, lips = cone_cut_edges(_plate_with_conical_hole(), 15.0, 0.0)
    assert not lips
    # only the mouth ring at the bed: the top ring is an interior edge and
    # is never picked, and no straight plate edge is selected either
    assert rims
    assert all(abs(i.key[2]) < 0.01 for i in rims)
    assert all(i.curve_type == "circle" for i in rims)


def test_chamfer_cone_cut_chamfers_the_bed_rim_not_fillets_it():
    plate = _plate_with_conical_hole()
    rims, lips = cone_cut_edges(plate, 15.0, 0.0)
    assert rims and not lips
    before = sorted(i.length for i in rims)
    report = ValidationReport()
    out = chamfer_cone_cut(plate, 15.0, 0.0, 0.5, report)
    assert not report.warnings
    assert cad_helpers.volume_mm3(out) < cad_helpers.volume_mm3(plate)
    # A 45 degree chamfer removes more material than a fillet of equal size.
    filleted = cad_helpers.fillet_edges(plate, rims, 0.5)
    assert cad_helpers.volume_mm3(out) < cad_helpers.volume_mm3(filleted)
    # The bed opening grows by the chamfer size on every side: the chamfer
    # face is itself a cone, so the new bed boundary is a circle of the larger
    # radius (never a rounded torus).
    after_rims, after_lips = cone_cut_edges(out, 15.0, 0.0)
    assert not after_lips
    assert sorted(i.length for i in after_rims) == pytest.approx(
        [length + 2.0 * math.pi * 0.5 for length in before]
    )
    # the plate's own wall/floor edges stay straight
    lines = 0
    for face in cad_helpers.faces(out):
        for wire in face.wires():
            for edge in wire.edges():
                info = cad_helpers.edge_info(edge)
                if (
                    info.curve_type == "line"
                    and abs(info.key[2]) < 0.01
                    and info.length > 30.0
                ):
                    lines += 1
    assert lines >= 4


def _tray():
    outer = cad_helpers.translate(cad_helpers.box_centered(60, 40, 20), 0, 0, 10)
    cavity = cad_helpers.translate(cad_helpers.box_centered(56, 36, 20), 0, 0, 12)
    return cad_helpers.cut(outer, cavity)


def _tray_with_boss():
    boss = cad_helpers.translate(cad_helpers.cylinder_centered(6, 12), 10, 5, 2 + 6)
    return cad_helpers.union(_tray(), boss)


def _tray_with_rect():
    """A bridged boss: a rectangle on the tray floor, its long axis along Y."""
    boss = cad_helpers.rect_prism(3.5, 4.0, 19.0, 12.0, x=10.0, z=2.0)
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


def _wall_column(x: float = 0.0, y: float = 15.5, diameter: float = 7.3):
    """``_tray()`` with a column crossing its front wall face (cavity face 18).

    The joint stations sit 2.5 mm inboard of the cavity face, so the column's
    axis is at 15.5 and its radius (3.65) reaches 1.15 mm past that face.
    """
    return cad_helpers.union(
        _tray(),
        cad_helpers.translate(
            cad_helpers.cylinder_centered(diameter, 18.0), x, y, 11.0
        ),
    )


def _column(x: float, y: float, diameter: float):
    """A column's plan axis and its radius band -- one diameter, no frustum."""
    return (x, y, diameter / 2.0, diameter / 2.0)


def _column_probe(shape, half: float, face: float, z: float) -> list[float]:
    """Material in the corner just past the chord and just off the wall face."""
    out = []
    for dx in (0.8, 1.1):
        for dy in (0.3, 0.6):
            probe = cad_helpers.translate(
                cad_helpers.box_centered(0.2, 0.2, 0.4), half + dx, face - dy, z
            )
            out.append(cad_helpers.volume_mm3(cad_helpers.intersect(shape, probe)))
    return out


def test_column_junction_edges_finds_the_two_wall_chords():
    """ADR-0024: only the vertical chords on a front/rear cavity wall face."""
    column = _column(0.0, 15.5, 7.3)
    edges = column_junction_edges(_wall_column(), [column], 18.0)
    assert len(edges) == 2
    half = math.sqrt((7.3 / 2.0) ** 2 - 2.5**2)
    assert sorted(round(e.key[0], 2) for e in edges) == [
        round(-half, 2), round(half, 2)
    ]
    assert all(abs(abs(e.key[1]) - 18.0) < 1e-2 for e in edges)
    assert all(e.curve_type == "line" for e in edges)


def test_a_column_on_an_x_wall_keeps_its_chords_sharp():
    """The X walls, the corner chamfer and the Well ring are never picked."""
    column = _column(25.5, 0.0, 7.3)
    shape = _wall_column(x=25.5, y=0.0)
    assert column_junction_edges(shape, [column], 18.0) == []


def test_a_frustum_chord_is_found_through_its_radius_band():
    """The Tray's column tapers below the cone's neck: its chord tilts, still Z."""
    shape = cad_helpers.union(
        _tray(),
        cad_helpers.translate(
            cad_helpers.frustum_centered(7.8, 7.3, 18.0), 0.0, 15.5, 11.0
        ),
    )
    column = (0.0, 15.5, 7.3 / 2.0, 7.8 / 2.0)
    edges = column_junction_edges(shape, [column], 18.0)
    assert len(edges) == 2
    report = ValidationReport()
    merged = merge_column_walls(shape, [column], 18.0, 1.5, report)
    assert report.warnings == []
    assert merged.volume > shape.volume


def test_merge_column_walls_fills_the_reentrant_corner():
    """The fillet adds a bead beside each chord -- material where there was air."""
    column = _column(0.0, 15.5, 7.3)
    shape = _wall_column()
    half = math.sqrt((7.3 / 2.0) ** 2 - 2.5**2)

    report = ValidationReport()
    merged = merge_column_walls(shape, [column], 18.0, 1.5, report)
    assert report.warnings == []
    assert merged.volume > shape.volume
    assert column_junction_edges(merged, [column], 18.0) == []

    before = _column_probe(shape, half, 18.0, 11.0)
    after = _column_probe(merged, half, 18.0, 11.0)
    assert max(before) < 1e-9, "the sharp corner is air beside the chord"
    assert min(after) > 0.0, "the merged corner is filled beside the chord"


def _corner_web_shape():
    """A tray corner with a column and its web into the X wall (ADR-0029)."""
    from geometry.corner_web import CornerWeb

    web = CornerWeb(x=24.0, y=15.5, radius=3.65, x_wall=28.0, y_wall=18.0)
    column = cad_helpers.translate(
        cad_helpers.cylinder_centered(7.3, 18.0), 24.0, 15.5, 11.0
    )
    x0, x1, y0, y1 = web.plan()
    prism = cad_helpers.box_centered(x1 - x0, y1 - y0, 18.0)
    prism = cad_helpers.translate(
        prism, (x0 + x1) / 2.0, (y0 + y1) / 2.0, 11.0
    )
    return cad_helpers.union(_tray(), column, prism), web


def test_web_junction_edges_finds_the_x_wall_chord():
    """ADR-0029: the web's inboard face crosses the X wall in one chord."""
    shape, web = _corner_web_shape()
    edges = web_junction_edges(shape, [web])
    assert len(edges) == 1
    assert edges[0].curve_type == "line"
    assert abs(edges[0].key[0] - 28.0) < 1e-2
    assert abs(edges[0].key[1] - 11.85) < 1e-2


def test_web_base_edges_finds_the_floor_edge():
    """ADR-0029: the web meets the floor in one straight edge along X."""
    shape, web = _corner_web_shape()
    edges = web_base_edges(shape, [web], 2.0, 1.0, BED_DOWN)
    assert len(edges) == 1
    assert abs(edges[0].key[1] - 11.85) < 1e-2
    assert abs(edges[0].key[2] - 2.0) < 1e-2


def _treated_stepped_sections(extra: float):
    from geometry.edge_treatment import round_seam_corners
    from geometry.split import split_sections
    from utilities.config_loader import Seam

    seam = Seam.stepped(0.0, 4.0, 4, 40.0)
    sections = split_sections(_tray(), [seam], 40.0)
    out = []
    for section in sections:
        r = ValidationReport()
        section = relieve_concave_joints(section, BED_DOWN, 1.0, r)
        section = round_seam_corners(section, BED_DOWN, [seam], 40.0, 1.0 + extra, r)
        assert not r.warnings, r.warnings
        out.append(section)
    return out


def test_seam_step_corners_point_at_both_sides_of_every_jog():
    from geometry.edge_treatment import seam_corner_points
    from utilities.config_loader import Seam

    points = seam_corner_points([Seam.stepped(0.0, 4.0, 4, 40.0)], 40.0)
    assert sorted(points) == sorted([(0.0, -10.0), (4.0, -10.0), (4.0, 0.0), (0.0, 0.0),
                                     (0.0, 10.0), (4.0, 10.0)])
    assert seam_corner_points([Seam.straight(0.0)], 40.0) == []


def test_rounded_tabs_fit_the_filleted_notches():
    left, right = _treated_stepped_sections(extra=0.5)
    assert cad_helpers.volume_mm3(cad_helpers.intersect(left, right)) < 1e-6


def test_sharp_tabs_clash_with_the_filleted_notches():
    from geometry.split import split_sections
    from utilities.config_loader import Seam

    seam = Seam.stepped(0.0, 4.0, 4, 40.0)
    left, right = (relieve_concave_joints(s, BED_DOWN, 1.0, ValidationReport())
                   for s in split_sections(_tray(), [seam], 40.0))
    assert cad_helpers.volume_mm3(cad_helpers.intersect(left, right)) > 1e-3


def test_boss_base_edges_finds_the_ring_a_boss_springs_from():
    """ADR-0025: the circular reentrant edge under a boss on a plane."""
    edges = boss_base_edges(_tray_with_boss(), [(10.0, 5.0, 3.0, 3.0)], 2.0, 1.0)
    assert len(edges) == 1
    assert edges[0].curve_type == "circle"
    assert edges[0].key[2] == pytest.approx(2.0)


def test_a_boss_growing_away_from_the_bed_keeps_its_base_sharp():
    """The cove would face the bed, so the round needs support: not selected."""
    up = PrintOrientation((0, 0, 1))
    assert boss_base_edges(_tray_with_boss(), [(10.0, 5.0, 3.0, 3.0)], 2.0, 1.0, up) == []


def test_fillet_boss_bases_rounds_the_floor_ring():
    shape = _tray_with_boss()
    report = ValidationReport()
    out = fillet_boss_bases(shape, [(10.0, 5.0, 3.0, 3.0)], 2.0, 1.0, 1.0, report)
    assert report.warnings == []
    assert out.volume > shape.volume
    assert boss_base_edges(out, [(10.0, 5.0, 3.0, 3.0)], 2.0, 1.0) == []


def test_rect_base_edges_finds_the_bridge_floor_edges():
    """ADR-0026: a bridged boss meets its base plane in a rectangle outline."""
    rect = (10.0, 4.0, 19.0, 3.5)
    edges = rect_base_edges(_tray_with_rect(), [rect], 2.0, 1.0)
    assert edges
    assert all(e.key[2] == pytest.approx(2.0) for e in edges)


def test_rect_junction_edges_finds_the_wall_chords():
    """The rectangle's long sides meet the tray wall in two vertical chords."""
    rect = (10.0, 4.0, 19.0, 3.5)
    edges = rect_junction_edges(_tray_with_rect(), [rect], 18.0)
    assert len(edges) == 2
    assert all(e.curve_type == "line" for e in edges)


def test_fillet_junctions_rounds_the_rect_base():
    """The combined pass eases a bridged boss's base in one go."""
    rect = (10.0, 4.0, 19.0, 3.5)
    shape = _tray_with_rect()
    bases = rect_base_edges(shape, [rect], 2.0, 1.0)
    report = ValidationReport()
    out = fillet_junctions(shape, [], bases, 1.0, 1.0, report)
    assert report.warnings == []
    assert out.volume > shape.volume
    assert rect_base_edges(out, [rect], 2.0, 1.0) == []
