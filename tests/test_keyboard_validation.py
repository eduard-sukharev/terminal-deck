"""Tests for keyboard plate validation and the ADR-0014 plate sizing chain.

The plate is *derived*: the Well Cutout is the real keycap footprint plus the
wobble allowance, and the plate is the Cutout plus one wall thickness on each
side so it bears on the Well walls' lower faces (ADR-0014). The plate carries
no floor-standoff holes; mounting holes are injected by the enclosure.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from keyboard import parse_layout
from keyboard.geometry.outline import generate_outline
from keyboard.geometry.plate import generate
from keyboard.metadata import MountingHole
from keyboard.registry import registered_switches, registered_stabilizers
from keyboard.validation import validate

#: The Well ring / plate border (config ``wall.thickness``, mm).
WALL = 2.0
#: The keycap wobble allowance each side of the Cutout (config, mm).
WOBBLE = 0.6


def _jd40_layout():
    path = Path("keyboard/layouts/jd40.json")
    raw = json.loads(path.read_text())
    return parse_layout(raw, pitch=19.05)


def _jd40_model(**kwargs):
    args = dict(
        switch_family="mx_alps",
        stabilizer_family="cherry",
        plate_thickness=1.5,
        wall=WALL,
        keycap_profile="xda",
        wobble=WOBBLE,
        corner_radius=2.0,
    )
    args.update(kwargs)
    return generate(_jd40_layout(), **args)


def _bbox(points):
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    return (min(xs), min(ys), max(xs), max(ys))


def test_registered_switches():
    switches = registered_switches()
    assert "mx_alps" in switches
    assert "square" in switches


def test_registered_stabilizers():
    stabs = registered_stabilizers()
    assert "cherry" in stabs


def test_jd40_validation_passes():
    layout = _jd40_layout()
    model = _jd40_model()
    checks, errors = validate(layout, model, "mx_alps", "cherry")
    assert checks == 9
    assert errors == [], f"Validation errors: {errors}"


def test_invalid_switch_family():
    layout = _jd40_layout()
    model = _jd40_model()
    checks, errors = validate(layout, model, "nonexistent", "cherry")
    assert checks == 9
    assert any("switch" in e.lower() for e in errors)


def test_invalid_stabilizer_family():
    layout = _jd40_layout()
    model = _jd40_model()
    checks, errors = validate(layout, model, "mx_alps", "nonexistent")
    assert checks == 9
    assert any("stabilizer" in e.lower() for e in errors)


# -- the sizing chain (ADR-0014) ------------------------------------------


def test_cutout_is_the_keycap_footprint_plus_the_wobble():
    """Cutout = real keycap footprint + wobble per side, never a chosen number."""
    model = _jd40_model(wobble=0.0)
    bare = model.metadata.cutout
    model = _jd40_model()
    cutout = model.metadata.cutout
    assert cutout[0] == pytest.approx(bare[0] - WOBBLE)
    assert cutout[1] == pytest.approx(bare[1] - WOBBLE)
    assert cutout[2] == pytest.approx(bare[2] + WOBBLE)
    assert cutout[3] == pytest.approx(bare[3] + WOBBLE)


def test_plate_is_the_cutout_plus_one_wall_on_every_side():
    model = _jd40_model()
    cx0, cy0, cx1, cy1 = model.metadata.cutout
    px0, py0, px1, py1 = _bbox(model.plate_outline)
    assert px0 == pytest.approx(cx0 - WALL)
    assert py0 == pytest.approx(cy0 - WALL)
    assert px1 == pytest.approx(cx1 + WALL)
    assert py1 == pytest.approx(cy1 + WALL)
    assert model.metadata.width == pytest.approx((cx1 - cx0) + 2 * WALL)
    assert model.metadata.height == pytest.approx((cy1 - cy0) + 2 * WALL)


def test_plate_border_is_free_of_switch_and_stabilizer_cutouts():
    """The border the plate bears on is the Well ring: no cutout may enter it."""
    model = _jd40_model()
    cx0, cy0, cx1, cy1 = model.metadata.cutout
    for cut in list(model.switch_cutouts) + list(model.stabilizer_cutouts):
        x0, y0, x1, y1 = _bbox([(cut.x + vx, cut.y + vy) for vx, vy in cut.vertices])
        assert x0 >= cx0 and x1 <= cx1 and y0 >= cy0 and y1 <= cy1, (
            f"cutout at ({cut.x:.2f}, {cut.y:.2f}) enters the plate border"
        )


def test_edge_margins_are_derived_from_the_cutout_not_chosen():
    """Border from the outermost switch/stabilizer cutout, per side."""
    model = _jd40_model()
    left, right, bottom, top = model.metadata.edge_margins
    assert left == pytest.approx(right)  # the switch field is symmetric in X
    # Solid plate under the whole Well ring on every side: the border is
    # wider than the ring itself (the spacebar stabilizer is the tightest).
    assert min(left, right, bottom, top) > WALL
    assert model.metadata.edge_margin == pytest.approx(
        min(left, right, bottom, top)
    )


def test_generate_outline_supports_per_side_margins():
    verts = generate_outline(
        [(0.0, 0.0)], margin=(1.0, 2.0, 3.0, 4.0), corner_radius=0.0,
    )
    assert _bbox(verts) == (-1.0, -3.0, 2.0, 4.0)


def test_asymmetric_plate_keeps_one_wall_beside_an_off_centre_cutout():
    """A keycap footprint off the switch-centre bbox gives asymmetric margins."""
    base_model = _jd40_model()
    cx0, cy0, cx1, cy1 = base_model.metadata.cutout
    base = base_model.metadata.edge_margins
    model = _jd40_model(cutout=(cx0 - 5.0, cy0, cx1, cy1))
    px0, py0, px1, py1 = _bbox(model.plate_outline)
    assert px0 == pytest.approx(cx0 - 5.0 - WALL)
    assert py0 == pytest.approx(cy0 - WALL)
    assert px1 == pytest.approx(cx1 + WALL)
    assert py1 == pytest.approx(cy1 + WALL)
    # Only the side the Cutout grew on gains border; the plate followed it.
    left, right, bottom, top = model.metadata.edge_margins
    assert left == pytest.approx(base[0] + 5.0)
    assert (right, bottom, top) == pytest.approx((base[1], base[2], base[3]))
    checks, errors = validate(_jd40_layout(), model, "mx_alps", "cherry")
    assert errors == [], f"an off-centre Cutout must still validate: {errors}"


# -- no floor-standoff holes (ADR-0014) -----------------------------------


def test_the_plate_carries_no_floor_standoff_holes():
    model = _jd40_model()
    assert model.mounting_holes == []
    assert model.metadata.mounting_points == []


def test_injected_mounting_holes_appear_verbatim():
    holes = [MountingHole(10.0, 5.0, 2.2), MountingHole(-100.0, -30.0, 2.2)]
    model = _jd40_model(mounting_holes=holes)
    assert model.mounting_holes == holes
    assert model.metadata.mounting_points == [(10.0, 5.0), (-100.0, -30.0)]


def test_the_model_needs_the_wall_to_size_the_plate():
    with pytest.raises(TypeError):
        generate(_jd40_layout())  # ``wall`` is keyword-only and required


def test_keyboard_package_imports_without_a_cad_library():
    code = """
import sys

class _NoCad:
    def find_spec(self, name, path=None, target=None):
        if name.split(".")[0] in {"build123d", "cadquery", "OCP"}:
            raise ImportError("CAD library blocked for this test")
        return None

sys.meta_path.insert(0, _NoCad())
import keyboard
from keyboard import parse_layout
from keyboard.geometry.plate import generate
import json

layout = parse_layout(json.load(open("keyboard/layouts/jd40.json")), pitch=19.05)
model = generate(layout, wall=2.0, wobble=0.6, keycap_profile="xda")
assert model.metadata.width > 0
assert model.mounting_holes == []
"""
    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
