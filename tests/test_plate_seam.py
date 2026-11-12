"""Keyboard plate Seam: follows the key-column gap nearest the center."""

import json
from pathlib import Path

from keyboard import parse_layout
from keyboard.geometry.plate import generate
from keyboard.geometry.seam import plate_seam, seam_conflicts


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
