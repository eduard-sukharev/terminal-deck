"""Constraint-based compact clamshell layout (sealed deck).

Replicates the original ``LayoutCompact`` placement using declarative
constraints:

* keyboard centered at the base origin
* SBC buried under the raised plate, offset beside the controller
* USB hub behind the SBC, facing rear
* battery on the opposite side of the controller
* display centered in the lid at z=60
* driver board behind the display
"""

from __future__ import annotations

from layouts.constraints import (
    CenteredOn,
    FixedPosition,
    RelativePlacement,
    ZStack,
)
from layouts.layout_constrained import ConstraintLayout


class LayoutCompactV2(ConstraintLayout):
    """Compact clamshell layout (constraint-based)."""

    name = "compact_v2"

    def _build_constraints(self):
        components = self.components
        keyboard = components["keyboard"]
        sbc = components.get("sbc")
        battery = components.get("battery")
        hub = components.get("usb_breakout")
        display = components["display"]
        driver = components.get("driver")

        controller = getattr(keyboard, "controller", None)
        cw = controller.size().width / 2 if controller is not None else 12.0

        constraints = []

        # Keyboard centered at origin.
        constraints.append(FixedPosition(subject="keyboard", x=0.0, y=0.0))

        # SBC buried under the raised plate, offset beside the controller.
        if sbc is not None:
            sb = sbc.size()
            sbc_x = cw + 6.0 + sb.width / 2
            constraints.append(FixedPosition(subject="sbc", x=sbc_x, y=0.0))

            # USB hub behind the SBC, facing rear.
            if hub is not None:
                hb = hub.size()
                hub_y = -(sb.depth / 2 + hb.depth / 2 + 1.0)
                constraints.append(
                    FixedPosition(subject="usb_breakout", x=sbc_x, y=hub_y, rotation=180.0)
                )

        # Battery on the opposite side of the controller.
        if battery is not None:
            bb = battery.size()
            battery_x = -(cw + 6.0 + bb.width / 2)
            constraints.append(FixedPosition(subject="battery", x=battery_x, y=0.0))

        # Base-floor Z stack.
        constraints.append(
            ZStack(layers=[["keyboard", "sbc", "battery", "usb_breakout"]])
        )

        # Display centered in the lid at stacking height.
        constraints.append(FixedPosition(subject="display", z=60.0))
        constraints.append(CenteredOn(subject="display", axes=("x", "y")))

        # Driver board behind the display.
        if driver is not None:
            constraints.append(
                RelativePlacement(
                    subject="driver", target="display",
                    offset_x=driver.reference_origin()[0],
                    offset_y=driver.reference_origin()[1],
                    offset_z=-(driver.size().height
                               if hasattr(driver, "size") else 8.0),
                )
            )

        return constraints


__all__ = ["LayoutCompactV2"]
