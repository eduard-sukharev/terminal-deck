"""Slider screen lid: an inverted-tray Bezel closed by a flat back panel.

First-generation shell (issue #3). The tray's front carries the glass opening;
the back panel faces the keyboard and is cut with the two guide-rod
C-channels. The rods and bearings are separate purchased parts (the ``slide``
target), and Sections/fastening are the next iteration.
"""

from __future__ import annotations

from typing import Any

from case.slider_frame import SliderFrame


class ScreenLid:
    """The upper half of the slider: bezel tray, back panel, guide channels."""

    def __init__(self, config: Any, frame: SliderFrame) -> None:
        self.config = config
        self.frame = frame

    def build(self):
        """Return the screen-lid shell with the glass opening and C-channels."""
        from utilities import cad_helpers as ch

        ch.require_cad()
        f = self.frame
        wall = f.wall

        outer = ch.box_centered(f.width, f.lid_height, f.lid_thickness)
        outer = ch.translate(
            outer, 0.0, f.lid_y_center, f.lid_bottom + f.lid_thickness / 2.0
        )
        outer = ch.fillet_vertical_edges(outer, self.config.corners.radius)

        back = ch.box_centered(f.width, f.lid_height, wall)
        back = ch.translate(back, 0.0, f.lid_y_center, f.lid_bottom + wall / 2.0)
        body = ch.union(outer, back)

        # Interior cavity: inset by the solid side pod and the end walls; open
        # through the bottom so the panel/driver drop in from the back.
        cavity = ch.box_centered(
            f.width - 2.0 * f.pod_solid,
            f.lid_height - 2.0 * wall,
            f.lid_thickness - 2.0 * wall,
        )
        cavity = ch.translate(
            cavity, 0.0, f.lid_y_center, f.lid_bottom + f.lid_thickness / 2.0
        )
        body = ch.cut(body, cavity)

        # Guide-rod C-channels: the Bearing clamps enter from below; the
        # outer skin and the top band keep the rod contained.
        for side in (-1, 1):
            channel = ch.box_centered(
                f.clamp_width,
                f.lid_height - 2.0 * wall,
                f.clamp_top - f.lid_bottom + 1.0,
            )
            channel = ch.translate(
                channel,
                side * f.rod_x,
                f.lid_y_center,
                (f.lid_bottom - 1.0 + f.clamp_top) / 2.0,
            )
            body = ch.cut(body, channel)

        # Glass opening through the front wall, inside the bezel inset.
        inset = self.config.bezel.inset
        window = ch.box_centered(
            f.display_w - 2.0 * inset,
            f.display_d - 2.0 * inset,
            3.0 * wall,
        )
        window = ch.translate(
            window,
            0.0,
            f.display_y,
            f.lid_bottom + f.lid_thickness - wall / 2.0,
        )
        body = ch.cut(body, window)
        return ch.clean(body)

    def sections(self) -> tuple[Any, Any]:
        """Split the lid into its left and right printable Sections."""
        from utilities import cad_helpers as ch

        return ch.split_x(self.build())


__all__ = ["ScreenLid"]
