"""Slide subsystem: the slider's travel, guide span and face-height budget.

Pure data — no CAD. The screen lid carries two steel Guide rods on its back
panel's inner face, each held by two printed Rod clamps; the printed Bearing
clamps straddle the back panel through a long slot and are seated in the
Chassis Deck (ADR-0010). The closed face height is the binding constraint, so
the budget is derived from the real keyboard/display/driver sizes and the slide
config and checked by the build.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from routing.cable_routing import CONNECTOR_HDMI, MIN_BEND_RADIUS_MM

from geometry.chassis_joint import chassis_joint as chassis_band_joint
from geometry.joint import lid_joint


@dataclass(frozen=True)
class SlideBudget:
    """Derived slide geometry and the face-height budget (all mm)."""

    travel: float
    keyboard_top: float
    rear_band: float
    rear_band_min: float
    rear_band_extension: float
    chassis_height: float
    guide_span: float
    rod_usable: float
    rod_y: float
    rod_clamp_y: tuple[float, float]
    lid_height: float
    closed_face_height: float
    open_face_height: float
    lid_overlap: float
    thickness: float
    width: float
    clamp_width: float
    clamp_body_width: float
    hardware_width: float
    side_pod: float
    draft_allowance: float
    usable_half: float
    rod_x: float
    rod_clamp_width: float
    rod_raise: float
    lid_joint: Any
    chassis_top: float
    chassis_joint: Any
    bearing_model: str
    bearing_length: float
    bearing_per_rod: int
    rod_clamp_length: float
    bearing_clamp_length: float
    slot_span: float
    slot_needed: float
    face_height_limit: float
    chain_bend_radius: float
    cable_min_bend_radius: float

    @property
    def within_face_limit(self) -> bool:
        """The closed face height is a HARD limit."""
        return self.closed_face_height <= self.face_height_limit + 1e-9

    @property
    def slot_fits(self) -> bool:
        """The back-panel slot must contain the Bearing clamp at both poses."""
        return self.slot_span >= self.slot_needed - 1e-9

    @property
    def face_flush(self) -> bool:
        """The closed lid and the chassis share the same face depth (mm)."""
        return abs(self.lid_height - self.chassis_height) <= 1e-9

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
            f"(rear band {self.rear_band:.2f}, of which "
            f"{self.rear_band_extension:.2f} is the lid-driven extension)",
            f"  guide span: {self.guide_span:.2f} mm "
            f"({self.bearing_per_rod}x {self.bearing_model} "
            f"{self.bearing_length:.1f} mm, usable {self.rod_usable:.2f})",
            f"  rod clamps: {self.rod_clamp_length:.1f} mm each end, "
            f"slot {self.slot_span:.2f} / {self.slot_needed:.2f} mm needed",
            f"  lid: {self.lid_height:.2f} mm, overlap in the open pose "
            f"{self.lid_overlap:.2f} mm",
            f"  chassis joint: {self.chassis_joint.station_count} stations, "
            f"band {self.chassis_joint.band:.1f} mm at z "
            f"{self.chassis_joint.parting_z:.2f}, "
            f"{self.chassis_joint.screw.size}x{self.chassis_joint.screw.length} "
            f"(tightest boss {self.chassis_joint.smallest_boss():.2f} mm)",
            f"open face height: {self.open_face_height:.2f} mm",
            f"thickness: {self.thickness:.2f} mm, width: {self.width:.2f} mm "
            f"(side pod {self.side_pod:.2f} incl. draft {self.draft_allowance:.2f}, "
            f"clamp {self.clamp_width:.2f})",
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

    The formulas are the spec's face-height budget (ADR-0009/0010):

    * ``travel = well_front_margin + keyboard.depth + travel_clearance``
      (the lid's lower edge must pass the keyboard's *upper* edge).
    * the Bearing clamp's seat sits at the rear end of the bearing's travel
      envelope; the rear band is the larger of that run and the SBC depth.
    * ``rod_usable = travel + bearings + 2 * (Rod clamp + clearance)``: the
      bearing must not run under the end clamps at either pose.
    * ``guide_span = rod_usable + 2 * end supports``; the lid is the guide
      span plus its top bezel.
    * the lid's guide span is fixed by the mechanism and is the larger half,
      so the chassis grows to the lid's closed face: the two halves are flush
      at the rear and the lid never overhangs the chassis.
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
    controller = _size(components, "controller")

    keyboard_top = slide.well_front_margin + keyboard.depth
    travel = keyboard_top + slide.travel_clearance

    bearing_stack = (
        bearing.per_rod * bearing.length
        + (bearing.per_rod - 1) * slide.clamp_wall
    )
    # The rod must be long enough for the bearing's full travel envelope plus
    # a Rod clamp and a clearance gap at each end.
    rod_clamp_allowance = slide.rod_clamp.length + slide.rod_clamp.clearance
    rod_usable = travel + bearing_stack + 2.0 * rod_clamp_allowance
    rear_band_clamp = slide.rear_band_clamp
    rear_band_contents = sbc.depth + 2 * shell
    rear_band_min = max(rear_band_clamp, rear_band_contents)
    chassis_height_min = keyboard_top + rear_band_min + wall

    guide_span = rod_usable + 2 * rod.end_support
    lid_height = guide_span + slide.top_bezel
    # The lid is the larger half: its guide span is fixed by the purchased
    # bearing and the end clamps, so the chassis grows to meet it instead of
    # the lid overhanging the chassis at the rear. The lid defines the
    # footprint; the chassis rear wall must end flush with it.
    closed_face = max(chassis_height_min, lid_height)
    chassis_height = closed_face
    rear_band = chassis_height - keyboard_top - wall
    rear_band_extension = max(0.0, chassis_height - chassis_height_min)
    open_face = max(chassis_height, lid_height + travel)
    # How much of the lid still overlaps the chassis (and so its clamp) when
    # open: the lid's own overhang and the top bezel must not inflate it.
    lid_overlap = min(lid_height, chassis_height) - travel

    chassis_thickness = max(
        keyboard.height,
        wall + sbc.height,
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
        + shell
        - config.bezel.recess
    )

    # The rod sits half-sunk in the back panel: its lowest point is the panel's
    # mid-thickness, so the inverted tray's cavity above it stays as deep as
    # possible. Derived, never tuned.
    rod_raise = rod.diameter / 2.0 - slide.lid_back / 2.0
    if rod_raise <= 0.0:
        raise ValueError(
            "slide.lid_back is too thick for the guide rod: it would swallow the "
            f"rod (lid_back {slide.lid_back} > rod diameter {rod.diameter})"
        )

    clamp_width = bearing.outer_diameter + 2 * slide.clamp_wall
    # The head is the same width as the neck (a cylinder around the bearing);
    # there is no flange. The display only has to clear the moving head, which
    # is the width of the back-panel cutout it travels in.
    clamp_body_width = clamp_width
    hardware_width = clamp_width + 2.0 * slide.slot_clearance
    # The X side walls are drafted, so the lid cavity narrows toward its face
    # panel. The hardware sits on the back panel's inner face and is tallest at
    # its top; widening the side pod by the draft inset over that height keeps
    # the shell clearance there without moving the guide hardware (rod_x stays
    # put because usable_half is unchanged by the side pod).
    hardware_height = max(
        slide.rod_clamp.height,
        rod_raise + clamp_width / 2.0,
    )
    draft_allowance = math.tan(math.radians(config.draft.angle)) * (
        slide.lid_back + hardware_height
    )
    side_pod = (
        slide.component_gap
        + hardware_width
        + wall
        + shell
        + draft_allowance
        + slide.joint.corner_post
    )
    width = max(keyboard.width, display.width) + 2 * side_pod
    # The Tray <-> Deck band joint (ADR-0012): the Parting plane and the ten
    # fastener stations, sized from the chassis plan at that plane.
    chassis_band = chassis_band_joint(
        width=width,
        depth=chassis_height,
        chassis_top=chassis_thickness,
        draft_angle=config.draft.angle,
        minimum_feature=config.material.minimum_feature,
        chamfer=config.corners.chamfer,
        parting=config.parting,
        joint=config.chassis_joint,
    )
    usable_half = width / 2.0 - side_pod
    # Only the moving bearing housing and the fixed Rod clamps live outboard
    # of `usable_half`. The display clears the moving housing; the fixed Rod
    # clamps are Y-separated from it and are checked separately.
    rod_x = usable_half + slide.component_gap + hardware_width / 2.0
    joint = lid_joint(
        width=width,
        lid_height=lid_height,
        lid_back=slide.lid_back,
        rod_x=rod_x,
        rod_clamp_width=slide.rod_clamp.width,
        joint=slide.joint,
        wall=wall,
    )

    rod_clamp_length = slide.rod_clamp.length
    bearing_clamp_length = slide.bearing_clamp.length
    # The rod is inset by one end support from the chassis front, so the lid's
    # end wall stays solid; both Rod clamps sit at its ends.
    rod_y = -chassis_height / 2.0 + rod.end_support + rod_usable / 2.0
    rod_clamp_y = (
        rod_y - rod_usable / 2.0 + rod_clamp_length / 2.0,
        rod_y + rod_usable / 2.0 - rod_clamp_length / 2.0,
    )
    slot_span = rod_usable - 2.0 * rod_clamp_length
    slot_needed = travel + bearing_clamp_length + 2.0 * slide.slot_clearance

    return SlideBudget(
        travel=travel,
        keyboard_top=keyboard_top,
        rear_band=rear_band,
        rear_band_min=rear_band_min,
        rear_band_extension=rear_band_extension,
        chassis_height=chassis_height,
        guide_span=guide_span,
        rod_usable=rod_usable,
        rod_y=rod_y,
        rod_clamp_y=rod_clamp_y,
        lid_height=lid_height,
        closed_face_height=closed_face,
        open_face_height=open_face,
        lid_overlap=lid_overlap,
        thickness=thickness,
        width=width,
        clamp_width=clamp_width,
        clamp_body_width=clamp_body_width,
        hardware_width=hardware_width,
        side_pod=side_pod,
        draft_allowance=draft_allowance,
        usable_half=usable_half,
        rod_x=rod_x,
        rod_clamp_width=slide.rod_clamp.width,
        rod_raise=rod_raise,
        lid_joint=joint,
        chassis_top=chassis_thickness,
        chassis_joint=chassis_band,
        bearing_model=bearing.model,
        bearing_length=bearing.length,
        bearing_per_rod=bearing.per_rod,
        rod_clamp_length=rod_clamp_length,
        bearing_clamp_length=bearing_clamp_length,
        slot_span=slot_span,
        slot_needed=slot_needed,
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


def build_rod_clamp(
    rod_diameter: float,
    rod_raise: float,
    length: float,
    height: float,
    width: float,
    screw: str,
    screw_span: float,
    set_screw: str,
):
    """A printed clamp holding one rod end to the lid back panel.

    Local origin: the back panel's inner face, centred on the rod. The rod
    passes along Y at ``z = rod_raise``; the clamp's two screws drop through it
    into heat-set inserts in the panel, and a set screw from the top locks the
    rod axially.
    """
    from utilities import cad_helpers as ch
    from utilities.fasteners import screw as screw_spec

    ch.require_cad()
    spec = screw_spec(screw)
    set_spec = screw_spec(set_screw)
    block = ch.box_centered(width, length, height)
    block = ch.translate(block, 0.0, 0.0, height / 2.0)
    bore = ch.rotate_x(
        ch.cylinder_centered(rod_diameter + 0.2, length + 2.0), 90.0
    )
    bore = ch.translate(bore, 0.0, 0.0, rod_raise)
    part = ch.cut(block, bore)
    for side in (-1, 1):
        x = side * screw_span / 2.0
        hole = ch.translate(
            ch.cylinder_centered(spec.clearance, height + 2.0), x, 0.0, height / 2.0
        )
        head = ch.translate(
            ch.cylinder_centered(spec.head_diameter, spec.head_depth),
            x,
            0.0,
            height - spec.head_depth / 2.0,
        )
        part = ch.cut(part, hole, head)
    rod_top = rod_raise + rod_diameter / 2.0
    set_hole = ch.translate(
        ch.cylinder_centered(set_spec.pilot_hole, height - rod_top),
        0.0,
        0.0,
        (height + rod_top) / 2.0,
    )
    part = ch.cut(part, set_hole)
    return ch.clean(part)


def build_bearing_clamp(
    bearing_outer: float,
    clamp_wall: float,
    rod_raise: float,
    length: float,
    foot_length: float,
    foot_thickness: float,
    foot_top: float,
    screw: str,
    screw_span_y: float,
    corner_chamfer: float = 0.0,
    top_chamfer: float = 0.0,
):
    """A printed clamp holding the Linear bearing, straddling the back panel.

    Local origin: the back panel's inner face, centred on the rod. The head is
    a **cylinder** coaxial with the bearing, its diameter equal to the neck
    width, so it no longer overhangs the back-panel slot: the rod passing
    through the bearing is what retains the lid. The neck passes through the
    panel slot and the joint gap; the foot sits in the chassis seat pocket.
    ``foot_top`` is the foot's top face in local Z (below the panel, at the
    Deck top): the foot is flush with the chassis top, wholly in the pocket.

    The foot is longer than the bearing, and its two screws sit outboard of the
    bearing's ends, so a screw tip can never reach the bearing or the housing
    above it. ``corner_chamfer`` breaks the foot's four vertical corners
    (matched by the pocket); ``top_chamfer`` breaks the exposed top perimeter
    of the foot (matched by the pocket mouth). The head's circular rims stay
    as formed: an arc chamfer is a different, fragile operation and a round
    rim is already print-friendly.
    """
    from utilities import cad_helpers as ch
    from utilities.fasteners import screw as screw_spec

    ch.require_cad()
    spec = screw_spec(screw)
    head_diameter = bearing_outer + 2.0 * clamp_wall
    foot_bottom = foot_top - foot_thickness

    foot = ch.box_centered(head_diameter, foot_length, foot_thickness)
    if corner_chamfer > 0.0:
        foot = ch.chamfer_vertical_edges(foot, corner_chamfer)
    foot = ch.translate(foot, 0.0, 0.0, foot_bottom + foot_thickness / 2.0)

    # The head is a cylinder around the bearing: same width as the neck, its
    # axis along Y, centred on the rod. Its lower half passes through the
    # back-panel slot and into the foot, so it is unioned after the bore.
    head = ch.rotate_x(ch.cylinder_centered(head_diameter, length), 90.0)
    head = ch.translate(head, 0.0, 0.0, rod_raise)
    # Bore the head *before* the foot is joined: the bore is 0.2 mm larger
    # than the bearing, so cutting the foot too would shave a 0.1 mm groove
    # into its top face. The foot top then becomes the bore's floor, exactly
    # tangent to the bearing.
    bore = ch.rotate_x(
        ch.cylinder_centered(bearing_outer + 0.2, length + 2.0), 90.0
    )
    bore = ch.translate(bore, 0.0, 0.0, rod_raise)
    head = ch.cut(head, bore)

    part = ch.union(head, foot)

    if top_chamfer > 0.0:
        # The exposed top perimeter of the foot (the wings beside the head);
        # the head junction is an inside corner and stays sharp.
        top_edges = [
            edge
            for edge in ch.convex_edges(part)
            if abs(edge.midpoint[2] - foot_top) < 1e-6
            and edge.curve_type == "line"
        ]
        part = ch.chamfer_edges(part, top_edges, top_chamfer)

    # Two screws from inside the chassis, through the seat floor into the foot.
    # The span is wider than the bearing, so the tips land outside it.
    pilot_depth = foot_thickness - 1.0
    for side in (-1, 1):
        y = side * screw_span_y / 2.0
        pilot = ch.translate(
            ch.cylinder_centered(spec.pilot_hole, pilot_depth),
            0.0,
            y,
            foot_bottom + pilot_depth / 2.0,
        )
        part = ch.cut(part, pilot)
    return ch.clean(part)


__all__ = [
    "SlideBudget",
    "build_bearing_clamp",
    "build_guide_rod",
    "build_linear_bearing",
    "build_rod_clamp",
    "compute_slide_budget",
]
