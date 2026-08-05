"""Tests for the keycap registry, geometry, and sizing."""

import math

import pytest

from keyboard import get_keycap, registered_keycaps
from keyboard.geometry.keycaps import (
    keycap_specs,
    rectangle_vertices,
    stadium_vertices,
)
from keyboard.layout.key import Key


def test_registered_keycaps():
    caps = registered_keycaps()
    assert "xda" in caps


def test_get_keycap():
    cls = get_keycap("xda")
    profile = cls()
    assert profile.base_size() == 18.5
    assert profile.top_diameter() == 15.0
    assert profile.height() == 9.0
    assert profile.segments() == 32


def test_get_keycap_unknown():
    with pytest.raises(ValueError, match="Unknown keycap profile"):
        get_keycap("nonexistent")


def test_keycap_specs_1u():
    keys = [Key(x=0.0, y=0.0, width=1.0, height=1.0)]
    profile = get_keycap("xda")()
    specs = keycap_specs(keys, profile)
    assert len(specs) == 1
    s = specs[0]
    assert s["base_w"] == 18.5
    assert s["base_d"] == 18.5
    assert s["top_w"] == 15.0
    assert s["top_d"] == 15.0
    assert s["corner_radius"] == 7.5
    assert s["height"] == 9.0
    assert s["segments"] == 32
    assert s["rotation"] == 0.0


def test_keycap_specs_175u():
    """1.75u Shift key — width scales, depth stays constant."""
    keys = [Key(x=0.0, y=0.0, width=1.75, height=1.0)]
    profile = get_keycap("xda")()
    specs = keycap_specs(keys, profile)
    s = specs[0]
    assert s["base_w"] == pytest.approx(32.375)
    assert s["base_d"] == 18.5
    assert s["top_w"] == pytest.approx(26.25)
    assert s["top_d"] == 15.0
    assert s["corner_radius"] == 7.5


def test_keycap_specs_spacebar():
    """6.25u spacebar — long stadium top."""
    keys = [Key(x=0.0, y=0.0, width=6.25, height=1.0)]
    profile = get_keycap("xda")()
    specs = keycap_specs(keys, profile)
    s = specs[0]
    assert s["base_w"] == pytest.approx(115.625)
    assert s["base_d"] == 18.5
    assert s["top_w"] == pytest.approx(93.75)
    assert s["top_d"] == 15.0
    assert s["corner_radius"] == 7.5


def test_keycap_specs_centroid_offset():
    """Keys at non-zero positions get correct mm coordinates."""
    keys = [Key(x=1.0, y=2.0, width=1.0, height=1.0)]
    profile = get_keycap("xda")()
    specs = keycap_specs(keys, profile, pitch=19.05, layout_centroid=(0.0, 0.0))
    s = specs[0]
    assert s["x"] == 19.05
    assert s["y"] == 38.1


def test_rectangle_vertices_count():
    verts = rectangle_vertices(18.5, 18.5, n=32)
    assert len(verts) == 32


def test_rectangle_vertices_symmetry():
    """Rectangle vertices should be symmetric about both axes."""
    verts = rectangle_vertices(18.5, 18.5, n=32)
    for x, y in verts:
        assert abs(x) <= 9.25 + 1e-9
        assert abs(y) <= 9.25 + 1e-9


def test_stadium_vertices_circle():
    """When w=d=2r, stadium_vertices should produce a circle of radius r."""
    verts = stadium_vertices(15.0, 15.0, 7.5, n=32)
    assert len(verts) == 32
    for x, y in verts:
        r = math.sqrt(x * x + y * y)
        assert abs(r - 7.5) < 1e-9


def test_stadium_vertices_wide():
    """Wide stadium: long axis along X, short axis along Y."""
    verts = stadium_vertices(26.25, 15.0, 7.5, n=32)
    assert len(verts) == 32
    for x, y in verts:
        assert abs(y) <= 7.5 + 1e-9
        # Points near the ends should have |x| near 13.125
        if abs(y) < 1.0:
            assert abs(x) <= 13.125 + 1e-9


def test_stadium_vertices_matched_angles():
    """Stadium and rectangle vertices should pair 1:1 by angle for lofting."""
    n = 32
    rect = rectangle_vertices(18.5, 18.5, n)
    stadium = stadium_vertices(15.0, 15.0, 7.5, n)
    assert len(rect) == len(stadium)
    # Both should start at the same angle (+X axis).
    assert rect[0][1] == 0.0
    assert stadium[0][1] == 0.0
    assert rect[0][0] > 0
    assert stadium[0][0] > 0
