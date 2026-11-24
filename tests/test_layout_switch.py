"""Keyboard-layout adaptability: the CLI override, derived pin sites and the
plate-pin clearance check.

The plate must follow any KLE layout without hand-tuned config: its Seam is
derived (keyboard.geometry.seam.plate_seam), its filament-pin sites follow the
Seam's row-gap boundaries (pin_sites), and each fin is sized/centred on the jog
it bridges (geometry.seam_joint.pin_footprint). These are pure-data checks.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from geometry.seam_joint import pin_footprint, step_at
from keyboard import parse_layout
from keyboard.geometry.plate import generate
from keyboard.geometry.seam import pin_sites, plate_seam
from utilities.build_cache import BuildCache
from utilities.config_loader import SeamPin


LAYOUTS = ("jd40", "planck", "saber")


def _model(name: str):
    raw = json.loads(Path(f"keyboard/layouts/{name}.json").read_text())
    return generate(
        parse_layout(raw, pitch=19.05),
        switch_family="mx_alps",
        stabilizer_family="cherry",
        plate_thickness=1.5,
        wall=2.0,
        keycap_profile="xda",
        wobble=0.6,
        corner_radius=2.0,
    )


def _cut_boxes(model):
    boxes = []
    for cut in list(model.switch_cutouts) + list(model.stabilizer_cutouts):
        xs = [cut.x + vx for vx, _ in cut.vertices]
        ys = [cut.y + vy for _, vy in cut.vertices]
        boxes.append((min(xs), max(xs), min(ys), max(ys)))
    return boxes


def _overlap(a, b) -> bool:
    return not (a[1] <= b[0] or b[1] <= a[0] or a[3] <= b[2] or b[3] <= a[2])


# -- pin sites derive from the Seam, per layout -------------------------


@pytest.mark.parametrize("name", LAYOUTS)
def test_pin_sites_are_the_seams_row_gap_boundaries(name):
    model = _model(name)
    seam = plate_seam(model)
    sites = pin_sites(seam)
    # One site per gap between consecutive rows.
    assert len(sites) == len(seam.bands) - 1
    assert sites == tuple(b[1] for b in seam.bands[:-1])
    # Ordered front to back, inside the plate.
    assert list(sites) == sorted(sites)
    half = model.metadata.height / 2.0
    assert all(-half < y < half for y in sites)


@pytest.mark.parametrize("name", LAYOUTS)
def test_every_plate_pin_clears_every_cutout(name):
    model = _model(name)
    seam = plate_seam(model)
    pin = SeamPin()
    depth = model.metadata.height
    boxes = _cut_boxes(model)
    half_w, half_d = model.metadata.width / 2.0, model.metadata.height / 2.0
    for y in pin_sites(seam):
        x0, x1, y0, y1 = pin_footprint(seam, depth, y, pin, follow_step=True)
        assert -half_w <= x0 and x1 <= half_w, (name, y, "x off plate")
        assert -half_d <= y0 and y1 <= half_d, (name, y, "y off plate")
        for box in boxes:
            assert not _overlap((x0, x1, y0, y1), box), (name, y, box)


# -- the fin is sized and centred on the jog it bridges -----------------


def test_a_straight_run_boundary_has_no_step():
    # Two bands at the same X: the boundary is not a jog.
    from keyboard.geometry.seam import RowSeam

    seam = RowSeam(((-30.0, -10.0, 0.0), (-10.0, 10.0, 0.0)))
    assert step_at(seam, 60.0, -10.0) is None


def test_a_jog_fin_spans_its_step_plus_engagement_each_side():
    from keyboard.geometry.seam import RowSeam

    seam = RowSeam(((-30.0, -10.0, 0.0), (-10.0, 10.0, 8.0)))
    pin = SeamPin()
    centre, travel = step_at(seam, 60.0, -10.0)
    assert centre == pytest.approx(4.0)
    assert travel == pytest.approx(8.0)
    x0, x1, _, _ = pin_footprint(seam, 60.0, -10.0, pin, follow_step=True)
    assert (x0 + x1) / 2.0 == pytest.approx(centre)  # centred on the jog
    assert (x1 - x0) == pytest.approx(travel + 2.0 * pin.engagement)


# -- the cache keys on the effective layout -----------------------------


def test_cache_salt_separates_layouts(tmp_path):
    root = Path(".")
    jd40 = BuildCache(
        tmp_path / "c.json", root=root, extra_salt="keyboard/layouts/jd40.json"
    ).fingerprint("keyboard_plate")
    planck = BuildCache(
        tmp_path / "c.json", root=root, extra_salt="keyboard/layouts/planck.json"
    ).fingerprint("keyboard_plate")
    assert jd40 != planck


# -- the --keyboard-layout override -------------------------------------


def test_keyboard_layout_override_replaces_layout_source():
    from main import BuildPipeline

    pipeline = BuildPipeline(
        config_path="config/default.yaml",
        keyboard_layout="keyboard/layouts/planck.json",
    )
    cfg = pipeline.load_config()
    assert cfg.keyboard.layout_source == "keyboard/layouts/planck.json"


def test_missing_keyboard_layout_file_raises():
    from main import BuildPipeline

    pipeline = BuildPipeline(
        config_path="config/default.yaml",
        keyboard_layout="keyboard/layouts/does-not-exist.json",
    )
    with pytest.raises(FileNotFoundError):
        pipeline.load_config()
