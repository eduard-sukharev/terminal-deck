"""Slider-specific validation (issue #3).

These checks consume the pure-data slide budget and the resolved placements.
They do not build geometry: the CAD sweep of the shell, the connector cutouts
and the drag-chain channel are checked by the case build once it exists (see
``docs/form_factor.md``).
"""

from __future__ import annotations

from typing import Any

from utilities.validation import ValidationReport

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

    # The SBC and hub live in the rear band: inside the chassis rear wall and
    # between the Bearing clamps. There are no clamp placements in the data
    # layer, so the clamp corridor comes from the budget.
    rear_band_names = ("orange pi zero 2w", "usb hub")
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
            "SBC/hub stay inside the rear band",
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
        "slide-guide-span",
        budget.rod_usable >= budget.travel + budget.bearing_per_rod * budget.bearing_length
        + (budget.bearing_per_rod - 1) * slide.clamp_wall,
        f"rod usable {budget.rod_usable:.2f} >= bearing reach "
        f"{budget.travel + budget.bearing_per_rod * budget.bearing_length:.2f}",
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
    report.add(
        "slide-no-slope",
        all(getattr(p, "tilt_x", 0.0) == 0.0 for p in placements),
        "the slider has no keyboard slope: no placement is tilted",
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

    report.goals["closed-face-height"] = budget.closed_face_height
    report.goals["open-face-height"] = budget.open_face_height
    report.goals["thickness"] = budget.thickness
    report.goals["width"] = budget.width
    return report


__all__ = ["BUILD_VOLUME", "MIN_LID_CLEARANCE", "SWEEP_SAMPLES", "run_slider_checks"]
