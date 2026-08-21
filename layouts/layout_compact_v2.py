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

            # USB hub behind the SBC, in the case's rear-right corner. Its
            # long north edge (3x USB-A + micro-SD + audio + USB-C) faces the
            # rear wall and its single east-edge USB-A faces the right wall —
            # two adjacent walls, as the board has no mounting holes of its
            # own and relies on this cradle fit. Getting both edges to face
            # outward from the SAME corner needs the board mounted upside
            # down (flip): an unflipped Z-rotation can only pair "rear +
            # left" or "front + right", never "rear + right", since the two
            # edges are rigidly 90° apart on the physical PCB. Flipped, its
            # top face sits at z=hb.height and the body hangs down to the
            # floor (z=0), same as an unflipped board sitting on the floor —
            # set directly (not through the shared ZStack layer below, which
            # assigns a flip-unaware z=0 to everything in it).
            if hub is not None:
                hb = hub.size()
                hub_y = -(sb.depth / 2 + hb.depth / 2 + 1.0)
                constraints.append(
                    FixedPosition(
                        subject="usb_breakout", x=sbc_x, y=hub_y,
                        z=hb.height, rotation=0.0, flip=True,
                    )
                )

        # Battery on the opposite side of the controller.
        if battery is not None:
            bb = battery.size()
            battery_x = -(cw + 6.0 + bb.width / 2)
            constraints.append(FixedPosition(subject="battery", x=battery_x, y=0.0))

        # Base-floor Z stack (usb_breakout is flipped and gets its z set
        # explicitly above, since this resolver would otherwise overwrite it
        # with a flip-unaware z=0).
        constraints.append(
            ZStack(layers=[["keyboard", "sbc", "battery"]])
        )

        # Display centered in the lid at stacking height.
        constraints.append(FixedPosition(subject="display", z=60.0))
        constraints.append(CenteredOn(subject="display", axes=("x", "y")))

        # Driver board flat against the panel back (flipped), rotated 180°
        # so its FPC slot faces the panel ribbon. offset_z=-0.5 keeps the
        # PCB backside 0.5 mm off the panel; a flipped board hangs below its
        # origin.
        if driver is not None:
            constraints.append(
                RelativePlacement(
                    subject="driver", target="display",
                    offset_x=driver.reference_origin()[0],
                    offset_y=driver.reference_origin()[1],
                    offset_z=-0.5,
                    rotation=180.0,
                    flip=True,
                )
            )

        return constraints


__all__ = ["LayoutCompactV2"]
