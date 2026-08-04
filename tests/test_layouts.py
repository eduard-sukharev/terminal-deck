"""Tests for layout placement."""

from layouts import make_layout
from utilities.config_loader import load_config
from main import BuildPipeline


def _components():
    p = BuildPipeline("config/default.yaml")
    cfg = p.load_config()
    return p.load_components()


def test_default_placements():
    comps = _components()
    layout = make_layout("default", comps)
    placements = layout.placements()
    assert len(placements) == 5  # keyboard, sbc, battery, display, driver


def test_compact_placements():
    comps = _components()
    layout = make_layout("compact", comps)
    placements = layout.placements()
    assert len(placements) == 6  # keyboard, sbc, battery, hub, display, driver


def test_default_no_collisions():
    from utilities.validation import ValidationReport, check_collisions
    comps = _components()
    layout = make_layout("default", comps)
    r = ValidationReport()
    check_collisions(layout.placements(), r)
    assert r.passed, r.checks[0].message


def test_compact_no_collisions():
    from utilities.validation import ValidationReport, check_collisions
    comps = _components()
    layout = make_layout("compact", comps)
    r = ValidationReport()
    check_collisions(layout.placements(), r)
    assert r.passed, r.checks[0].message
