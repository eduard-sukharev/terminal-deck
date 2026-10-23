"""Printed friction hinge (ADR 0004): cheeks, Lid knuckles, Base knuckle part."""

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


def test_layout_runs_cheek_washers_lid_knuckle_washers_base_knuckle():
    h = hinge()
    (c0, c1), (d0, d1) = h.cheek_spans(WIDTH)
    (l0, l1), (r0, r1) = h.lid_knuckle_spans(WIDTH)
    b0, b1 = h.base_knuckle_span(WIDTH)
    assert math.isclose(c0, -h.span(WIDTH) / 2) and math.isclose(d1, h.span(WIDTH) / 2)
    assert math.isclose(l0 - c1, h.washer_stack) and math.isclose(d0 - r1, h.washer_stack)
    assert math.isclose(b0 - l1, h.washer_stack) and math.isclose(r0 - b1, h.washer_stack)
    assert b1 - b0 > l1 - l0  # the Base knuckle is the long one


def test_tunnel_sits_between_two_bolt_lands():
    h = hinge()
    b0, b1 = h.base_knuckle_span(WIDTH)
    t0, t1 = h.tunnel_span(WIDTH)
    assert math.isclose(t0 - b0, h.land) and math.isclose(b1 - t1, h.land)


def test_thin_tunnel_wall_is_rejected():
    with pytest.raises(ValueError):
        Hinge({"diameter": 9.0, "wire_tunnel": 8.0}, wall_thickness=2.5)


def test_friction_bolt_stock_length_covers_the_clamped_stack():
    h = hinge()
    run = h.end_cheek - h.head_recess_depth() + 2 * h.washer_stack + h.lid_knuckle + h.land
    assert h.bolt_length() <= run
    assert run - h.bolt_length() < 5  # the next stock size up would not fit


def test_base_knuckle_part_fits_the_build_volume():
    if not cad_helpers.cad_available():
        pytest.skip("build123d not installed")
    h = hinge()
    x, y, z = cad_helpers.bounding_box_mm(h.build_base_part(WIDTH, drop=29.0))
    assert x <= 220.0 and cad_helpers.solid_count(h.build_base_part(WIDTH, drop=29.0)) == 1


def test_base_part_is_one_solid_with_cheeks_joined_through_the_flange():
    if not cad_helpers.cad_available():
        pytest.skip("build123d not installed")
    h = hinge()
    part = h.build_base_part(WIDTH, drop=29.0, screws=((20.0, 4.7),))
    assert cad_helpers.solid_count(part) == 1
    x, y, z = cad_helpers.bounding_box_mm(part)
    assert math.isclose(x, h.span(WIDTH), rel_tol=1e-6)


def test_lid_knuckles_are_bored_for_the_bolt():
    if not cad_helpers.cad_available():
        pytest.skip("build123d not installed")
    h = hinge()
    knuckles = cad_helpers.volume_mm3(h.build_lid_knuckles(WIDTH))
    solid = 2 * math.pi * h.radius ** 2 * h.lid_knuckle
    assert knuckles < solid


def test_hinge_fits_check():
    from utilities.validation import ValidationReport, check_hinge_fits

    ok, bad = ValidationReport(), ValidationReport()
    check_hinge_fits(13.0, 20.0, 30.0, ok)
    check_hinge_fits(13.0, 5.0, 30.0, bad)
    assert ok.passed
    assert [c.name for c in bad.failures] == ["hinge-fits"]


def test_notches_cover_the_other_shells_pieces_with_clearance():
    h = hinge()
    b0, b1 = h.base_knuckle_span(WIDTH)
    (cl0, cl1), (cr0, cr1) = h.corner_notch_spans(WIDTH)
    (l0, l1), (r0, r1) = h.lid_knuckle_spans(WIDTH)
    # Deck notches hold the Lid knuckles and reach past the case side.
    assert cl0 < -WIDTH / 2 and cr1 > WIDTH / 2
    assert cl0 <= l0 and cl1 >= l1 and cr0 <= r0 and cr1 >= r1
    # Lid notches hold the Base bar and both cheeks, with clearance, and touch no Lid knuckle.
    notches = h.lid_notch_spans(WIDTH)
    for lo, hi in [h.cheek_spans(WIDTH)[0], (b0, b1), h.cheek_spans(WIDTH)[1]]:
        assert any(n0 <= lo and hi <= n1 for n0, n1 in notches)
    for lo, hi in [(l0, l1), (r0, r1)]:
        assert not any(n0 < hi and lo < n1 for n0, n1 in notches)
    assert h.notch_radius > h.diameter / 2


def test_hardware_is_bolts_nuts_washers_and_caps_only():
    h = hinge()
    if not cad_helpers.cad_available():
        pytest.skip("build123d not installed")
    hardware = cad_helpers.volume_mm3(h.build_hardware(WIDTH))
    assert 0 < hardware < cad_helpers.volume_mm3(h.build(WIDTH))


def test_lid_roll_spans_the_full_width_on_the_hinge_axis():
    if not cad_helpers.cad_available():
        pytest.skip("build123d not installed")
    h = hinge()
    x, y, z = cad_helpers.bounding_box_mm(h.build_lid_roll(WIDTH))
    assert math.isclose(x, WIDTH, rel_tol=1e-6)
    assert math.isclose(y, h.diameter, rel_tol=1e-6) and math.isclose(z, h.diameter, rel_tol=1e-6)


def test_hinge_clears_check_covers_cheeks_and_flange():
    from types import SimpleNamespace

    from utilities.validation import ValidationReport, check_hinge_clearance

    def placed(x0, x1, y0, y1, z0, z1):
        return SimpleNamespace(
            component=object(), box=(x0, y0, x1, y1), z_bounds=lambda: (z0, z1)
        )

    box = (-10.0, 10.0, -40.0, -37.5, 5.0, 18.0)
    cheek = {"left end cheek": (-60.0, -55.0, -40.0, -37.5, 5.0, 18.0)}
    ok, bad, bad_cheek = ValidationReport(), ValidationReport(), ValidationReport()
    check_hinge_clearance(box, [placed(-5, 5, -30, 0, 0, 20)], ok, cheek)
    check_hinge_clearance(box, [placed(-5, 5, -42, -30, 0, 20)], bad, cheek)
    check_hinge_clearance(box, [placed(-58, -56, -42, -30, 0, 20)], bad_cheek, cheek)
    assert ok.passed
    assert [c.name for c in bad.failures] == ["hinge-clears"]
    assert "cheek" in bad_cheek.failures[0].message


def test_sweep_check_needs_the_cheeks_and_bar_in_lid_notches():
    from utilities.validation import ValidationReport, check_hinge_sweep

    ok, bad, low = ValidationReport(), ValidationReport(), ValidationReport()
    cheeks, bar = ((-100.0, -95.0), (95.0, 100.0)), (-60.0, 60.0)
    notches = ((-110.0, -94.0), (-61.0, 61.0), (94.0, 110.0))
    check_hinge_sweep(cheeks, bar, notches, -7.0, 6.5, ok)
    check_hinge_sweep(cheeks, bar, notches[1:], -7.0, 6.5, bad)
    check_hinge_sweep(cheeks, bar, notches, -6.0, 6.5, low)
    assert ok.passed and not bad.passed and not low.passed
