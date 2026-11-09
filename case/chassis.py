"""Slider chassis: Tray + Deck with the keyboard Well and Bearing clamps.

First-generation shell (issue #3). It is a valid closed solid that fits the
derived budget and exports STEP/STL/glTF; Sections, Seams, vents and connector
cutouts are the next iteration (see docs/form_factor.md).
"""

from __future__ import annotations

from typing import Any

from case.slider_frame import SliderFrame


class Chassis:
    """The lower half of the slider: a tray, a Deck with the Well and clamps."""

    def __init__(self, config: Any, frame: SliderFrame) -> None:
        self.config = config
        self.frame = frame

    def build(self):
        """Return the chassis shell (tray + deck + two Bearing clamps)."""
        from utilities import cad_helpers as ch

        ch.require_cad()
        f = self.frame
        wall = f.wall

        outer = ch.box_centered(f.width, f.depth, f.chassis_top)
        outer = ch.translate(outer, 0.0, 0.0, f.chassis_top / 2.0)
        outer = ch.fillet_vertical_edges(outer, self.config.corners.radius)

        tray = ch.shell_open_face(outer, wall, ch.FaceRef.TOP)

        deck = ch.box_centered(f.width, f.depth, wall)
        deck = ch.translate(deck, 0.0, 0.0, f.chassis_top - wall / 2.0)
        body = ch.union(tray, deck)

        # The keyboard Well: a through-opening in the deck over the placed
        # keyboard, one shell clearance larger than the plate.
        well = ch.box_centered(
            f.keyboard_w + 2.0 * f.clearance,
            f.keyboard_d + 2.0 * f.clearance,
            3.0 * wall,
        )
        well = ch.translate(
            well, f.keyboard_x, f.keyboard_y, f.chassis_top
        )
        body = ch.cut(body, well)

        body = ch.union(body, self._clamp(-1), self._clamp(1))
        body = self._vents(body)
        return ch.clean(body)

    def _vents(self, body):
        """A row of vertical vent slots through the +Y rear wall."""
        from utilities import cad_helpers as ch

        vents = self.config.slide.vents
        if vents.height <= 0 or vents.end_x < vents.start_x:
            return body
        pitch = vents.slot_width + vents.gap
        x = vents.start_x
        while x <= vents.end_x + 1e-6:
            slot = ch.box_centered(
                vents.slot_width, 3.0 * self.frame.wall, vents.height
            )
            slot = ch.translate(
                slot, x, self.frame.depth / 2.0, vents.z_center
            )
            body = ch.cut(body, slot)
            x += pitch
        return body

    def _clamp(self, side: int):
        """A Bearing clamp standing on the Deck behind the keyboard."""
        from utilities import cad_helpers as ch

        f = self.frame
        block = ch.box_centered(
            f.clamp_width, f.clamp_len, f.clamp_top - f.chassis_top
        )
        block = ch.translate(
            block,
            side * f.rod_x,
            f.clamp_center_y,
            (f.chassis_top + f.clamp_top) / 2.0,
        )
        bore = ch.cylinder_centered(f.bearing_outer + 0.2, f.clamp_len + 4.0)
        bore = ch.rotate_x(bore, 90.0)
        bore = ch.translate(bore, side * f.rod_x, f.clamp_center_y, f.rod_z)
        return ch.cut(block, bore)

    def sections(self) -> tuple[Any, Any]:
        """Split the chassis into its left and right printable Sections."""
        from utilities import cad_helpers as ch

        return ch.split_x(self.build())


__all__ = ["Chassis"]
