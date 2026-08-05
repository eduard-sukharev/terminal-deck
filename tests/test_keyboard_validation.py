"""Tests for keyboard plate validation."""

import json
from pathlib import Path

from keyboard import parse_layout
from keyboard.geometry.plate import generate
from keyboard.validation import validate
from keyboard.registry import registered_switches, registered_stabilizers


def _jd40_layout():
    path = Path("keyboard/layouts/jd40.json")
    raw = json.loads(path.read_text())
    return parse_layout(raw, pitch=19.05)


def _jd40_model():
    layout = _jd40_layout()
    return generate(
        layout,
        switch_family="mx_alps",
        stabilizer_family="cherry",
        plate_thickness=1.5,
        edge_margin=8.0,
        corner_radius=8.0,
        screw_diameter=2.2,
        screw_edge_offset=5.0,
    )


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
    assert checks == 8
    assert errors == [], f"Validation errors: {errors}"


def test_invalid_switch_family():
    layout = _jd40_layout()
    model = _jd40_model()
    checks, errors = validate(layout, model, "nonexistent", "cherry")
    assert checks == 8
    assert any("switch" in e.lower() for e in errors)


def test_invalid_stabilizer_family():
    layout = _jd40_layout()
    model = _jd40_model()
    checks, errors = validate(layout, model, "mx_alps", "nonexistent")
    assert checks == 8
    assert any("stabilizer" in e.lower() for e in errors)
