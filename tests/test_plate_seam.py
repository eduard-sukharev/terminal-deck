"""Keyboard plate Seam: follows the key-column gap nearest the center.

The plate splits **between keys** (ADR-0003, ADR-0014): the Seam is the
row-jogging path from :func:`plate_seam`, never the straight ``x=0`` cut that
passed through switch cutouts (issue #9). The model exposes the Seam and the
two Section outlines; a Seam that crosses a cutout is a HARD failure.
"""

import json
from pathlib import Path

import pytest

from keyboard import parse_layout
from keyboard.geometry import plate as plate_module
from keyboard.geometry.plate import generate
from keyboard.geometry.seam import (
    RowSeam,
    plate_seam,
    seam_conflicts,
    section_outlines,
)
from keyboard.validation import _point_in_polygon


def _model():
    raw = json.loads(Path("keyboard/layouts/jd40.json").read_text())
    return generate(
        parse_layout(raw, pitch=19.05),
        switch_family="mx_alps", stabilizer_family="cherry",
        plate_thickness=1.5, wall=2.0, keycap_profile="xda", wobble=0.6,
        corner_radius=8.0,
    )


def test_seam_cuts_no_switch_or_stabilizer_cutout():
    model = _model()
    assert seam_conflicts(model, plate_seam(model)) == []


def test_seam_runs_through_gap_nearest_center_per_row():
    model = _model()
    xs = [x for _, _, x in plate_seam(model).segments(model.metadata.height)]
    assert len(xs) == 4  # one segment per key row
    assert min(abs(x) for x in xs) < 6.0  # some rows split right at the middle


def test_seam_segments_tile_the_plate_depth():
    model = _model()
    depth = model.metadata.height
    segs = plate_seam(model).segments(depth)
    assert segs[0][0] == -depth / 2 and segs[-1][1] == depth / 2
    assert all(a[1] == b[0] for a, b in zip(segs, segs[1:]))


def test_conflict_detected_for_a_straight_cut_through_keys():
    from keyboard.geometry.seam import RowSeam
    model = _model()
    assert seam_conflicts(model, RowSeam(((-38.4, 38.4, 20.0),)))


# -- the Seam on the model and the two Section outlines -------------------


def _area(poly: list[tuple[float, float]]) -> float:
    """Shoelace area (mm^2) of a closed polygon."""
    return abs(sum(
        a[0] * b[1] - b[0] * a[1] for a, b in zip(poly, poly[1:] + poly[:1])
    )) / 2.0


def test_the_model_exposes_the_seam_it_splits_at():
    model = _model()
    assert model.seam is not None
    assert model.seam == plate_seam(model)
    assert seam_conflicts(model, model.seam) == []


def test_the_model_exposes_two_section_outlines():
    model = _model()
    left, right = model.section_outlines
    assert len(left) > 3 and len(right) > 3
    # They partition the plate: no area is lost, doubled or invented.
    assert _area(left) + _area(right) == pytest.approx(_area(model.plate_outline))
    # Left is left of right.
    assert max(x for x, _ in left) <= max(x for x, _ in right)


def test_every_cutout_is_wholly_inside_one_section():
    """The regression from issue #9: no switch or stabilizer crosses the cut."""
    model = _model()
    left, right = model.section_outlines
    for cut in list(model.switch_cutouts) + list(model.stabilizer_cutouts):
        verts = [(cut.x + vx, cut.y + vy) for vx, vy in cut.vertices]
        in_left = [_point_in_polygon(x, y, left) for x, y in verts]
        in_right = [_point_in_polygon(x, y, right) for x, y in verts]
        assert all(in_left) != all(in_right), (
            f"cutout at ({cut.x:.2f}, {cut.y:.2f}) is crossed by the Seam"
        )


def test_every_switch_center_is_on_exactly_one_side():
    model = _model()
    left, right = model.section_outlines
    for x, y in model.metadata.switch_centers:
        assert _point_in_polygon(x, y, left) != _point_in_polygon(x, y, right)


def test_the_seam_polyline_is_a_jogging_staircase():
    model = _model()
    poly = model.seam.polyline(model.metadata.height)
    assert poly[0][1] == pytest.approx(-model.metadata.height / 2)
    assert poly[-1][1] == pytest.approx(model.metadata.height / 2)
    # Every vertex is a plain corner: exactly one coordinate changes per step.
    for a, b in zip(poly, poly[1:]):
        assert (a[0] == b[0]) != (a[1] == b[1])
    xs = {x for x, _ in poly}
    assert len(xs) > 1, "a straight Seam is the bug (#9), not the fix"


def test_section_outlines_run_to_the_plate_edges():
    """The Sections keep the plate's real outline (rounded corners included)."""
    model = _model()

    def bbox(poly):
        xs = [x for x, _ in poly]
        ys = [y for _, y in poly]
        return (min(xs), min(ys), max(xs), max(ys))

    px0, py0, px1, py1 = bbox(model.plate_outline)
    left = bbox(model.section_outlines[0])
    right = bbox(model.section_outlines[1])
    assert left[0] == pytest.approx(px0)
    assert right[2] == pytest.approx(px1)
    # The rounded corners are polygonised, so a Section's extreme Y is a
    # fraction of the corner radius inside the plate's own extreme.
    for lo, hi in ((left[1], left[3]), (right[1], right[3])):
        assert py0 - 1e-9 <= lo <= py0 + 0.5
        assert py1 - 0.5 <= hi <= py1 + 1e-9
    # Neither Section is the whole plate: the Seam is between them.
    assert left[2] < right[2]



def test_section_outlines_split_a_plain_rectangle():
    outline = [(0.0, 0.0), (100.0, 0.0), (100.0, 40.0), (0.0, 40.0)]
    left, right = section_outlines(
        outline, RowSeam(((0.0, 20.0, 60.0), (20.0, 40.0, 40.0))), 40.0,
    )
    assert _area(left) + _area(right) == pytest.approx(4000.0)
    assert _area(left) == pytest.approx(2000.0)  # 60 mm then 40 mm, 20 mm each
    assert _area(right) == pytest.approx(2000.0)


def test_generate_refuses_a_seam_that_crosses_a_cutout(monkeypatch):
    """A layout change that reintroduces #9 fails the build (HARD)."""
    monkeypatch.setattr(
        plate_module, "plate_seam",
        lambda model: RowSeam(((-40.0, 40.0, 0.0),)),
    )
    with pytest.raises(ValueError, match="Seam"):
        _model()


def test_the_floor_standoff_machinery_is_retired():
    """ADR-0014's Well mounts replaced the Tray-floor standoffs entirely."""
    import importlib

    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("keyboard.geometry.seam_holes")

    from layouts.resolvers import default_resolver_registry

    assert "keyboard_mounting_holes" not in default_resolver_registry()


