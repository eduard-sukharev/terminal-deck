"""Slider-specific validation (issue #3).

These checks consume the pure-data slide budget and the resolved placements.
They do not build geometry: the CAD sweep of the shell, the connector cutouts
and the drag-chain channel are checked by the case build once it exists (see
``docs/form_factor.md``).
"""

from __future__ import annotations

from typing import Any

from utilities.validation import ValidationReport
from utilities import fasteners

#: The lid's flat back must clear the keycaps by at least this much (mm).
MIN_LID_CLEARANCE = 1.0

#: Target printer build volume (X x Y x Z, mm).
BUILD_VOLUME = (220.0, 220.0, 256.0)

#: How many positions the slide sweep samples between closed and open.
SWEEP_SAMPLES = 8


def _is_lid(placement: Any) -> bool:
    name = placement.component.name.lower()
    return "display" in name or "driver" in name


def _aabb(placement: Any, shift_y: float = 0.0) -> tuple[float, ...]:
    x0, y0, x1, y1 = placement.box
    z0, z1 = placement.z_bounds()
    return (x0, y0 + shift_y, x1, y1 + shift_y, z0, z1)


def _overlap(a: tuple[float, ...], b: tuple[float, ...]) -> bool:
    return (
        a[0] < b[2] and b[0] < a[2]
        and a[1] < b[3] and b[1] < a[3]
        and a[4] < b[5] and b[4] < a[5]
    )


def _rect_gap(a: tuple[float, ...], b: tuple[float, ...]) -> float:
    """Clear distance between two axis-aligned XY rectangles (0 if touching)."""
    dx = max(a[0] - b[2], b[0] - a[2], 0.0)
    dy = max(a[1] - b[3], b[1] - a[3], 0.0)
    return (dx * dx + dy * dy) ** 0.5


def _by_role(placements: list[Any], role_fragment: str) -> Any | None:
    return next(
        (p for p in placements if role_fragment in p.component.name.lower()),
        None,
    )


