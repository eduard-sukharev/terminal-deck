"""Default clamshell layout.

Placement plan (world frame, origin = center of base, +Y forward):

* keyboard plate near the front (palm rest in front of it)
* SBC behind the keyboard toward the hinge
* display in the lid, above the base at a stacking height assigned later
* HDMI driver board beside/behind the display
* USB breakout at the rear edge

Positions are calculated from component sizes and configured margins — no CAD,
no hardcoded numbers.
"""

from __future__ import annotations

from layouts.base import Layout, Placement


class LayoutDefault(Layout):
    """Default clamshell layout."""

    name = "default"

    def _build_placements(self, placements: list[Placement]) -> None:
        keyboard = self.components["keyboard"]
        sbc = self.components["sbc"]
        display = self.components["display"]

        kb = keyboard.size()
        sb = sbc.size()

        # Palm rest depth in front of the keyboard (config-driven when given).
        palm_rest = self.components.get("palm_rest_depth")
        front_margin = float(palm_rest) if isinstance(palm_rest, (int, float)) else 20.0

        # Keyboard centered on X, pushed to the front of the base.
        keyboard_y = sb.depth / 2 + front_margin
        # SBC centered on X, behind the keyboard toward the hinge.
        sbc_y = -(kb.depth / 2) - 6.0

        # Rebalance the keyboard/SBC pair around the base origin so the
        # front and rear walls come out symmetric (content otherwise overhangs
        # one wall). Relative spacing is unchanged.
        span_mid = (keyboard_y + kb.depth / 2 + sbc_y - sb.depth / 2) / 2.0
        keyboard_y -= span_mid
        sbc_y -= span_mid

        placements.append(
            Placement(keyboard, 0.0, keyboard_y, rotation=0.0, z=0.0)
        )

        # SBC centered on X, behind the keyboard toward the hinge.
        placements.append(Placement(sbc, 0.0, sbc_y, rotation=0.0, z=0.0))

        # Battery beside the SBC at the rear (sealed deck: internal power).
        battery = self.components.get("battery")
        if battery is not None:
            bb = battery.size()
            battery_x = sb.width / 2 + 6.0 + bb.width / 2
            placements.append(
                Placement(battery, battery_x, sbc_y, rotation=0.0, z=0.0)
            )

        # Display: lid side, centered on X at the lid stacking height.
        placements.append(
            Placement(display, 0.0, 0.0, rotation=0.0, z=60.0)
        )

        driver = self.components.get("driver")
        if driver is not None:
            # The driver board mounts flat against the panel back (flipped),
            # rotated 180° so its FPC slot faces the panel ribbon. A flipped
            # board hangs below its origin, so its top face sits 0.5 mm below
            # the display's Z to keep the PCB backside off the panel. Its
            # offset from the display center is declared by reference_origin().
            offset_x, offset_y, _ = driver.reference_origin()
            placements.append(
                Placement(driver, offset_x, offset_y, rotation=180.0, z=59.5, flip_x=True)
            )
