"""Slide subsystem: the slider's travel, guide span and face-height budget.

Pure data — no CAD. The screen lid carries two steel Guide rods on its back
panel's inner face, each held by two printed Rod clamps; the printed Bearing
clamps straddle the back panel through a long slot and are seated in the
Chassis Deck (ADR-0010/0013). The rods sit **under the display**, so they no
longer set the case width; the moving Bearing-clamp head passes under the
panel instead, which is what sets the lid's thickness. A printed FPC grille
plate guards the display's ribbon where that head sweeps it.

The closed face height is the binding constraint, so the budget is derived from
the real keyboard/display/driver sizes and the slide config and checked by the
build.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from routing.cable_routing import CONNECTOR_HDMI, MIN_BEND_RADIUS_MM

from components.keycap_set import CAP_PLATE_GAP
from geometry.chassis_joint import chassis_joint as chassis_band_joint
from geometry.joint import lid_joint
from utilities import fasteners


@dataclass(frozen=True)
class WelledPlate:
    """The keyboard plate and the Deck's Well (ADR-0014), all mm.

    The Well is a ``ring``-thick ring of Deck walls around a rectangular
    ``cutout``, descending from the Deck's top face to ``plate_top``; the plate
    is a flat sheet one wall wider than the Cutout on every side, so it bears
    on the ring's lower faces from below. Both sizes are derived from the real
    keycap footprint and the wobble allowance -- never chosen.

    ``front_lip``/``rear_lip`` are the solid Deck material outboard of the ring
    (front wall inner face -> ring, and ring -> rear wall inner face); the
    plate's M2 insert bosses are merged to the ring's outer face there, so each
    lip must host one (``boss_lip_required``).

    ``seam`` is the plate's split Seam (the row-jogging path between key
    columns). It rides on the Well because the Well sizes the plate: the Deck's
    insert bosses and the plate's ears are one pattern, so both must read the
    same path from one place.
    """

    keycap_width: float
    keycap_depth: float
    tallest_keycap: float
    wobble: float
    cutout_width: float
    cutout_depth: float
    plate_width: float
    plate_depth: float
    plate_thickness: float
    plate_bottom: float
    plate_top: float
    well_depth: float
    ring: float
    front_lip: float
    rear_lip: float
    boss_lip_required: float
    #: The plate's split Seam (a ``RowSeam``-like path), if the keyboard
    #: component supplied one. The Well is the single source the Deck's bosses
    #: and the plate's ears both derive their stations from.
    seam: Any = None

    @property
    def cutout(self) -> tuple[float, float]:
        """The Well Cutout ``(width, depth)`` — keycap + wobble per side."""
        return (self.cutout_width, self.cutout_depth)

    @property
    def plate(self) -> tuple[float, float]:
        """The plate ``(width, depth)`` — Cutout + one wall per side."""
        return (self.plate_width, self.plate_depth)

    @property
    def front_lip_slack(self) -> float:
        """Material left in the front lip beyond what an M2 boss needs (mm)."""
        return self.front_lip - self.boss_lip_required

    def plate_frame(self, placement):
        """The plate's frame in the chassis plan, from the keyboard's placement.

        The Well sizes the plate; the layout places it (rotated, so the
        spacebar faces the user). This is the one call that joins the two, so
        the Deck's bosses and the plate's ears cannot end up in different
        frames (issue #19).
        """
        from geometry.well_mounts import PlateFrame

        return PlateFrame.from_placement(
            placement,
            width=self.plate_width,
            depth=self.plate_depth,
        )

    def seam_in(self, frame):
        """The split Seam converted into the chassis plan through ``frame``.

        ``seam`` is plate-local (the keyboard model's frame), so the world Seam
        is derived here once, with the same frame the mounts use.
        """
        from geometry.well_mounts import SeamPath

        if self.seam is None:
            return None
        return SeamPath.from_seam(self.seam, self.plate_depth).to_world(frame)

    def summary(self) -> str:
        return (
            f"cutout {self.cutout_width:.2f} x {self.cutout_depth:.2f}, "
            f"plate {self.plate_width:.2f} x {self.plate_depth:.2f} x "
            f"{self.plate_thickness:.1f} at z {self.plate_bottom:.2f} "
            f"(top {self.plate_top:.2f}), ring {self.ring:.1f}, "
            f"wobble {self.wobble:.2f}"
        )


@dataclass(frozen=True)
class RodBounds:
    """The three features the guide stance must clear (X, mm).

    ``post`` is the lid's band corner post (the insert plus its boss margin
    outboard of the Rod clamp), ``seat`` the Deck's Bearing-clamp seat against
    the chassis band's corner boss, and ``head`` the moving clamp head under
    the display. The stance is derived from the tightest of them.
    """

    post: float
    seat: float
    head: float

    @property
    def tightest(self) -> float:
        return min(self.post, self.seat, self.head)

    @property
    def tightest_name(self) -> str:
        values = {"post": self.post, "seat": self.seat, "head": self.head}
        return min(values, key=values.get)


@dataclass(frozen=True)
class SlideBudget:
    """Derived slide geometry and the face-height budget (all mm)."""

    travel: float
    keyboard_top: float
    well_front_margin: float
    well: WelledPlate
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
    head_crown: float
    display_cavity: float
    lid_thickness: float
    rod_x_bounds: RodBounds
    guard_planform: tuple[float, float, float, float]
    fpc_guard: Any
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
    clamp_center_y: float
    face_height_limit: float
    chain_bend_radius: float
    cable_min_bend_radius: float

    @property
    def within_face_limit(self) -> bool:
        """The closed face height is a HARD limit."""
        return self.closed_face_height <= self.face_height_limit + 1e-9

    @property
    def plate_z(self) -> float:
        """The plate's bottom face (ADR-0014): the Deck's Well reaches it."""
        return self.well.plate_bottom

    @property
    def parting_below_plate(self) -> bool:
        """``parting_z <= plate_bottom`` is HARD: the Parting never cuts the Well."""
        return self.chassis_joint.parting_z <= self.well.plate_bottom + 1e-9

    @property
    def front_lip_hosts_boss(self) -> bool:
        """The front lip must hold the plate's M2 insert boss (ADR-0014)."""
        return self.well.front_lip_slack >= -1e-9

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
            f"  well: {self.well.summary()}",
            f"  front margin: {self.well_front_margin:.2f} mm "
            f"(lip {self.well.front_lip:.2f} for a "
            f"{self.well.boss_lip_required:.2f} boss)",
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
            f"thickness: {self.thickness:.2f} mm (lid {self.lid_thickness:.2f}, "
            f"display cavity {self.display_cavity:.2f}), width: {self.width:.2f} mm "
            f"(side pod {self.side_pod:.2f} incl. draft {self.draft_allowance:.2f})",
            f"guides: rod x +/-{self.rod_x:.2f} "
            f"(bounds post {self.rod_x_bounds.post:.2f}, "
            f"seat {self.rod_x_bounds.seat:.2f}, head {self.rod_x_bounds.head:.2f}), "
            f"FPC guard {self.fpc_guard.total:.2f} mm over x "
            f"{self.guard_planform[0]:.2f}..{self.guard_planform[2]:.2f}, "
            f"y +/-{self.guard_planform[3]:.2f}",
            f"drag chain: bend radius {self.chain_bend_radius:.1f} mm "
            f"(cable minimum {self.cable_min_bend_radius:.1f})",
        ]
        return "\n".join(lines)


