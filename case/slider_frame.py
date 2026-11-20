"""Shared dimensions of the slider case, derived from the layout and budget.

The case is built in the world frame (face-up): X right, Y along the slide
(+Y = screen end), Z up. The values here are the only place the chassis/lid
builders read the placement geometry, so the budget, the layout and the CAD
cannot drift apart silently.

The slide hardware follows the reference mechanism: the two guide rods sit in
the screen lid's open cavity on the back panel's inner face, each held by two
printed Rod clamps; a through-slot in the back panel runs between the clamps,
and the printed Bearing clamp straddles the panel and slides along that slot.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from geometry.seam_joint import pin_planes


def _seam_pin_planes(
    config: Any, budget: Any, lid_top: float, panel_inner_z: float
) -> dict[str, tuple[float, bool]]:
    """The Seam pins' planes, with the frame's own derivations cross-checked.

    :func:`geometry.seam_joint.pin_planes` is the single source; the frame
    re-derives the Bezel's panel inner face and the Back plate's inner face
    from its own numbers, so a drift between the two fails the build instead of
    printing a pin into the wrong surface.
    """
    planes = pin_planes(config, budget)
    bezel_expected = lid_top - config.slide.lid_front
    back_expected = panel_inner_z
    if abs(planes["screen_lid_bezel"][0] - bezel_expected) > 1e-6:
        raise ValueError(
            "the Bezel's Seam-pin substrate disagrees with its panel inner "
            f"face ({planes['screen_lid_bezel'][0]:.2f} vs "
            f"{bezel_expected:.2f} mm)"
        )
    if abs(planes["screen_lid_back"][0] - back_expected) > 1e-6:
        raise ValueError(
            "the Back plate's Seam-pin substrate disagrees with its inner "
            f"face ({planes['screen_lid_back'][0]:.2f} vs "
            f"{back_expected:.2f} mm)"
        )
    return planes


@dataclass(frozen=True)
class SliderFrame:
    """World-frame dimensions shared by the chassis and screen-lid builders."""

    width: float
    depth: float
    lid_draft_angle: float
    #: The lid's front/rear (Y) wall draft (degrees): the Tray's base taper.
    lid_taper_angle: float
    chassis_base_width: float
    lid_face_width: float
    lid_face_height: float
    chassis_top: float
    parting_z: float
    chassis_band_z0: float
    chassis_band_z1: float
    chassis_band_width: float
    chassis_joint: Any
    base_taper: Any
    lid_height: float
    lid_bottom: float
    lid_thickness: float
    lid_back: float
    lid_front: float
    panel_outer_z: float
    panel_inner_z: float
    lid_top: float
    band_z0: float
    band_z1: float
    lid_joint: Any
    bezel_recess: float
    #: Per part, the Seam pins' ``(substrate z, fins stand up?)`` (ADR-0006).
    seam_pin_planes: Any
    front: float
    lid_y_center: float
    wall: float
    clearance: float
    side_pod: float
    usable_half: float
    well: Any
    well_front_margin: float
    plate_frame: Any
    plate_z: float
    plate_top_z: float
    clamp_width: float
    clamp_body_width: float
    rod_x: float
    rod_y: float
    rod_z: float
    rod_raise: float
    rod_length: float
    rod_clamp_len: float
    rod_clamp_width: float
    rod_clamp_height: float
    rod_clamp_screw_span: float
    rod_clamp_y: tuple[float, float]
    rod_groove_width: float
    rod_groove_depth: float
    bearing_outer: float
    bearing_bore: float
    bearing_length: float
    clamp_center_y: float
    clamp_len: float
    slot_width: float
    slot_y0: float
    slot_y1: float
    slot_len: float
    foot_length: float
    foot_thickness: float
    foot_top: float
    foot_top_z: float
    foot_bottom_z: float
    seat_width: float
    seat_length: float
    seat_height: float
    seat_bottom: float
    pocket_width: float
    pocket_length: float
    pocket_depth: float
    keyboard_x: float
    keyboard_y: float
    keyboard_w: float
    keyboard_d: float
    display_x: float
    display_y: float
    display_w: float
    display_d: float
    display_z0: float
    head_crown: float
    fpc_guard: Any
    guard_planform: tuple[float, float, float, float]
    guard_channel_width: float
    guard_slot_depth: float
    guard_slot_pitch: float

    @classmethod
    def from_data(cls, config: Any, budget: Any, components: dict, placements: list) -> "SliderFrame":
        keyboard = components["keyboard"]
        display = components["display"]
        keyboard_p = next(p for p in placements if p.component is keyboard)
        display_p = next(p for p in placements if p.component is display)

        slide = config.slide
        wall = config.wall_thickness
        clearance = config.clearance.shell
        chassis_top = keyboard_p.z_bounds()[1]
        chassis_joint = budget.chassis_joint
        if abs(chassis_top - chassis_joint.chassis_top) > 1e-9:
            raise ValueError(
                "slide budget and keyboard disagree on the chassis top "
                f"({chassis_joint.chassis_top:.3f} vs {chassis_top:.3f} mm)"
            )
        parting_z = chassis_joint.parting_z
        chassis_band_z0 = chassis_joint.band_z0
        chassis_band_z1 = chassis_joint.band_z1
        chassis_band_width = chassis_joint.band_width
        chassis_base_width = chassis_joint.base_width
        lid_bottom = chassis_top + slide.lid_clearance
        lid_thickness = budget.thickness - lid_bottom
        panel_outer_z = lid_bottom
        panel_inner_z = lid_bottom + slide.lid_back
        lid_top = lid_bottom + lid_thickness
        joint = budget.lid_joint
        band_z0 = panel_inner_z
        band_z1 = panel_inner_z + joint.band
        # X side-wall draft (ADR-0031): the Tray's are vertical (ADR-0019: the
        # accessory rail needs a flat face); the lid narrows from its face
        # panel down to the prismatic band, so the two halves meet at the
        # closed face at the full width. The front/rear (Y) walls lean at the
        # Tray's own base-taper angle, so both halves show one slope. The Deck
        # and both joint bands are prismatic; only the lid above its band
        # tapers.
        lid_draft_angle = config.draft.lid
        lid_taper_angle = budget.lid_taper_angle
        draft_tan = math.tan(math.radians(lid_draft_angle))
        taper_height = lid_thickness - slide.lid_back - joint.band
        lid_face_width = budget.width - 2.0 * draft_tan * max(taper_height, 0.0)
        lid_face_height = (
            budget.lid_height
            - 2.0 * math.tan(math.radians(lid_taper_angle)) * max(taper_height, 0.0)
        )
        if min(chassis_base_width, lid_face_width, lid_face_height) <= 0.0:
            raise ValueError(
                "draft angle is too large for the case height: the drafted "
                "face would collapse past the centreline"
            )

        front = -budget.chassis_height / 2.0
        # The keyboard placement must sit exactly the derived Well margin behind
        # the chassis front (ADR-0014): the recipe reads that margin from the
        # budget, so a recipe/config drift has to fail here, not move the Well.
        if abs((keyboard_p.box[1] - front) - budget.well_front_margin) > 1e-6:
            raise ValueError(
                "the keyboard placement disagrees with the derived Well front "
                f"margin ({keyboard_p.box[1] - front:.3f} vs "
                f"{budget.well_front_margin:.3f} mm)"
            )
        rod_raise = budget.rod_raise
        rod_z = panel_inner_z + rod_raise
        rod_length = budget.rod_usable
        # The rod is inset by one end support from each lid end, so the lid's
        # end wall stays solid. Its usable span is exactly travel + bearing:
        # at the closed pose its +Y end meets the bearing's +Y end, at the open
        # pose its -Y end meets the bearing's -Y end.
        rod_y = budget.rod_y
        clamp_center_y = rod_y + budget.travel / 2.0

        rod_clamp_len = slide.rod_clamp.length
        rod_clamp_y = budget.rod_clamp_y
        slot_y0 = rod_y - rod_length / 2.0 + rod_clamp_len
        slot_y1 = rod_y + rod_length / 2.0 - rod_clamp_len

        foot_thickness = slide.bearing_clamp.foot_thickness
        # The foot's top is flush with the Deck top: the neck spans the back
        # panel and the joint gap, and the foot sits wholly in the pocket.
        foot_top_z = chassis_top
        foot_bottom_z = foot_top_z - foot_thickness
        pocket_depth = max(0.0, chassis_top - foot_bottom_z)
        pocket_width = budget.clamp_width + 2.0 * slide.bearing_clamp.seat_fit
        pocket_length = slide.bearing_clamp.foot_length + 2.0 * slide.bearing_clamp.seat_fit
        seat_height = pocket_depth + slide.bearing_clamp.seat_floor

        clamp_width = budget.clamp_width
        clamp_body_width = budget.clamp_body_width
        rod_clamp_width = slide.rod_clamp.width
        rod_x = budget.rod_x

        # The FPC guard sits on the display's back, in the display's own frame:
        # the budget's planform is display-local, and the plate's underside is
        # what the moving head has to clear.
        display_x = (display_p.box[0] + display_p.box[2]) / 2.0
        display_y = (display_p.box[1] + display_p.box[3]) / 2.0
        display_z0 = display_p.z_bounds()[0]
        if abs(display_z0 - (panel_inner_z + budget.display_cavity)) > 1e-6:
            raise ValueError(
                "the display placement disagrees with the derived cavity "
                f"({display_z0 - panel_inner_z:.3f} vs "
                f"{budget.display_cavity:.3f} mm)"
            )
        guard = slide.fpc_guard
        gx0, gy0, gx1, gy1 = budget.guard_planform
        guard_planform = (
            display_x + gx0,
            display_y + gy0,
            display_x + gx1,
            display_y + gy1,
        )
        flex = config.display.flex
        guard_channel_width = (
            flex.width + 2.0 * clearance if flex is not None else 0.0
        )
        guard_slot_depth = guard.floor - config.material.minimum_feature
        if guard_slot_depth <= 0.0:
            raise ValueError(
                "the FPC guard's grille floor is thinner than the printable "
                f"minimum feature (floor {guard.floor:.2f} <= "
                f"{config.material.minimum_feature:.2f} mm)"
            )

        return cls(
            width=budget.width,
            depth=budget.chassis_height,
            lid_draft_angle=lid_draft_angle,
            lid_taper_angle=lid_taper_angle,
            chassis_base_width=chassis_base_width,
            lid_face_width=lid_face_width,
            lid_face_height=lid_face_height,
            chassis_top=chassis_top,
            parting_z=parting_z,
            chassis_band_z0=chassis_band_z0,
            chassis_band_z1=chassis_band_z1,
            chassis_band_width=chassis_band_width,
            chassis_joint=chassis_joint,
            base_taper=budget.base_taper,
            lid_height=budget.lid_height,
            lid_bottom=lid_bottom,
            lid_thickness=lid_thickness,
            lid_back=slide.lid_back,
            lid_front=slide.lid_front,
            panel_outer_z=panel_outer_z,
            panel_inner_z=panel_inner_z,
            lid_top=lid_top,
            band_z0=band_z0,
            band_z1=band_z1,
            lid_joint=joint,
            bezel_recess=config.bezel.recess,
            seam_pin_planes=_seam_pin_planes(config, budget, lid_top, panel_inner_z),
            front=front,
            lid_y_center=front + budget.lid_height / 2.0,
            wall=wall,
            clearance=clearance,
            side_pod=budget.side_pod,
            usable_half=budget.usable_half,
            well=budget.well,
            well_front_margin=budget.well_front_margin,
            plate_frame=budget.well.plate_frame(keyboard_p),
            plate_z=budget.well.plate_bottom,
            plate_top_z=budget.well.plate_top,
            clamp_width=clamp_width,
            clamp_body_width=clamp_body_width,
            rod_x=rod_x,
            rod_y=rod_y,
            rod_z=rod_z,
            rod_raise=rod_raise,
            rod_length=rod_length,
            rod_clamp_len=rod_clamp_len,
            rod_clamp_width=rod_clamp_width,
            rod_clamp_height=slide.rod_clamp.height,
            rod_clamp_screw_span=slide.rod_clamp.screw_span,
            rod_clamp_y=rod_clamp_y,
            rod_groove_width=slide.rod.diameter + 0.4,
            rod_groove_depth=slide.rod.diameter / 2.0 - rod_raise + 0.1,
            bearing_outer=slide.bearing.outer_diameter,
            bearing_bore=slide.bearing.bore,
            bearing_length=slide.bearing.length,
            clamp_center_y=clamp_center_y,
            clamp_len=slide.bearing_clamp.length,
            slot_width=clamp_width + 2.0 * slide.slot_clearance,
            slot_y0=slot_y0,
            slot_y1=slot_y1,
            slot_len=slot_y1 - slot_y0,
            foot_length=slide.bearing_clamp.foot_length,
            foot_thickness=foot_thickness,
            foot_top=foot_top_z - panel_inner_z,
            foot_top_z=foot_top_z,
            foot_bottom_z=foot_bottom_z,
            seat_width=pocket_width + 2.0 * slide.bearing_clamp.seat_wall,
            seat_length=pocket_length + 2.0 * slide.bearing_clamp.seat_wall,
            seat_height=seat_height,
            seat_bottom=chassis_top - seat_height,
            pocket_width=pocket_width,
            pocket_length=pocket_length,
            pocket_depth=pocket_depth,
            keyboard_x=(keyboard_p.box[0] + keyboard_p.box[2]) / 2.0,
            keyboard_y=(keyboard_p.box[1] + keyboard_p.box[3]) / 2.0,
            keyboard_w=keyboard.size().width,
            keyboard_d=keyboard.size().depth,
            display_x=display_x,
            display_y=display_y,
            display_w=display.size().width,
            display_d=display.size().depth,
            display_z0=display_z0,
            head_crown=budget.head_crown,
            fpc_guard=guard,
            guard_planform=guard_planform,
            guard_channel_width=guard_channel_width,
            guard_slot_depth=guard_slot_depth,
            guard_slot_pitch=guard.grille_slot + 2.0 * config.material.minimum_feature,
        )


__all__ = ["SliderFrame"]
