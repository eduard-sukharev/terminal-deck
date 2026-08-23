"""Tests for component config plumbing."""

import pytest

from components.display_88 import Display88
from components.hdmi_driver import HdmiDriver
from components.battery import Battery


def test_display_flex_config():
    d = Display88({
        "width": 231.0,
        "height": 64.5,
        "thickness": 6.5,
        "flex": {"width": 38.5, "thickness": 1.0, "fold": 6.0, "edge_protrusion": 1.0},
    })
    assert d._flex_width == 38.5
    assert d._flex_thickness == 1.0
    assert d._flex_fold == 6.0
    assert d._flex_edge_protrusion == 1.0


def test_display_flex_defaults():
    d = Display88({"width": 231.0, "height": 64.5, "thickness": 6.5})
    assert d._flex_width == 38.5
    assert d._flex_thickness == 1.0
    assert d._flex_fold == 6.0
    assert d._flex_edge_protrusion == 0.75


def test_hdmi_driver_fpc_slot():
    h = HdmiDriver({"driver_board": {"fpc_slot_height": 1.5}})
    assert h._fpc_slot_height == 1.5


def test_hdmi_driver_fpc_slot_default():
    h = HdmiDriver({"driver_board": {}})
    assert h._fpc_slot_height == 1.0


def test_battery_side_by_side():
    """Two cells barrel-to-barrel: 2 diameters wide, one length deep."""
    b = Battery({"battery": {
        "cell_diameter": 18.6, "cell_length": 65.2,
        "count": 2, "arrangement": "side_by_side", "clearance": 2.0,
    }})
    assert b.size().width == pytest.approx(37.2)
    assert b.size().depth == pytest.approx(65.2)
    assert b.size().height == pytest.approx(18.6)
    assert b.clearance == 2.0


def test_battery_end_to_end():
    """Two cells cap-to-cap: one diameter wide, 2 lengths deep."""
    b = Battery({"battery": {
        "cell_diameter": 18.6, "cell_length": 65.2,
        "count": 2, "arrangement": "end_to_end",
    }})
    assert b.size().width == pytest.approx(18.6)
    assert b.size().depth == pytest.approx(130.4)
    assert b.size().height == pytest.approx(18.6)


def test_battery_defaults_to_two_18650_side_by_side():
    b = Battery({})
    assert b.count == 2
    assert b.size().width == pytest.approx(37.2)
    assert b.size().depth == pytest.approx(65.2)
    assert b.size().height == pytest.approx(18.6)


def test_battery_cell_centers_are_spaced_by_geometry():
    """Cell centers come from diameter/length, not hardcoded offsets."""
    b = Battery({"battery": {"count": 3, "arrangement": "side_by_side"}})
    xs = sorted(x for x, _ in b._cell_centers())
    assert xs == pytest.approx([-18.6, 0.0, 18.6])
    assert b.size().width == pytest.approx(3 * 18.6)


def test_battery_rejects_unknown_arrangement():
    with pytest.raises(ValueError, match="arrangement"):
        Battery({"battery": {"arrangement": "stacked"}})


def test_battery_rejects_zero_count():
    with pytest.raises(ValueError, match="count"):
        Battery({"battery": {"count": 0}})
