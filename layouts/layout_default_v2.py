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
    PortAccess,
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
        hb = components["usb_breakout"].size()
        disp = components["display"].size()
        driver = components["driver"]

        front_margin = 20.0
        sbc_gap = 6.0
        battery_gap = 6.0
        # The hub's west edge (its stiff ribbon cable) needs more room to bend
        # than a bare clearance gap; its blank south edge needs none beyond
        # the usual shell clearance, since nothing sits directly against it.
        hub_cable_clearance = 20.0
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
            # USB hub beside the battery, in the case's rear-right corner.
            # Its long north edge (3x USB-A + micro-SD + audio + USB-C) faces
            # the rear wall and its single east-edge USB-A faces the right
            # wall — two adjacent walls, since the board has no mounting
            # holes of its own and relies on this cradle fit. Getting both
            # edges to face outward from the SAME corner needs the board
            # mounted upside down (flip): an unflipped Z-rotation can only
            # pair "rear + left" or "front + right", never "rear + right",
            # since the two edges are rigidly 90° apart on the physical PCB.
            # Flipped, its top face sits at offset_z=hb.height and the body
            # hangs down to the floor (z=0), same as an unflipped board
            # sitting on the floor. Its west edge (the stiff ribbon cable)
            # ends up facing the battery, with extra room to bend.
            RelativePlacement(
                subject="usb_breakout", target="battery",
                offset_x=bb.width / 2 + hub_cable_clearance + hb.width / 2,
                offset_z=hb.height,
                rotation=0.0,
                flip=True,
            ),
            # Keyboard mounting holes: between rows, near wide keys.
            KeyboardMountingHoles(subject="keyboard"),
            # Base-floor Z stack (usb_breakout is flipped and gets its z set
            # explicitly above, since this resolver would otherwise overwrite
            # it with a flip-unaware z=0).
            ZStack(layers=[["keyboard", "sbc", "battery"]]),
            PortAccess(subject="usb_breakout", connector_type="USB-A", wall="rear"),
            # Display centered in the lid at stacking height.
            FixedPosition(subject="display", z=lid_z),
            CenteredOn(subject="display", axes=("x", "y")),
            # Driver board flat against the panel back (flipped), rotated 180°
            # so its FPC slot faces the panel ribbon. offset_z=-0.5 keeps the
            # PCB backside 0.5 mm off the panel; a flipped board hangs below
            # its origin, so the driver's top face sits 0.5 mm below the
            # display's Z.
            RelativePlacement(
                subject="driver", target="display",
                offset_x=driver.reference_origin()[0],
                offset_y=driver.reference_origin()[1],
                offset_z=-0.5,
                rotation=180.0,
                flip=True,
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
                bend_radius=30.0,
            ),
        ]


__all__ = ["LayoutDefaultV2"]
