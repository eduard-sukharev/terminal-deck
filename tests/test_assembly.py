"""Tests for assembly helpers (select_placements)."""

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
