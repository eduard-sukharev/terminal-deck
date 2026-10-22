"""P6-style hinge: two Lid knuckles, one Base knuckle with the cable tunnel."""

import math

import pytest

from components.hinge import Hinge
from utilities import cad_helpers
from utilities.config_loader import load_config

WIDTH = 236.0


def hinge():
    cfg = load_config("config/default.yaml")
    from dataclasses import asdict
    return Hinge(asdict(cfg.hinge), wall_thickness=cfg.wall_thickness)


def test_knuckles_tile_the_span_with_gaps():
    h = hinge()
    (l0, l1), (r0, r1) = h.lid_knuckle_spans(WIDTH)
    b0, b1 = h.base_knuckle_span(WIDTH)
    assert math.isclose(l0, -h.span(WIDTH) / 2) and math.isclose(r1, h.span(WIDTH) / 2)
    assert math.isclose(b0 - l1, h.knuckle_gap) and math.isclose(r0 - b1, h.knuckle_gap)
    assert b1 - b0 > l1 - l0  # the Base knuckle is the long one


def test_tunnel_sits_between_two_pin_lands():
    h = hinge()
    b0, b1 = h.base_knuckle_span(WIDTH)
    t0, t1 = h.tunnel_span(WIDTH)
    assert math.isclose(t0 - b0, h.pin_land) and math.isclose(b1 - t1, h.pin_land)


def test_thin_tunnel_wall_is_rejected():
    with pytest.raises(ValueError):
        Hinge({"diameter": 9.0, "wire_tunnel": 8.0}, wall_thickness=2.5)


def test_caps_close_the_pin_ends_and_pins_clear_each_other():
    h = hinge()
    if not cad_helpers.cad_available():
        pytest.skip("build123d not installed")
    whole = h.build(WIDTH)
    x, y, z = cad_helpers.bounding_box_mm(whole)
    assert math.isclose(x, h.span(WIDTH) + 2 * h.cap_thickness, rel_tol=1e-6)
    assert math.isclose(y, h.diameter, rel_tol=1e-6)
    # The Base knuckle is hollow for the tunnel; solid knuckle would be heavier.
    base = h.build_base_knuckle(WIDTH)
    assert cad_helpers.solid_count(base) == 1
    pins = cad_helpers.volume_mm3(h.build_pins(WIDTH))
    assert math.isclose(pins, 2 * math.pi * (h.pin / 2) ** 2 * h.pin_length(), rel_tol=1e-6)


def test_hinge_fits_check():
    from utilities.validation import ValidationReport, check_hinge_fits

    ok, bad = ValidationReport(), ValidationReport()
    check_hinge_fits(13.0, 20.0, 30.0, ok)
    check_hinge_fits(13.0, 5.0, 30.0, bad)
    assert ok.passed
    assert [c.name for c in bad.failures] == ["hinge-fits"]


def test_notches_cover_the_other_shells_knuckles_with_clearance():
    h = hinge()
    b0, b1 = h.base_knuckle_span(WIDTH)
    (cl0, cl1), (cr0, cr1) = h.corner_notch_spans(WIDTH)
    (l0, l1), (r0, r1) = h.lid_knuckle_spans(WIDTH)
    # Base notches hold the Lid knuckles and reach past the case side (cap access).
    assert cl0 < -WIDTH / 2 and cr1 > WIDTH / 2
    assert cl0 <= l0 and cl1 >= l1 and cr0 <= r0 and cr1 >= r1
    # The Lid notch holds the Base knuckle, with clearance, and touches no Lid knuckle.
    m0, m1 = h.middle_notch_span(WIDTH)
    assert m0 < b0 and m1 > b1 and m0 >= l1 and m1 <= r0
    assert h.notch_radius > h.diameter / 2


def test_hardware_is_pins_and_caps_only():
    h = hinge()
    if not cad_helpers.cad_available():
        pytest.skip("build123d not installed")
    hardware = cad_helpers.volume_mm3(h.build_hardware(WIDTH))
    assert hardware < cad_helpers.volume_mm3(h.build(WIDTH))
    assert hardware > cad_helpers.volume_mm3(h.build_pins(WIDTH))


def test_lid_roll_spans_the_full_width_on_the_hinge_axis():
    if not cad_helpers.cad_available():
        pytest.skip("build123d not installed")
    h = hinge()
    x, y, z = cad_helpers.bounding_box_mm(h.build_lid_roll(WIDTH))
    assert math.isclose(x, WIDTH, rel_tol=1e-6)
    assert math.isclose(y, h.diameter, rel_tol=1e-6) and math.isclose(z, h.diameter, rel_tol=1e-6)


def test_hinge_clears_check():
    from types import SimpleNamespace

    from utilities.validation import ValidationReport, check_hinge_clearance

    def placed(x0, x1, y0, y1, z0, z1):
        return SimpleNamespace(
            component=object(), box=(x0, y0, x1, y1), z_bounds=lambda: (z0, z1)
        )

    box = (-10.0, 10.0, -40.0, -37.5, 5.0, 18.0)
    ok, bad = ValidationReport(), ValidationReport()
    check_hinge_clearance(box, [placed(-5, 5, -30, 0, 0, 20)], ok)
    check_hinge_clearance(box, [placed(-5, 5, -42, -30, 0, 20)], bad)
    assert ok.passed
    assert [c.name for c in bad.failures] == ["hinge-clears"]
