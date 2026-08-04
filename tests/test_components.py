"""Tests for component config plumbing."""

from components.display_88 import Display88
from components.hdmi_driver import HdmiDriver
from components.battery import Battery


def test_display_flex_config():
    d = Display88({
        "width": 231.0,
        "height": 64.5,
        "thickness": 6.5,
        "flex": {"width": 38.5, "thickness": 1.0, "fold": 6.0},
    })
    assert d._flex_width == 38.5
    assert d._flex_thickness == 1.0
    assert d._flex_fold == 6.0


def test_display_flex_defaults():
    d = Display88({"width": 231.0, "height": 64.5, "thickness": 6.5})
    assert d._flex_width == 38.5
    assert d._flex_thickness == 1.0
    assert d._flex_fold == 6.0


def test_hdmi_driver_fpc_slot():
    h = HdmiDriver({"driver_board": {"fpc_slot_height": 1.5}})
    assert h._fpc_slot_height == 1.5


def test_hdmi_driver_fpc_slot_default():
    h = HdmiDriver({"driver_board": {}})
    assert h._fpc_slot_height == 1.0


def test_battery_config():
    b = Battery({"battery": {"width": 60, "depth": 35, "height": 8, "clearance": 2.0}})
    assert b.size().width == 60
    assert b.size().depth == 35
    assert b.size().height == 8
    assert b.clearance == 2.0


def test_battery_defaults():
    b = Battery({})
    assert b.size().width == 60
    assert b.size().depth == 35
    assert b.size().height == 8
