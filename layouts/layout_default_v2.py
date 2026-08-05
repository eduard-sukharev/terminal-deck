"""Constraint-based default clamshell layout.

Replicates the original ``LayoutDefault`` placement using declarative
constraints. The constraint recipe mirrors the original layout's intent:

* keyboard front edge at enclosure front minus palm rest
* keyboard centered on X
* SBC behind the keyboard with a 6 mm gap
* SBC centered on X
* keyboard + SBC pair centered on Y (rebalancing)
* battery beside the SBC
* display centered in the lid at the stacking height
* driver board behind the display
"""

from __future__ import annotations

from typing import Any

from utilities.constants import CONNECTOR_HDMI

from layouts.constraints import (
    CablePath,
    CenteredGroup,
    CenteredOn,
    FixedPosition,
    KeyboardMountingHoles,
    RelativePlacement,
    ZStack,
)
from layouts.layout_constrained import ConstraintLayout


class LayoutDefaultV2(ConstraintLayout):
    """Default clamshell layout (constraint-based).

    Replicates the original ``LayoutDefault`` placement:

    * keyboard at y = SBC.depth/2 + palm_rest, centered on X
    * SBC behind keyboard with 6 mm gap, centered on X
    * keyboard + SBC pair centered on Y (rebalancing)
    * battery beside the SBC
    * display centered in the lid at z=60
    * driver board behind the display
    """

    name = "default_v2"

    def _build_constraints(self):
        components = self.components
        kb = components["keyboard"].size()
        sb = components["sbc"].size()
        bb = components["battery"].size()
        disp = components["display"].size()
        driver = components["driver"]

        front_margin = 20.0
        sbc_gap = 6.0
        battery_gap = 6.0
        lid_z = 60.0

        return [
            # Keyboard: initial Y from SBC depth + palm rest, centered on X.
            FixedPosition(subject="keyboard", y=sb.depth / 2 + front_margin),
            CenteredOn(subject="keyboard", axes=("x",)),
            # SBC: absolute Y behind keyboard (not relative — matches original).
            FixedPosition(subject="sbc", y=-(kb.depth / 2 + sbc_gap)),
            CenteredOn(subject="sbc", axes=("x",)),
            # Rebalance: center the keyboard+SBC pair on Y.
            CenteredGroup(subjects=["keyboard", "sbc"], axes=("y",)),
            # Battery beside the SBC.
            RelativePlacement(
                subject="battery", target="sbc",
                offset_x=sb.width / 2 + battery_gap + bb.width / 2,
            ),
            # Keyboard mounting holes: between rows, near wide keys.
            KeyboardMountingHoles(subject="keyboard"),
            # Base-floor Z stack.
            ZStack(layers=[["keyboard", "sbc", "battery", "usb_breakout"]]),
            # Display centered in the lid at stacking height.
            FixedPosition(subject="display", z=lid_z),
            CenteredOn(subject="display", axes=("x", "y")),
            # Driver board behind the display (below it in Z).
            RelativePlacement(
                subject="driver", target="display",
                offset_x=driver.reference_origin()[0],
                offset_y=driver.reference_origin()[1],
                offset_z=-(driver.size().height
                           if hasattr(driver, "size") else 8.0),
            ),
            # HDMI cable path: SBC → hinge wire tunnel → driver board.
            # The via point is at the hinge center (rear edge, mid-height).
            CablePath(
                from_component="sbc",
                from_connector_type=CONNECTOR_HDMI,
                to_component="driver",
                to_connector_type=CONNECTOR_HDMI,
                via_point=(0.0, -70.0, 30.0),
                clearance_diameter=8.0,
                max_bend_radius=30.0,
            ),
        ]


__all__ = ["LayoutDefaultV2"]
