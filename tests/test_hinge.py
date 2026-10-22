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
