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


# -- ears and notches in the plate outline (ADR-0014, issue #14) ----------

#: The eight Well-mount stations' ears, as the enclosure injects them
#: (plate-local mm, rect + fillet). Numbers are #11/#18's arithmetic on the M2
#: fastener library and the plate border; here they are input data only.
EARS = [
    ((-109.4335, -45.0250, -104.2335, -39.8250), 2.0),
    ((-9.8000, -45.0250, -4.6000, -39.8250), 2.0),
    ((-60.3844, 39.8250, -55.1844, 45.0250), 2.0),
    ((-109.4335, 39.8250, -104.2335, 45.0250), 2.0),
    ((104.2335, -45.0250, 109.4335, -39.8250), 2.0),
    ((4.6000, -45.0250, 9.8000, -39.8250), 2.0),
    ((-45.9844, 39.8250, -40.7844, 45.0250), 2.0),
    ((104.2335, 39.8250, 109.4335, 45.0250), 2.0),
]

#: The four chassis-band notches, as the enclosure injects them.
NOTCHES = [
    (-116.7329, -40.7750, -111.4340, -39.3250),
    (111.4340, -40.7750, 116.7329, -39.3250),
    (-42.8439, -40.7750, -37.5450, -39.3250),
    (37.5450, -40.7750, 42.8439, -39.3250),
]


def _to_tabs(ears):
    from keyboard.geometry.outline import PlateTab

    return [PlateTab(rect=rect, fillet=fillet) for rect, fillet in ears]


def _in_rect(x, y, rect):
    return rect[0] < x < rect[2] and rect[1] < y < rect[3]


def _in_tab(x, y, rect, fillet):
    """Inside a filleted ear: its rect minus the two outboard corner bites."""
    if not _in_rect(x, y, rect):
        return False
    x0, y0, x1, y1 = rect
    if fillet <= 0.0:
        return True
    outboard_low = abs(y0) > abs(y1)  # front ears reach to -Y, rear ones +Y
    cy = y0 + fillet if outboard_low else y1 - fillet
    corners = [
        (x0 + fillet, cy, x <= x0 + fillet, y <= cy if outboard_low else y >= cy),
        (x1 - fillet, cy, x >= x1 - fillet, y <= cy if outboard_low else y >= cy),
    ]
    for cx, _, in_x, in_y in corners:
        if in_x and in_y and (x - cx) ** 2 + (y - cy) ** 2 > fillet * fillet:
            return False
    return True


def test_ears_and_notches_are_merged_into_the_plate_outline():
    """The outline is base ∪ ears ∖ notches -- checked by independent sampling."""
    from keyboard.validation import _point_in_polygon

    model = _jd40_model(
        ears=_to_tabs(EARS), notches=NOTCHES, corner_radius=2.0,
    )
    half_w = model.metadata.width / 2.0
    half_d = model.metadata.height / 2.0
    r = 2.0

    def expected(x, y):
        # Rounded-rect base (the corner check uses the arc, not the bbox).
        base = abs(x) <= half_w and abs(y) <= half_d
        if base:
            for sx in (-1.0, 1.0):
                for sy in (-1.0, 1.0):
                    if sx * x > half_w - r and sy * y > half_d - r:
                        cx, cy = sx * (half_w - r), sy * (half_d - r)
                        base = (x - cx) ** 2 + (y - cy) ** 2 <= r * r
        if not base and not any(
            _in_tab(x, y, rect, fillet) for rect, fillet in EARS
        ):
            return False
        return not any(_in_rect(x, y, rect) for rect in NOTCHES)

    step = 0.5
    xs = [(-half_w - 6.0) + step * i for i in range(int((2 * half_w + 12.0) / step) + 1)]
    ys = [(-half_d - 6.0) + step * i for i in range(int((2 * half_d + 12.0) / step) + 1)]
    for x in xs:
        for y in ys:
            # Skip samples near the plate's own edges/arcs and near any
            # feature boundary (the polygonisation tolerance).
            near = (
                abs(abs(x) - half_w) < 0.06
                or abs(abs(y) - half_d) < 0.06
                or any(
                    abs((x - sx * (half_w - r)) ** 2 + (y - sy * (half_d - r)) ** 2 - r * r)
                    < 0.35
                    for sx in (-1.0, 1.0)
                    for sy in (-1.0, 1.0)
                )
            )
            near = near or any(
                abs(v - e) < 0.06
                for rect in NOTCHES
                for v in (x, y)
                for e in rect
            ) or any(
                abs(v - e) < 0.06
                for rect, _ in EARS
                for v in (x, y)
                for e in rect
            ) or any(
                abs((x - cx) ** 2 + (y - cy) ** 2 - fillet * fillet) < 0.35
                for rect, fillet in EARS
                for cx in (rect[0] + fillet, rect[2] - fillet)
                for cy in ((rect[1] + fillet,) if abs(rect[1]) > abs(rect[3]) else (rect[3] - fillet,))
            )
            if near:
                continue
            assert _point_in_polygon(x, y, model.plate_outline) == expected(x, y), (
                f"outline disagrees at ({x:.2f}, {y:.2f})"
            )


def test_every_notch_is_a_gap_in_the_plate_and_every_ear_is_material():
    from keyboard.validation import _point_in_polygon

    model = _jd40_model(
        ears=_to_tabs(EARS), notches=NOTCHES, corner_radius=2.0,
    )
    outline = model.plate_outline
    half_d = model.metadata.height / 2.0
    for rect in NOTCHES:
        cx = (rect[0] + rect[2]) / 2.0
        # Inside the bite (between the plate edge and the notch floor).
        assert not _point_in_polygon(cx, -half_d + (rect[3] - (-half_d)) / 2.0, outline)
        # Just inboard of the notch floor there is still material.
        assert _point_in_polygon(cx, rect[3] + 0.2, outline)
    for rect, _ in EARS:
        cx = (rect[0] + rect[2]) / 2.0
        outboard = -half_d - 2.0 if rect[1] < 0 else half_d + 2.0
        assert _point_in_polygon(cx, outboard, outline)


def test_section_outlines_keep_every_tab_whole_and_partition_the_plate():
    from keyboard.validation import _point_in_polygon

    model = _jd40_model(
        ears=_to_tabs(EARS), notches=NOTCHES, corner_radius=2.0,
    )
    left, right = model.section_outlines
    plate_area = abs(sum(
        a[0] * b[1] - b[0] * a[1]
        for a, b in zip(model.plate_outline, model.plate_outline[1:] + model.plate_outline[:1])
    )) / 2.0
    section_area = sum(
        abs(sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(poly, poly[1:] + poly[:1]))) / 2.0
        for poly in (left, right)
    )
    assert section_area == pytest.approx(plate_area)
    # Every ear belongs wholly to one Section: probes inside the tab agree.
    for rect, _ in EARS:
        cx = (rect[0] + rect[2]) / 2.0
        cy = (rect[1] + rect[3]) / 2.0
        probes = [(cx, cy), (cx - 1.0, cy), (cx + 1.0, cy), (cx, cy - 1.0), (cx, cy + 1.0)]
        in_left = [_point_in_polygon(x, y, left) for x, y in probes]
        in_right = [_point_in_polygon(x, y, right) for x, y in probes]
        assert all(in_left) != all(in_right), f"ear {rect} straddles the Seam"
        assert len(set(in_left)) == 1 and len(set(in_right)) == 1
