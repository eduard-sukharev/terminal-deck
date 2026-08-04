"""Hardware components for the cyberdeck.

Every component implements the :class:`~components.base.Component` API so
placement, assembly, and enclosure generation stay generic. See
``docs/component_spec.md`` for the measured values and assumptions.
"""

from components.base import (
    BoundingBox,
    Component,
    Connector,
    Hole,
    Keepout,
)
from components.display_88 import Display88
from components.hdmi_driver import HdmiDriver
from components.heatset_insert import HeatSetInsert
from components.hinge import Hinge, HingePin, WireTunnel
from components.keyboard_plate import KeyboardPlate
from components.orange_pi_zero2w import OrangePiZero2W
from components.rp2040_keyboard import Rp2040Keyboard
from components.rp2040_zero import Rp2040Zero
from components.usb_breakout import UsbBreakout

__all__ = [
    "BoundingBox",
    "Component",
    "Connector",
    "Hole",
    "Keepout",
    "Display88",
    "HdmiDriver",
    "HeatSetInsert",
    "Hinge",
    "HingePin",
    "WireTunnel",
    "KeyboardPlate",
    "OrangePiZero2W",
    "Rp2040Keyboard",
    "Rp2040Zero",
    "UsbBreakout",
]