def _size(components: dict[str, Any], role: str) -> Any:
    component = components.get(role)
    if component is None:
        raise ValueError(f"slide budget needs the {role!r} component")
    return component.size()


def _plate_seam(keyboard_component: Any) -> Any:
    """The plate's split Seam, if the keyboard component can supply it.

    The keyboard assembly exposes its plate model (``plate_model()``), which is
    pure data; a component without one simply carries no Seam and the Well
    leaves it ``None``.
    """
    plate_model = getattr(keyboard_component, "plate_model", None)
    if plate_model is None:
        return None
    return getattr(plate_model(), "seam", None)


def compute_slide_budget(config: Any, components: dict[str, Any]) -> SlideBudget:
    """Derive the travel, guide span and envelope from config + components.

    The formulas are the spec's face-height budget (ADR-0009/0010/0013) and the
    Well's sizing chain (ADR-0014):

    * the **Cutout** is the keycap footprint plus the wobble allowance per
      side; the **plate** is the Cutout plus one wall per side, so it bears on
      the Well walls' lower faces.
    * ``plate_z = chassis_top - tallest_keycap - CAP_PLATE_GAP -
      plate_thickness``: the plate sits one cap stack below the Deck's top, so
      the Well is exactly as deep as the keycaps need. ``parting_z`` must stay
      below it (HARD).
    * the **front margin** is the face-height budget's remainder:
      ``face_height_limit - lid stack - plate.depth``, floored by the front lip
      that has to host the plate's M2 insert boss (ADR-0014).
    * ``travel = well_front_margin + plate.depth + travel_clearance`` (the
      lid's lower edge must pass the keyboard's *upper* edge).
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

    keyboard_component = components.get("keyboard")
    if keyboard_component is None:
        raise ValueError("slide budget needs the 'keyboard' component")
    keyboard = keyboard_component.size()
    display = _size(components, "display")
    # Required: the FPC guard's planform is anchored to its FPC connector.
    _size(components, "driver")
    sbc = _size(components, "sbc")
    controller = _size(components, "controller")

    # -- The Well's Cutout and the plate (ADR-0014) -----------------------
    # The Cutout is the real keycap footprint plus the wobble allowance; the
    # plate is one wall wider on each side so it reaches under the Well walls
    # and bears on their lower faces.
    keycap_width, keycap_depth, tallest_keycap = keyboard_component.keycap_envelope()
    wobble = config.keyboard.plate_wobble
    cutout_width = keycap_width + 2.0 * wobble
    cutout_depth = keycap_depth + 2.0 * wobble
    plate_width = cutout_width + 2.0 * wall
    plate_depth = cutout_depth + 2.0 * wall
    plate_thickness = config.keyboard.plate_thickness

    # The chassis' Z stack: the keyboard is the tallest content unless a buried
    # part is. The Deck's top is the keycap stack above the plate.
    chassis_thickness = max(
        keyboard.height,
        wall + sbc.height,
        wall + controller.height,
    )
    # Slaved to the tallest keycap: the Well always reaches the plate's top.
    plate_z = (
        chassis_thickness - tallest_keycap - CAP_PLATE_GAP - plate_thickness
    )

    bearing_stack = (
        bearing.per_rod * bearing.length
        + (bearing.per_rod - 1) * slide.clamp_wall
    )
    # The rod must be long enough for the bearing's full travel envelope plus
    # a Rod clamp and a clearance gap at each end.
    rod_clamp_allowance = slide.rod_clamp.length + slide.rod_clamp.clearance

    # -- The face-height budget derives the front margin (ADR-0014) -------
    # Everything between the keyboard's top and the closed face: the travel's
    # clearance, the bearing, the two Rod clamps and their gaps, the lid's end
    # supports and its top bezel. The margin is what the HARD limit leaves
    # after the plate.
    lid_stack = (
        slide.travel_clearance
        + bearing_stack
        + 2.0 * rod_clamp_allowance
        + 2.0 * rod.end_support
        + slide.top_bezel
    )
    # The floor: the front lip is the Deck material between the front wall's
    # inner face and the Well ring. An M2 insert boss merged to the ring's
    # outer face needs the bore's merged-boss margin, the insert hole and the
    # boss margin around it.
    plate_screw = fasteners.heat_insert(
        str((config.keyboard.mounting or {}).get("screw", "M2"))
    )
    boss_lip_required = (
        config.merged_boss.bore_margin
        + plate_screw.printed_hole_diameter
        + config.chassis_joint.boss_margin
    )
    front_margin_floor = wall + boss_lip_required
    well_front_margin = max(
        slide.face_height_limit - lid_stack - plate_depth,
        front_margin_floor,
    )
    keyboard_top = well_front_margin + plate_depth
    travel = keyboard_top + slide.travel_clearance

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

    # -- The Well and the plate, sized from the numbers above --------------
    well = WelledPlate(
        keycap_width=keycap_width,
        keycap_depth=keycap_depth,
        tallest_keycap=tallest_keycap,
        wobble=wobble,
        cutout_width=cutout_width,
        cutout_depth=cutout_depth,
        plate_width=plate_width,
        plate_depth=plate_depth,
        plate_thickness=plate_thickness,
        plate_bottom=plate_z,
        plate_top=plate_z + plate_thickness,
        well_depth=chassis_thickness - (plate_z + plate_thickness),
        ring=wall,
        front_lip=well_front_margin - wall,
        rear_lip=rear_band,
        boss_lip_required=boss_lip_required,
        # The plate's Seam rides on the Well: the Deck's insert bosses and the
        # plate's ears are one pattern (the face-height budget above already
        # read the keyboard component, so the path costs nothing extra here).
        seam=_plate_seam(keyboard_component),
    )

    # -- The moving head has to pass under the display --------------------
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
    # The head's crown: the highest point the moving clamp reaches above the
    # back panel's inner face.
    head_crown = rod_raise + clamp_width / 2.0
    guard = slide.fpc_guard
    # The display's back must clear the head's crown by the component gap and
    # the documented sag allowance, plus the guard plate bonded to it.
    display_cavity = (
        head_crown + slide.component_gap + guard.sag_allowance + guard.total
    )
    lid_thickness = (
        slide.lid_back
        + display_cavity
        + display.height
        + slide.lid_front
        + shell
        - config.bezel.recess
    )
    thickness = chassis_thickness + slide.lid_clearance + lid_thickness

    # -- Width: the content plus the drafted side wall --------------------
    # The guide hardware is inboard now, so nothing but the display sets the
    # width. The lid's X side walls are drafted: the cavity narrows from the
    # prismatic band toward the face panel, so the side pod has to include the
    # draft inset over the display's height.
    display_top = display_cavity + display.height
    cavity_z1 = lid_thickness - slide.lid_front  # the front panel's inner face
    taper_height = max(
        0.0, min(display_top, cavity_z1) - slide.joint.band
    )
    draft_allowance = math.tan(math.radians(config.draft.angle)) * taper_height
    side_pod = wall + shell + draft_allowance
    # The keyboard plate is wider than the display (ADR-0014: it grew to bear
    # on the Well ring), so the Well plate is the width driver; the display is
    # only the fallback content reference.
    content_width = max(plate_width, display.width)
    width = content_width + 2 * side_pod
    # The Tray <-> Deck band joint (ADR-0012): the Parting plane and the ten
    # fastener stations, sized from the chassis plan at that plane.
    chassis_band = chassis_band_joint(
        width=width,
        depth=chassis_height,
        chassis_top=chassis_thickness,
        content_y1=-chassis_height / 2.0 + keyboard_top,
        draft_angle=config.draft.angle,
        minimum_feature=config.material.minimum_feature,
        chamfer=config.corners.chamfer,
        parting=config.parting,
        joint=config.chassis_joint,
        head_fit=config.clearance.head,
    )
    # `parting_z <= plate_bottom` is HARD (ADR-0014): the Tray/Deck Parting
    # must never cut through the Well, or the plate's bearing ring is split.
    if chassis_band.parting_z > plate_z + 1e-9:
        raise ValueError(
            "the chassis Parting plane cuts the keyboard Well: parting_z "
            f"{chassis_band.parting_z:.2f} > plate_bottom {plate_z:.2f} "
            "(ADR-0014 requires the Parting below the plate)"
        )
    # `usable_half` is the inner wall at the content's plane: what the layout
    # may fill before the shell clearance runs out.
    usable_half = width / 2.0 - side_pod

    # -- Guide stance: bounded by the three features it must clear --------
    insert_hole = fasteners.heat_insert(slide.joint.screw).printed_hole_diameter
    post_bound = (
        width / 2.0
        - wall
        - slide.joint.corner_clearance
        - slide.rod_clamp.width / 2.0
        - (insert_hole + 2.0 * slide.joint.boss_margin)
    )
    seat_half = (
        clamp_width / 2.0
        + slide.bearing_clamp.seat_fit
        + slide.bearing_clamp.seat_wall
    )
    seat_bound = (
        width / 2.0
        - config.chassis_joint.station_inset
        - config.chassis_joint.boss / 2.0
        - config.material.minimum_feature
        - seat_half
    )
    head_bound = display.width / 2.0 - clamp_width / 2.0
    rod_bounds = RodBounds(post=post_bound, seat=seat_bound, head=head_bound)
    rod_x = rod_bounds.tightest - rod.side_margin

    joint = lid_joint(
        width=width,
        lid_height=lid_height,
        lid_back=slide.lid_back,
        rod_x=rod_x,
        rod_clamp_width=slide.rod_clamp.width,
        joint=slide.joint,
        wall=wall,
        chamfer=config.corners.chamfer,
        minimum_feature=config.material.minimum_feature,
        head_fit=config.clearance.head,
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
    # The Bearing clamp's seat sits at the middle of its travel envelope.
    clamp_center_y = rod_y + travel / 2.0

    # -- The FPC guard's planform, in the display's own frame -------------
    # Bonded to the display's back: it starts at the driver's FPC connector
    # (the ribbon enters there) and spans the head's sweeps with margin, over
    # the ribbon's full width. The east end stays inside the display's shadow
    # so it can never pierce the drafted lid wall.
    flex = config.display.flex
    ribbon_half = flex.width / 2.0 if flex is not None else 0.0
    driver_component = components["driver"]
    guard_x0 = (
        driver_component.offset_x
        + driver_component.width / 2.0
        + guard.fit
    )
    guard_x1 = min(
        display.width / 2.0,
        rod_x + hardware_width / 2.0 + guard.margin,
    )
    guard_planform = (
        guard_x0,
        -(ribbon_half + guard.margin),
        guard_x1,
        ribbon_half + guard.margin,
    )

    return SlideBudget(
        travel=travel,
        keyboard_top=keyboard_top,
        well_front_margin=well_front_margin,
        well=well,
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
        head_crown=head_crown,
        display_cavity=display_cavity,
        lid_thickness=lid_thickness,
        rod_x_bounds=rod_bounds,
        guard_planform=guard_planform,
        fpc_guard=guard,
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
        clamp_center_y=clamp_center_y,
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
    from utilities.fasteners import head as head_spec
    from utilities.fasteners import screw as screw_spec

    ch.require_cad()
    spec = screw_spec(screw)
    spec_head = head_spec(screw, "cap")
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
            ch.cylinder_centered(spec_head.diameter, spec_head.depth),
            x,
            0.0,
            height - spec_head.depth / 2.0,
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
    "WelledPlate",
    "build_bearing_clamp",
    "build_guide_rod",
    "build_linear_bearing",
    "build_rod_clamp",
    "compute_slide_budget",
]
