"""Shared dimensions of the slider case, derived from the layout and budget.

The case is built in the world frame (face-up): X right, Y along the slide
(+Y = screen end), Z up. The values here are the only place the chassis/lid
builders read the placement geometry, so the budget, the layout and the CAD
cannot drift apart silently.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class SliderFrame:
    """World-frame dimensions shared by the chassis and screen-lid builders."""

    width: float
    depth: float
    chassis_top: float
    lid_height: float
    lid_bottom: float
    lid_thickness: float
    front: float
    lid_y_center: float
    wall: float
    clearance: float
    side_pod: float
    pod_solid: float
    clamp_width: float
    usable_half: float
    rod_x: float
    rod_y: float
    rod_z: float
    rod_length: float
    bearing_outer: float
    bearing_bore: float
    bearing_length: float
    clamp_center_y: float
    clamp_len: float
    clamp_top: float
    keyboard_x: float
    keyboard_y: float
    keyboard_w: float
    keyboard_d: float
    display_y: float
    display_w: float
    display_d: float

    @classmethod
    def from_data(cls, config: Any, budget: Any, components: dict, placements: list) -> "SliderFrame":
        keyboard = components["keyboard"]
        display = components["display"]
        keyboard_p = next(p for p in placements if p.component is keyboard)
        display_p = next(p for p in placements if p.component is display)

        wall = config.wall_thickness
        clearance = config.clearance.shell
        chassis_top = keyboard_p.z_bounds()[1]
        lid_bottom = chassis_top + config.slide.lid_clearance
        clamp_width = budget.clamp_width
        rod_x = budget.usable_half + clamp_width / 2.0
        rod_z = lid_bottom + config.slide.lid_back + config.slide.rod.diameter / 2.0
        clamp_center_y = (
            -budget.chassis_height / 2.0
            + budget.travel
            + budget.bearing_length / 2.0
        )
        rod_length = budget.rod_usable
        # The rod's lower end sits at the lid's front edge, so at the open
        # pose (lid +travel) it still covers the bearing's lower end.
        rod_y = -budget.chassis_height / 2.0 + rod_length / 2.0
        return cls(
            width=budget.width,
            depth=budget.chassis_height,
            chassis_top=chassis_top,
            lid_height=budget.lid_height,
            lid_bottom=lid_bottom,
            lid_thickness=budget.thickness - lid_bottom,
            front=-budget.chassis_height / 2.0,
            lid_y_center=-budget.chassis_height / 2.0 + budget.lid_height / 2.0,
            wall=wall,
            clearance=clearance,
            side_pod=budget.side_pod,
            # The side pod is the solid clamp+outer wall; the shell clearance
            # is the air gap between the pod and the widest component inside.
            pod_solid=budget.side_pod - clearance,
            clamp_width=clamp_width,
            usable_half=budget.usable_half,
            rod_x=rod_x,
            rod_y=rod_y,
            rod_z=rod_z,
            rod_length=rod_length,
            bearing_outer=config.slide.bearing.outer_diameter,
            bearing_bore=config.slide.bearing.bore,
            bearing_length=config.slide.bearing.length,
            clamp_center_y=clamp_center_y,
            clamp_len=config.slide.bearing.length + 2.0 * config.slide.clamp_wall,
            clamp_top=rod_z
            + config.slide.bearing.outer_diameter / 2.0
            + config.slide.clamp_wall,
            keyboard_x=(keyboard_p.box[0] + keyboard_p.box[2]) / 2.0,
            keyboard_y=(keyboard_p.box[1] + keyboard_p.box[3]) / 2.0,
            keyboard_w=keyboard.size().width,
            keyboard_d=keyboard.size().depth,
            display_y=(display_p.box[1] + display_p.box[3]) / 2.0,
            display_w=display.size().width,
            display_d=display.size().depth,
        )


__all__ = ["SliderFrame"]
