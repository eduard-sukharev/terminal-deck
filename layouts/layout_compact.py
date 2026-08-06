"""Compact clamshell layout (sealed deck).

A tighter variant for the sealed build: the keyboard plate covers the whole
base floor, so everything else lives *under* the raised plate — the RP2040
controller (at the plate center), the SBC buried alongside it, and the battery
beside the controller. The only external connectivity is a multifunctional USB
hub at the rear. The display and driver board sit in the lid, matching the
default layout's stacking height.

The base is slightly thicker than the default to give the buried components and
wiring clearance beneath the raised plate (``controller.z_clearance``).

Positions are calculated from component sizes and configured margins — no CAD.
"""

from __future__ import annotations

from layouts.base import Layout, Placement


class LayoutCompact(Layout):
    """Compact clamshell layout."""

    name = "compact"

    def _build_placements(self, placements: list[Placement]) -> None:
        keyboard = self.components["keyboard"]
        display = self.components["display"]
        sbc = self.components.get("sbc")
        battery = self.components.get("battery")
        hub = self.components.get("usb_breakout")

        # Keyboard centered on the base origin; the plate is raised on standoffs
        # in the component's own build (space beneath holds the buried parts).
        placements.append(Placement(keyboard, 0.0, 0.0, rotation=0.0, z=0.0))

        # Controller half-width (under the plate center) for offsetting buried
        # components so they clear it.
        controller = getattr(keyboard, "controller", None)
        cw = controller.size().width / 2 if controller is not None else 12.0

        # SBC buried under the raised plate, offset in X from the controller.
        # Its ports are internal — the sealed deck exposes only the rear hub.
        if sbc is not None:
            sb = sbc.size()
            sbc_x = cw + 6.0 + sb.width / 2
            placements.append(Placement(sbc, sbc_x, 0.0, rotation=0.0, z=0.0))

            # USB hub behind the SBC, sockets facing the rear wall (rotation
            # 180 turns its +Y connector toward -Y). Placed so the connector
            # sits just inside the rear wall (distance ~1 mm).
            if hub is not None:
                hb = hub.size()
                hub_x = sbc_x
                hub_y = -(sb.depth / 2 + hb.depth / 2 + 1.0)
                placements.append(
                    Placement(hub, hub_x, hub_y, rotation=180.0, z=0.0)
                )

        # Battery beside the controller on the opposite side of the SBC.
        if battery is not None:
            bb = battery.size()
            battery_x = -(cw + 6.0 + bb.width / 2)
            placements.append(
                Placement(battery, battery_x, 0.0, rotation=0.0, z=0.0)
            )

        # Display and driver in the lid, same stacking as the default layout.
        placements.append(
            Placement(display, 0.0, 0.0, rotation=0.0, z=60.0)
        )

        driver = self.components.get("driver")
        if driver is not None:
            # Driver board flat against the panel back (flipped), rotated 180°
            # so its FPC slot faces the panel ribbon. A flipped board hangs
            # below its origin, so its top face sits 0.5 mm below the
            # display's Z to keep the PCB backside off the panel.
            offset_x, offset_y, _ = driver.reference_origin()
            placements.append(
                Placement(driver, offset_x, offset_y, rotation=180.0, z=59.5, flip_x=True)
            )
