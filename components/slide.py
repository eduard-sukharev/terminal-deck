"""Slide subsystem: the slider's travel, guide span and face-height budget.

Pure data — no CAD. The screen lid rides two steel guide rods that live inside
its side walls; one LM...LUU bearing per rod is clamped in a Bearing clamp
standing on the chassis deck behind the keyboard (ADR-0009). The closed face
height is the binding constraint, so the budget is derived from the real
keyboard/display/driver sizes and the slide config and checked by the build.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from routing.cable_routing import CONNECTOR_HDMI, MIN_BEND_RADIUS_MM


@dataclass(frozen=True)
class SlideBudget:
    """Derived slide geometry and the face-height budget (all mm)."""

    travel: float
    keyboard_top: float
    rear_band: float
    chassis_height: float
    guide_span: float
    rod_usable: float
    lid_height: float
    closed_face_height: float
    open_face_height: float
    lid_overlap: float
    thickness: float
    width: float
    clamp_width: float
    side_pod: float
    usable_half: float
    bearing_model: str
    bearing_length: float
    bearing_per_rod: int
    face_height_limit: float
    chain_bend_radius: float
    cable_min_bend_radius: float

    @property
    def within_face_limit(self) -> bool:
        """The closed face height is a HARD limit."""
        return self.closed_face_height <= self.face_height_limit + 1e-9

    @property
    def chain_bend_ok(self) -> bool:
        """The drag chain must not bend the cable tighter than its minimum."""
        return self.chain_bend_radius >= self.cable_min_bend_radius

    def summary(self) -> str:
        """Human-readable budget, printed by the data pipeline."""
        status = "PASS" if self.within_face_limit else "FAIL"
        lines = [
            f"closed face height: {self.closed_face_height:.2f} mm "
            f"(limit {self.face_height_limit:.1f}, {status})",
            f"  travel: {self.travel:.2f} mm "
            f"(keyboard top {self.keyboard_top:.2f} + clearance)",
            f"  chassis: {self.chassis_height:.2f} mm "
            f"(rear band {self.rear_band:.2f})",
            f"  guide span: {self.guide_span:.2f} mm "
            f"({self.bearing_per_rod}x {self.bearing_model} "
            f"{self.bearing_length:.1f} mm, usable {self.rod_usable:.2f})",
            f"  lid: {self.lid_height:.2f} mm, overlap in the open pose "
            f"{self.lid_overlap:.2f} mm",
            f"open face height: {self.open_face_height:.2f} mm",
            f"thickness: {self.thickness:.2f} mm, width: {self.width:.2f} mm "
            f"(side pod {self.side_pod:.2f}, clamp {self.clamp_width:.2f})",
            f"drag chain: bend radius {self.chain_bend_radius:.1f} mm "
            f"(cable minimum {self.cable_min_bend_radius:.1f})",
        ]
        return "\n".join(lines)


def _size(components: dict[str, Any], role: str) -> Any:
    component = components.get(role)
    if component is None:
        raise ValueError(f"slide budget needs the {role!r} component")
    return component.size()


def compute_slide_budget(config: Any, components: dict[str, Any]) -> SlideBudget:
    """Derive the travel, guide span and envelope from config + components.

    The formulas are the spec's face-height budget (ADR-0009):

    * ``travel = well_front_margin + keyboard.depth + travel_clearance``
      (the lid's lower edge must pass the keyboard's *upper* edge).
    * the clamp's rear edge lands at ``travel + bearings + clamp_wall``: the
      open lid's lower edge is at the travel and the bearing starts there.
    * the rear band is the larger of that clamp run and the SBC/hub depth, so
      a deeper rear-band component grows the chassis instead of silently
      poking through the clamp.
    * ``guide_span = travel + bearings + end supports``; the lid is the guide
      span plus its top bezel. The usable rod span is the guide span minus
      the end supports.
    """
    slide = config.slide
    bearing = slide.bearing
    rod = slide.rod
    wall = config.wall_thickness
    shell = config.clearance.shell

    keyboard = _size(components, "keyboard")
    display = _size(components, "display")
    driver = _size(components, "driver")
    sbc = _size(components, "sbc")
    hub = _size(components, "usb_breakout")
    controller = _size(components, "controller")

    keyboard_top = slide.well_front_margin + keyboard.depth
    travel = keyboard_top + slide.travel_clearance

    bearing_stack = (
        bearing.per_rod * bearing.length
        + (bearing.per_rod - 1) * slide.clamp_wall
    )
    rear_band_clamp = (
        slide.travel_clearance + bearing_stack + slide.clamp_wall
    )
    rear_band_contents = max(sbc.depth, hub.depth) + 2 * shell
    rear_band = max(rear_band_clamp, rear_band_contents)
    chassis_height = keyboard_top + rear_band + wall

    guide_span = travel + bearing_stack + 2 * rod.end_support
    rod_usable = guide_span - 2 * rod.end_support
    lid_height = guide_span + slide.top_bezel
    closed_face = max(chassis_height, lid_height)
    open_face = max(chassis_height, lid_height + travel)
    # How much of the lid still overlaps the chassis (and so its clamp) when
    # open: the lid's own overhang and the top bezel must not inflate it.
    lid_overlap = min(lid_height, chassis_height) - travel

    chassis_thickness = max(
        keyboard.height,
        wall + sbc.height,
        wall + hub.height,
        wall + controller.height,
    )
    thickness = (
        chassis_thickness
        + slide.lid_clearance
        + slide.lid_back
        + slide.driver_gap
        + driver.height
        + display.height
        + slide.lid_front
        + 2 * shell
    )

    clamp_width = bearing.outer_diameter + 2 * slide.clamp_wall
    side_pod = clamp_width + wall + shell
    width = max(keyboard.width, display.width) + 2 * side_pod
    usable_half = width / 2.0 - side_pod

    return SlideBudget(
        travel=travel,
        keyboard_top=keyboard_top,
        rear_band=rear_band,
        chassis_height=chassis_height,
        guide_span=guide_span,
        rod_usable=rod_usable,
        lid_height=lid_height,
        closed_face_height=closed_face,
        open_face_height=open_face,
        lid_overlap=lid_overlap,
        thickness=thickness,
        width=width,
        clamp_width=clamp_width,
        side_pod=side_pod,
        usable_half=usable_half,
        bearing_model=bearing.model,
        bearing_length=bearing.length,
        bearing_per_rod=bearing.per_rod,
        face_height_limit=slide.face_height_limit,
        chain_bend_radius=slide.chain.bend_radius,
        cable_min_bend_radius=MIN_BEND_RADIUS_MM[CONNECTOR_HDMI],
    )


def build_guide_rod(diameter: float, length: float):
    """A steel guide rod as a cylinder along Y, centered on the origin."""
    from utilities import cad_helpers as ch

    ch.require_cad()
    return ch.rotate_x(ch.cylinder_centered(diameter, length), 90.0)


def build_linear_bearing(outer_diameter: float, bore: float, length: float):
    """An LM...LUU bushing as a hollow cylinder along Y, centered on the origin."""
    from utilities import cad_helpers as ch

    ch.require_cad()
    outer = build_guide_rod(outer_diameter, length)
    hole = ch.rotate_x(ch.cylinder_centered(bore, length + 2.0), 90.0)
    return ch.cut(outer, hole)


__all__ = [
    "SlideBudget",
    "build_guide_rod",
    "build_linear_bearing",
    "compute_slide_budget",
]