def run_slider_checks(
    budget: Any,
    config: Any,
    placements: list[Any],
) -> ValidationReport:
    """Run the slider's HARD checks and report its GOAL metrics.

    The face-height budget is a derivation, but it is still asserted: a config
    or component change that breaks a relationship must fail the build rather
    than silently produce a larger device. The remaining checks are derived
    from the resolved placements (the lid's open edge, the keycap gap, the
    clamp corridor, the sweep) so they can catch a layout regression that the
    budget alone would not see.
    """
    report = ValidationReport()
    slide = config.slide
    keyboard = _by_role(placements, "keyboard")
    display = _by_role(placements, "display")
    device_front = (
        keyboard.box[1] - slide.well_front_margin if keyboard is not None else 0.0
    )

    report.add(
        "slide-budget",
        budget.within_face_limit,
        f"closed face {budget.closed_face_height:.2f} <= "
        f"{budget.face_height_limit:.1f} mm",
    )
    if keyboard is not None:
        open_bottom = device_front + budget.travel
        report.add(
            "slide-travel",
            open_bottom >= keyboard.box[3] + slide.travel_clearance - 1e-6,
            f"open lid edge {open_bottom:.2f} >= keyboard top "
            f"{keyboard.box[3]:.2f} + clearance {slide.travel_clearance:.1f}",
        )
    else:
        report.add("slide-travel", False, "keyboard is not placed")

    # The SBC lives in the rear band: inside the chassis rear wall and between
    # the Bearing clamps. There are no clamp placements in the data layer, so
    # the clamp corridor comes from the budget.
    rear_band_names = ("orange pi zero 2w",)
    rear_band_parts = [
        p for p in placements if p.component.name.lower() in rear_band_names
    ]
    if keyboard is not None and rear_band_parts:
        report.add(
            "slide-rear-band-fit",
            max(
                p.box[3]
                - (device_front + budget.chassis_height - config.wall_thickness)
                for p in rear_band_parts
            )
            <= 1e-6,
            "SBC stays inside the rear band",
        )
        extent = max(max(abs(p.box[0]), abs(p.box[2])) for p in rear_band_parts)
        report.add(
            "slide-clamp-clear",
            extent <= budget.usable_half + 1e-6,
            f"rear-band extent {extent:.2f} <= clamp corridor "
            f"{budget.usable_half:.2f}",
        )
    else:
        report.add("slide-rear-band-fit", False, "no rear-band components")
        report.add("slide-clamp-clear", False, "no rear-band components")

    if keyboard is not None:
        report.add(
            "slide-closed-cover",
            budget.lid_height >= budget.chassis_height,
            f"lid {budget.lid_height:.2f} >= chassis {budget.chassis_height:.2f}",
        )
        if display is not None:
            report.add(
                "slide-display-fit",
                display.box[3] - device_front
                <= budget.lid_height - slide.top_bezel + 1e-6,
                f"display top {display.box[3] - device_front:.2f} <= lid "
                f"{budget.lid_height - slide.top_bezel:.2f}",
            )
    else:
        report.add("slide-closed-cover", False, "keyboard is not placed")

    report.add(
        "slide-closed-flush",
        budget.face_flush,
        f"lid and chassis share the closed face {budget.lid_height:.2f} mm",
    )

    # The display only has to clear the *moving* guide part: the bearing-clamp
    # head, which is as wide as the back-panel slot it travels in. The fixed
    # Rod clamps sit outboard in X but are Y-separated from the display.
    if display is not None:
        display_rect = (
            display.box[0],
            display.box[1],
            display.box[2],
            display.box[3],
        )
        display_half = max(abs(display_rect[0]), abs(display_rect[2]))
        head_inner = budget.rod_x - budget.hardware_width / 2.0
        report.add(
            "slide-display-guide-clear",
            head_inner - display_half >= slide.component_gap - 1e-6,
            f"display half {display_half:.2f} + gap {slide.component_gap:.2f} "
            f"<= moving head inner edge {head_inner:.2f}",
        )
        clamp_clear = min(
            _rect_gap(
                display_rect,
                (
                    budget.rod_x - budget.rod_clamp_width / 2.0,
                    center_y - budget.rod_clamp_length / 2.0,
                    budget.rod_x + budget.rod_clamp_width / 2.0,
                    center_y + budget.rod_clamp_length / 2.0,
                ),
            )
            for center_y in budget.rod_clamp_y
        )
        report.add(
            "slide-rod-clamp-clear",
            clamp_clear >= slide.component_gap - 1e-6,
            f"display to fixed Rod clamp {clamp_clear:.2f} >= "
            f"{slide.component_gap:.2f}",
        )
    else:
        report.add("slide-display-guide-clear", False, "display is not placed")
        report.add("slide-rod-clamp-clear", False, "display is not placed")

    report.add(
        "slide-guide-span",
        budget.rod_usable >= budget.travel + budget.bearing_per_rod * budget.bearing_length
        + (budget.bearing_per_rod - 1) * slide.clamp_wall,
        f"rod usable {budget.rod_usable:.2f} >= bearing reach "
        f"{budget.travel + budget.bearing_per_rod * budget.bearing_length:.2f}",
    )
    report.add(
        "slide-slot-fits",
        budget.slot_fits,
        f"back-panel slot {budget.slot_span:.2f} >= clamp travel "
        f"{budget.slot_needed:.2f}",
    )
    report.add(
        "slide-retention",
        budget.lid_overlap >= budget.bearing_length,
        f"lid overlap in the open pose {budget.lid_overlap:.2f} >= "
        f"bearing {budget.bearing_length:.1f}",
    )

    if keyboard is not None and display is not None:
        lid_back_bottom = min(
            p.z_bounds()[0] for p in placements if _is_lid(p)
        ) - slide.lid_back
        keycap_top = keyboard.z_bounds()[1]
        gap = lid_back_bottom - keycap_top
        report.add(
            "slide-keycap-clearance",
            gap >= MIN_LID_CLEARANCE - 1e-6,
            f"lid back {lid_back_bottom:.2f} - keycap top {keycap_top:.2f} "
            f"= {gap:.2f} >= {MIN_LID_CLEARANCE:.1f}",
        )
    else:
        report.add("slide-keycap-clearance", False, "keyboard/display not placed")

    # The lid sweeps over the chassis; no lid part may touch a chassis part at
    # any point of the travel (the budget only checks the end poses).
    chassis_parts = [p for p in placements if not _is_lid(p)]
    lid_parts = [p for p in placements if _is_lid(p)]
    swept_clear = True
    culprit = ""
    if chassis_parts and lid_parts:
        for step in range(SWEEP_SAMPLES + 1):
            shift = budget.travel * step / SWEEP_SAMPLES
            for lid_part in lid_parts:
                lid_box = _aabb(lid_part, shift)
                for chassis_part in chassis_parts:
                    if _overlap(lid_box, _aabb(chassis_part)):
                        swept_clear = False
                        culprit = (
                            f"{lid_part.component.name} at {shift:.1f} mm "
                            f"overlaps {chassis_part.component.name}"
                        )
                        break
                if not swept_clear:
                    break
            if not swept_clear:
                break
    else:
        swept_clear = False
        culprit = "keyboard/display not placed"
    report.add(
        "slide-sweep-clear",
        swept_clear,
        culprit or "no lid/chassis collision over the travel",
    )

    report.add(
        "slide-chain-bend",
        budget.chain_bend_ok,
        f"chain bend radius {budget.chain_bend_radius:.1f} >= cable minimum "
        f"{budget.cable_min_bend_radius:.1f}",
    )

    if placements:
        half_width = max(max(abs(p.box[0]), abs(p.box[2])) for p in placements)
        report.add(
            "slide-layout-width",
            half_width <= budget.width / 2.0 + 1e-6,
            f"widest placement half-width {half_width:.2f} <= "
            f"budget {budget.width / 2.0:.2f}",
        )
    else:
        report.add("slide-layout-width", False, "no placements")

    report.add(
        "slide-section-fit",
        budget.width / 2.0 <= BUILD_VOLUME[0]
        and budget.closed_face_height <= BUILD_VOLUME[1]
        and budget.thickness <= BUILD_VOLUME[2],
        f"half width {budget.width / 2.0:.1f} <= {BUILD_VOLUME[0]:.0f}, face "
        f"{budget.closed_face_height:.1f} <= {BUILD_VOLUME[1]:.0f}, thickness "
        f"{budget.thickness:.1f} <= {BUILD_VOLUME[2]:.0f}",
    )
    report.warn(
        "slide-section-rejoins / slide-section-bed-face and the drag-chain "
        "channel are checked by the case build (CAD stage)"
    )

    # -- Bezel <-> Back band joint (ADR-0011) -----------------------------
    joint = budget.lid_joint
    min_feature = config.material.minimum_feature
    report.add(
        "slide-lid-joint-band",
        joint.band >= joint.insert_depth + min_feature - 1e-6,
        f"band {joint.band:.2f} >= insert {joint.insert_depth:.2f} + "
        f"min feature {min_feature:.2f}",
    )
    report.add(
        "slide-lid-joint-post",
        joint.corner_post_width >= joint.insert_hole + 2.0 * joint.boss_margin - 1e-6,
        f"corner post {joint.corner_post_width:.2f} >= insert hole "
        f"{joint.insert_hole:.2f} + 2 x margin {joint.boss_margin:.2f}",
    )
    report.add(
        "slide-lid-joint-screw",
        joint.screw.engagement >= float(joint.screw.size.lstrip("M")) - 1e-6,
        f"{joint.screw.name} engages {joint.screw.engagement:.2f} mm of the "
        f"{joint.insert_depth:.2f} mm insert (grip {joint.grip:.2f})",
    )
    report.add(
        "slide-lid-joint-recess",
        config.bezel.recess <= slide.lid_front - min_feature + 1e-6,
        f"bezel recess {config.bezel.recess:.2f} <= front panel "
        f"{slide.lid_front:.2f} - min feature {min_feature:.2f}",
    )
    clamp_rects = []
    for center_y in budget.rod_clamp_y:
        half = budget.rod_clamp_length / 2.0
        clamp_rects.append(
            (
                budget.rod_x - budget.rod_clamp_width / 2.0,
                center_y - half,
                budget.rod_x + budget.rod_clamp_width / 2.0,
                center_y + half,
            )
        )
    post_rect = (
        joint.post_x[0],
        budget.lid_height / 2.0 - joint.corner_length,
        joint.post_x[1],
        budget.lid_height / 2.0,
    )
    tightest = float("inf")
    for station in joint.stations:
        if station.is_corner:
            rect = (
                post_rect[0],
                post_rect[1],
                post_rect[2],
                post_rect[3],
            ) if station.y > 0.0 else (
                post_rect[0], -post_rect[3], post_rect[2], -post_rect[1]
            )
        else:
            half = joint.boss / 2.0
            rect = (
                station.x - half, station.y - half,
                station.x + half, station.y + half,
            )
        for clamp in clamp_rects:
            tightest = min(tightest, _rect_gap(rect, clamp))
    report.add(
        "slide-lid-joint-station-clear",
        tightest >= joint.corner_clearance - 1e-6,
        f"closest band station to a Rod clamp {tightest:.2f} >= "
        f"{joint.corner_clearance:.2f}",
    )

    # -- Tray <-> Deck band joint (ADR-0012) -----------------------------
    cj = budget.chassis_joint
    report.add(
        "slide-chassis-joint-band",
        cj.band >= cj.insert_depth + min_feature - 1e-6,
        f"band {cj.band:.2f} >= insert {cj.insert_depth:.2f} + "
        f"min feature {min_feature:.2f}",
    )
    report.add(
        "slide-chassis-joint-boss-height",
        cj.boss_height >= cj.insert_depth + min_feature - 1e-6,
        f"insert boss {cj.boss_height:.2f} >= insert {cj.insert_depth:.2f} + "
        f"min feature {min_feature:.2f}",
    )
    report.add(
        "slide-chassis-joint-screw",
        cj.screw.engagement >= float(cj.screw.size.lstrip("M")) - 1e-6,
        f"{cj.screw.name} engages {cj.screw.engagement:.2f} mm of the "
        f"{cj.insert_depth:.2f} mm insert (grip {cj.grip:.2f})",
    )
    report.add(
        "slide-chassis-joint-boss",
        cj.smallest_boss() >= cj.insert_hole + 2.0 * cj.boss_margin - 1e-6,
        f"tightest insert boss {cj.smallest_boss():.2f} >= insert hole "
        f"{cj.insert_hole:.2f} + 2 x margin {cj.boss_margin:.2f}",
    )
    screw_clearance = fasteners.screw(cj.screw.size).clearance
    report.add(
        "slide-chassis-joint-column",
        cj.smallest_base_boss() >= screw_clearance + 2.0 * min_feature - 1e-6,
        f"tightest Tray column {cj.smallest_base_boss():.2f} >= screw "
        f"clearance {screw_clearance:.2f} + 2 x min feature {min_feature:.2f}",
    )
    floor_margin = min(
        station.base_distance - cj.countersink.diameter / 2.0
        for station in cj.stations
    )
    report.add(
        "slide-chassis-joint-floor",
        floor_margin >= min_feature - 1e-6,
        f"countersink to outer skin {floor_margin:.2f} >= min feature "
        f"{min_feature:.2f}",
    )
    scallop_margin = min(
        station.surface - cj.scallop_depth - cj.insert_hole / 2.0
        for station in cj.stations
    )
    report.add(
        "slide-chassis-joint-scallop",
        scallop_margin >= cj.boss_margin - 1e-6,
        f"scallop floor to insert {scallop_margin:.2f} >= boss margin "
        f"{cj.boss_margin:.2f}",
    )
    report.add(
        "slide-chassis-joint-parting",
        cj.parting_z >= cj.countersink.depth + min_feature - 1e-6
        and cj.band_z1 <= cj.chassis_top - config.wall_thickness + 1e-6,
        f"Parting plane {cj.parting_z:.2f}, band {cj.parting_z:.2f}-"
        f"{cj.band_z1:.2f} inside the chassis top {cj.chassis_top:.2f}",
    )
    # No station may grow into a placed component below the band's top.
    joint_z1 = cj.band_z1
    tightest_clear = float("inf")
    culprit = ""
    for station in cj.stations:
        radius = max(station.boss, station.base_boss) / 2.0
        rect = (
            station.x - radius,
            station.y - radius,
            station.x + radius,
            station.y + radius,
        )
        for placement in placements:
            z0, z1 = placement.z_bounds()
            if z1 <= 0.0 or z0 >= joint_z1:
                continue
            gap = _rect_gap(rect, placement.box)
            if gap < tightest_clear:
                tightest_clear = gap
                culprit = placement.component.name
    report.add(
        "slide-chassis-joint-clear",
        tightest_clear > 0.0,
        f"closest joint station to {culprit or 'no component'}: "
        f"{tightest_clear:.2f} mm",
    )

    report.goals["closed-face-height"] = budget.closed_face_height
    report.goals["open-face-height"] = budget.open_face_height
    report.goals["thickness"] = budget.thickness
    report.goals["width"] = budget.width
    return report


__all__ = ["BUILD_VOLUME", "MIN_LID_CLEARANCE", "SWEEP_SAMPLES", "run_slider_checks"]
