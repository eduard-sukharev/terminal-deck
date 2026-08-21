"""Tests for assembly helpers (select_placements)."""

import pytest
from assemblies.assembly import select_placements
from main import BuildPipeline


def _components_and_placements():
    p = BuildPipeline("config/default.yaml")
    p.load_config()
    comps = p.load_components()
    from layouts import make_layout
    layout = make_layout("default", comps)
    return comps, layout.placements()


def test_select_placements_display_group():
    comps, placements = _components_and_placements()
    keep = {comps["display"], comps["driver"]}
    result = select_placements(placements, keep)
    assert len(result) == 2
    assert result[0].component is comps["display"]
    assert result[1].component is comps["driver"]


def test_select_placements_preserves_order():
    comps, placements = _components_and_placements()
    keep = {comps["driver"], comps["display"]}
    result = select_placements(placements, keep)
    assert result[0].component is comps["display"]
    assert result[1].component is comps["driver"]


def test_select_placements_empty_for_unknown():
    _, placements = _components_and_placements()
    from components.base import Component, BoundingBox
    class Fake(Component):
        name = "fake"
        def size(self):
            return BoundingBox(1, 1, 1)
    result = select_placements(placements, {Fake()})
    assert result == []


def test_select_placements_single_component():
    comps, placements = _components_and_placements()
    result = select_placements(placements, {comps["sbc"]})
    assert len(result) == 1
    assert result[0].component is comps["sbc"]


def _keyboard_from_pipeline():
    """Return a properly configured Rp2040Keyboard via the pipeline."""
    p = BuildPipeline("config/default.yaml")
    p.load_config()
    comps = p.load_components()
    return comps["keyboard"]


def test_set_plate_raise_changes_size():
    kb = _keyboard_from_pipeline()
    original_height = kb.size().height
    original_raise = kb._plate_raise

    kb.set_plate_raise(original_raise + 5.0)
    new_height = kb.size().height
    assert new_height == pytest.approx(original_height + 5.0)
    assert kb._plate_raise == pytest.approx(original_raise + 5.0)


def test_set_plate_raise_changes_mounting_holes():
    kb = _keyboard_from_pipeline()
    holes = kb.mounting_holes()
    original_heights = [h.height for h in holes]

    kb.set_plate_raise(20.0)
    new_holes = kb.mounting_holes()
    for h in new_holes:
        assert h.height == pytest.approx(20.0)


def test_switch_bottom_protrusion():
    kb = _keyboard_from_pipeline()
    assert kb.switch_bottom_protrusion == pytest.approx(3.5)
