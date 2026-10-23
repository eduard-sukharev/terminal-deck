"""Seam-adjacent plate mounting holes (ADR 0003)."""

import json
import math
from pathlib import Path


from keyboard import parse_layout
from keyboard.geometry.plate import generate
from keyboard.geometry.seam import _x_span, _y_span, plate_seam
from keyboard.geometry.seam_holes import CUTOUT_MARGIN, seam_holes

UNIT = 19.05
SCREW_D = 2.2


def _model():
    raw = json.loads(Path("keyboard/layouts/jd40.json").read_text())
    return generate(
        parse_layout(raw, pitch=UNIT),
        switch_family="mx_alps", stabilizer_family="cherry",
        plate_thickness=1.5, edge_margin=2.0, corner_radius=8.0,
        screw_diameter=SCREW_D, screw_edge_offset=5.0,
    )


def _holes(model=None, blocked=None):
    model = model or _model()
    xs = [p[0] for p in model.plate_outline]
    ys = [p[1] for p in model.plate_outline]
    return seam_holes(
        model.switch_cutouts, model.stabilizer_cutouts, plate_seam(model),
        (min(xs), min(ys), max(xs), max(ys)), UNIT, SCREW_D, blocked,
    )


def test_each_section_gets_one_lower_and_one_upper_hole():
    found = {(h.section, h.rows) for h in _holes()}
    assert found == {("left", "lower"), ("left", "upper"), ("right", "lower"), ("right", "upper")}


def test_holes_are_within_one_unit_of_the_seam_and_on_their_own_side():
    model = _model()
    seam = plate_seam(model)
    for h in _holes(model):
        xs = [x for y0, y1, x in seam.bands if y0 - 1e-6 <= h.y <= y1 + 1e-6]
        if h.section == "left":
            assert h.x < min(xs) and min(xs) - h.x <= UNIT + 1e-6
        else:
            assert h.x > max(xs) and h.x - max(xs) <= UNIT + 1e-6


def test_holes_sit_in_row_gaps_clear_of_every_cutout():
    model = _model()
    cuts = list(model.switch_cutouts) + list(model.stabilizer_cutouts)
    for h in _holes(model):
        for c in cuts:
            x0, x1 = _x_span(c)
            y0, y1 = _y_span(c)
            d = math.hypot(h.x - min(max(h.x, x0), x1), h.y - min(max(h.y, y0), y1))
            assert d >= SCREW_D / 2 + CUTOUT_MARGIN - 1e-9


def test_lower_holes_are_in_the_lower_half_and_upper_in_the_upper():
    for h in _holes():
        assert (h.y < 0) == (h.rows == "lower")


def test_a_blocked_spot_is_skipped_for_the_next_free_one():
    base = {(h.section, h.rows): h for h in _holes()}
    target = base[("right", "lower")]
    moved = {(h.section, h.rows): h for h in _holes(blocked=lambda x, y, d: abs(x - target.x) < 3 and abs(y - target.y) < 3)}
    assert moved[("right", "lower")].x > target.x


def test_a_half_with_no_free_spot_gets_no_hole():
    found = {(h.section, h.rows) for h in _holes(blocked=lambda x, y, d: x > 0 and y < 5)}
    assert ("right", "lower") not in found
    assert ("left", "upper") in found


def test_the_default_plate_carries_eight_mounting_holes():
    assert len(_model().mounting_holes) == 8
