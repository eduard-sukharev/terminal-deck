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

#: Tolerance for "surfaces touch but do not overlap" (mm).
_EPS = 1e-9


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


def _circle_rect_gap(
    cx: float, cy: float, radius: float, rect: tuple[float, ...]
) -> float:
    """Radial clearance between a circular column and an XY rectangle (mm).

    The band joint's Tray columns and Deck bosses are round, so their real
    footprint is the disc -- not its bounding square. A negative result means
    the disc reaches into the material. Zero means it touches.
    """
    dx = max(rect[0] - cx, 0.0, cx - rect[2])
    dy = max(rect[1] - cy, 0.0, cy - rect[3])
    return (dx * dx + dy * dy) ** 0.5 - radius


def _by_role(placements: list[Any], role_fragment: str) -> Any | None:
    return next(
        (p for p in placements if role_fragment in p.component.name.lower()),
        None,
    )


# -- the plate's real plan footprint ------------------------------------


def _subtract_rect(
    rects: list[tuple[float, float, float, float]],
    hole: tuple[float, float, float, float],
) -> list[tuple[float, float, float, float]]:
    """Remove an axis-aligned ``hole`` from a list of rectangles (plan, mm).

    The leftover is split into at most four rectangles (above, below, left and
    right of the hole), which is exact for an axis-aligned cut-out: the union
    of the returned rectangles is the material that was there before.
    """
    hx0, hy0, hx1, hy1 = hole
    out: list[tuple[float, float, float, float]] = []
    for x0, y0, x1, y1 in rects:
        ix0, iy0 = max(x0, hx0), max(y0, hy0)
        ix1, iy1 = min(x1, hx1), min(y1, hy1)
        if ix0 >= ix1 - _EPS or iy0 >= iy1 - _EPS:
            out.append((x0, y0, x1, y1))
            continue
        if iy0 > y0 + _EPS:
            out.append((x0, y0, x1, iy0))
        if iy1 < y1 - _EPS:
            out.append((x0, iy1, x1, y1))
        if ix0 > x0 + _EPS:
            out.append((x0, iy0, ix0, iy1))
        if ix1 < x1 - _EPS:
            out.append((ix1, iy0, x1, iy1))
    return out


def _footprint_material(
    placement: Any,
) -> list[tuple[float, float, float, float]] | None:
    """A placement's plan material as rectangles, or ``None`` for its bbox.

    A component that knows its real (notched or eared) plan footprint exposes
    ``footprint_cutouts()`` -- the plate-local rectangles the chassis forces it
    to give up (ADR-0014). Subtracting them from the placement's bounding
    rectangle is the real sheet: a band station may sit in a notch, while the
    bounding box can never say so.

    ``None`` means no footprint is available (an empty pattern counts: before
    the Well-mount pattern is injected the plate *will* be notched), so the
    caller falls back to the bounding box and warns.
    """
    getter = getattr(placement.component, "footprint_cutouts", None)
    if getter is None:
        return None
    try:
        cutouts = list(getter())
    except (ValueError, AttributeError):
        # A component with a broken footprint must not crash the report; the
        # caller falls back to the conservative bbox and says so.
        return None
    if not cutouts:
        return None

    from geometry.well_mounts import PlanRect, PlateFrame

    size = placement.component.size()
    try:
        frame = PlateFrame.from_placement(
            placement, width=size.width, depth=size.depth
        )
    except ValueError:
        # A frame the plan cannot express (a non-axis-aligned turn) is not a
        # licence to guess: fall back to the conservative bbox.
        return None
    material = [placement.box]
    for cutout in cutouts:
        world = frame.local_rect_to_world(PlanRect(*cutout))
        material = _subtract_rect(
            material, (world.x0, world.y0, world.x1, world.y1)
        )
    return material


# -- ADR-0014: the Well, the plate and its eight mounts ------------------


def _add_well_checks(report: ValidationReport, config: Any, budget: Any) -> None:
    """HARD: the Well reaches the plate and is sized by the keycaps.

    ``parting_z <= plate_bottom`` is the ADR's serviceability rule: the Tray /
    Deck Parting plane never cuts the Well. The Cutout is the keycap footprint
    plus ``wobble`` per side -- never the plate, and never
    ``clearance.shell`` -- and the ring is one wall thick on both axes (a ring
    has one value per axis, reported as such, not four independent sides).
    """
    well = budget.well
    joint = budget.chassis_joint
    wall = float(config.wall.thickness)

    report.add(
        "keyboard-well-parting",
        joint.parting_z <= well.plate_bottom + _EPS,
        f"Parting plane {joint.parting_z:.2f} <= plate bottom "
        f"{well.plate_bottom:.2f} (plate top {well.plate_top:.2f}, Well depth "
        f"{well.well_depth:.2f})",
    )

    # The Well is a ring around a rectangular Cutout, so its border has two
    # values, one per axis -- the per-side names are just their two ends.
    inset_x = (well.plate_width - well.cutout_width) / 2.0
    inset_y = (well.plate_depth - well.cutout_depth) / 2.0
    report.add(
        "keyboard-well-ring",
        well.ring >= wall - _EPS and min(inset_x, inset_y) >= well.ring - _EPS,
        f"Well ring {well.ring:.2f} >= wall.thickness {wall:.2f}; border in "
        f"the plate X {inset_x:.2f} / Y {inset_y:.2f} (plate "
        f"{well.plate_width:.2f} x {well.plate_depth:.2f} around a Cutout "
        f"{well.cutout_width:.2f} x {well.cutout_depth:.2f})",
    )

    cutout_w = well.keycap_width + 2.0 * well.wobble
    cutout_d = well.keycap_depth + 2.0 * well.wobble
    report.add(
        "keyboard-well-cutout",
        abs(well.cutout_width - cutout_w) <= 1e-6
        and abs(well.cutout_depth - cutout_d) <= 1e-6,
        f"Cutout {well.cutout_width:.2f} x {well.cutout_depth:.2f} = keycap "
        f"{well.keycap_width:.2f} x {well.keycap_depth:.2f} + 2 x wobble "
        f"{well.wobble:.2f} = {cutout_w:.2f} x {cutout_d:.2f}",
    )


def _add_plate_checks(
    report: ValidationReport,
    config: Any,
    budget: Any,
    model: Any | None,
) -> None:
    """HARD: the generated plate carries the Well's bearing border.

    Measured on the plate model the keyboard actually generates (not the
    budget): its border is at least one wall on every side, no switch or
    stabilizer cutout enters it, the Seam crosses no cutout, and each Section
    fits the printer.
    """
    names = (
        "keyboard-plate-overhang",
        "keyboard-plate-border",
        "keyboard-plate-seam",
        "keyboard-plate-sections",
    )
    if model is None:
        for name in names:
            report.add(name, False, "the keyboard plate model is unavailable")
        return
    wall = float(config.wall.thickness)
    meta = model.metadata
    cutout = meta.cutout
    half_w, half_d = meta.width / 2.0, meta.height / 2.0
    overhang = {
        "left": cutout[0] + half_w,
        "right": half_w - cutout[2],
        # Plate-local +Y is the keyboard's front (the spacebar row).
        "front": half_d - cutout[3],
        "rear": cutout[1] + half_d,
    }
    report.add(
        "keyboard-plate-overhang",
        min(overhang.values()) >= wall - _EPS,
        f"plate {meta.width:.2f} x {meta.height:.2f} over the Cutout "
        f"{cutout[2] - cutout[0]:.2f} x {cutout[3] - cutout[1]:.2f}: "
        f"left/right/front/rear {overhang['left']:.2f}/"
        f"{overhang['right']:.2f}/{overhang['front']:.2f}/"
        f"{overhang['rear']:.2f} >= wall {wall:.2f}",
    )

    margins = meta.edge_margins
    report.add(
        "keyboard-plate-border",
        min(margins) >= wall - _EPS,
        f"switch-free border left/right/front(spacebar)/rear {margins[0]:.2f}/"
        f"{margins[1]:.2f}/{margins[3]:.2f}/{margins[2]:.2f} >= wall "
        f"{wall:.2f} (no switch or stabilizer cutout in the bearing border)",
    )

    seam = getattr(model, "seam", None)
    if seam is None:
        report.add(
            "keyboard-plate-seam",
            False,
            "the keyboard plate model has no Seam",
        )
    else:
        from keyboard.geometry.seam import seam_conflicts

        conflicts = seam_conflicts(model, seam)
        bands = getattr(seam, "bands", ())
        xs = [x for _, _, x in bands] or [0.0]
        report.add(
            "keyboard-plate-seam",
            not conflicts,
            f"Seam ({len(bands)} bands, plate x {min(xs):.2f}..{max(xs):.2f}) "
            "crosses no switch or stabilizer cutout"
            + (": " + "; ".join(conflicts) if conflicts else ""),
        )

    sections = getattr(model, "section_outlines", None)
    if not sections or len(sections) != 2:
        report.add(
            "keyboard-plate-sections",
            False,
            f"the plate model has {0 if not sections else len(sections)} "
            "Section outlines, the Seam must split it into two",
        )
    else:
        extents = []
        fit = True
        for points in sections:
            xs = [p[0] for p in points]
            ys = [p[1] for p in points]
            width = max(xs) - min(xs)
            depth = max(ys) - min(ys)
            thickness = meta.plate_thickness
            extents.append((width, depth, thickness))
            if (
                width > BUILD_VOLUME[0] + 1e-6
                or depth > BUILD_VOLUME[1] + 1e-6
                or thickness > BUILD_VOLUME[2] + 1e-6
            ):
                fit = False
        report.add(
            "keyboard-plate-sections",
            fit,
            "plate Sections "
            + ", ".join(
                f"{side} {w:.2f} x {d:.2f} x {t:.2f}"
                for side, (w, d, t) in zip(("left", "right"), extents)
            )
            + f" <= {BUILD_VOLUME[0]:.0f} x {BUILD_VOLUME[1]:.0f} x "
            f"{BUILD_VOLUME[2]:.0f}",
        )


def _tray_cavity_half(config: Any, budget: Any, z: float) -> tuple[float, float]:
    """The Tray's inner half-width and half-depth at height ``z`` (mm).

    The Tray is drafted below ``band_z0`` and prismatic above it; the front and
    rear end walls stay vertical. The narrowest cavity over a feature's Z span
    is therefore at the span's lowest height.
    """
    from utilities.cad_helpers import draft_inset

    joint = budget.chassis_joint
    wall = config.wall_thickness
    if z >= joint.band_z0:
        outer = budget.width
    else:
        outer = joint.base_width + 2.0 * draft_inset(config.draft.angle, z)
    return outer / 2.0 - wall, budget.chassis_height / 2.0 - wall


def _head_verdict(
    mounts: Any,
    config: Any,
    budget: Any,
    keyboard: Any | None,
    placements: list[Any],
) -> tuple[bool, str]:
    """HARD: the plate-screw heads may dip into the Tray, but land clear.

    A 1.5 mm plate cannot recess an M2 head (Ø3.80 × 2.00): the head sits on the
    plate's underside and crosses the Parting plane by the difference. That is
    unavoidable and accepted (ADR-0014), so it is *measured*: every head's plan
    disc must stay inside the Tray's inner walls at its lowest Z and clear every
    placed part below the plane. The keyboard itself is excluded -- these are
    the screws of its own plate.
    """
    joint = budget.chassis_joint
    parting = joint.parting_z
    radius = mounts.head_diameter / 2.0
    head_z0 = mounts.plate_bottom - mounts.head_depth
    crossing = parting - head_z0 if head_z0 < parting else 0.0
    if crossing <= 0.0:
        return True, (
            f"{len(mounts.mounts)} x Ø{mounts.head_diameter:.2f} head ("
            f"{mounts.head_depth:.2f} deep) sit above the Parting plane "
            f"{parting:.2f} (plate bottom {mounts.plate_bottom:.2f})"
        )

    inside = min(head_z0, parting)
    half_x, half_y = _tray_cavity_half(config, budget, max(inside, 0.0))
    wall_gap = min(
        min(
            half_x - abs(mount.x) - radius,
            half_y - abs(mount.y) - radius,
        )
        for mount in mounts.mounts
    )
    worst = wall_gap
    culprit = "the Tray walls"
    for mount in mounts.mounts:
        for placement in placements:
            if keyboard is not None and placement.component is keyboard:
                continue
            z0, z1 = placement.z_bounds()
            if z1 <= head_z0 + _EPS or z0 >= inside - _EPS:
                continue
            gap = _circle_rect_gap(mount.x, mount.y, radius, placement.box)
            if gap < worst:
                worst, culprit = gap, placement.component.name
    return worst > _EPS, (
        f"{len(mounts.mounts)} x Ø{mounts.head_diameter:.2f} head ("
        f"{mounts.head_depth:.2f} deep) sit on plate bottom "
        f"{mounts.plate_bottom:.2f} -> {head_z0:.2f}: they cross the Parting "
        f"plane {parting:.2f} by {crossing:.2f} mm; closest to {culprit} "
        f"{worst:.2f} mm (Tray cavity {2.0 * half_x:.2f} x "
        f"{2.0 * half_y:.2f})"
    )


def _add_mount_checks(
    report: ValidationReport,
    config: Any,
    budget: Any,
    mounts: Any | None,
    *,
    keyboard: Any | None = None,
    placements: list[Any] = (),
) -> None:
    """HARD: eight M2 stations, four per Section, clear of everything.

    The pattern itself is derived by :func:`geometry.well_mounts.well_mounts`
    (one source for the Deck's bosses and the plate's ears/notches). These
    checks surface its verdict, the derived stock screw and the Parting-plane
    rule: no printed plate fastener column crosses the plane, and the screw
    heads that do dip into the Tray are measured against it.
    """
    names = (
        "keyboard-mounts-stations",
        "keyboard-mounts-fit",
        "keyboard-mounts-screw",
        "keyboard-mounts-head",
        "keyboard-mounts-parting",
    )
    if mounts is None:
        for name in names:
            report.add(name, False, "the Well-mount pattern is unavailable")
        return

    from geometry.well_mounts import STATIONS

    counts = mounts.section_counts
    per_station = {
        station: [m for m in mounts.mounts if m.station == station]
        for station in STATIONS
    }
    stations_ok = (
        len(mounts.mounts) == 2 * len(STATIONS)
        and all(counts.get(side, 0) == len(STATIONS) for side in ("left", "right"))
        and all(len(members) == 2 for members in per_station.values())
    )
    report.add(
        "keyboard-mounts-stations",
        stations_ok,
        f"{len(mounts.mounts)} stations: left {counts.get('left', 0)}, right "
        f"{counts.get('right', 0)}; "
        + ", ".join(
            f"{station} x{len(members)}"
            for station, members in per_station.items()
        ),
    )

    report.add(
        "keyboard-mounts-fit",
        mounts.ok,
        f"{len(mounts.mounts)} x {mounts.screw_name} bosses "
        f"Ø{mounts.boss_diameter:.2f} (insert Ø"
        f"{mounts.insert_hole_diameter:.2f} x {mounts.insert_depth:.2f} deep, "
        f"clearance Ø{mounts.clearance_hole_diameter:.2f}); lip "
        f"{mounts.front_lip:.2f}/{mounts.rear_lip:.2f} needs "
        f"{mounts.lip_required:.2f}; Seam clearance "
        f"{mounts.seam_clearance:.2f}"
        + (
            "; " + "; ".join(mounts.failures)
            if not mounts.ok
            else ""
        ),
    )

    # The screw is a stock length derived from the grip (the plate thickness)
    # and the insert depth, exactly like the chassis joints: it must reach one
    # thread diameter into the insert without bottoming out.
    nominal = float(mounts.screw.lstrip("M"))
    report.add(
        "keyboard-mounts-screw",
        nominal <= mounts.screw_engagement <= mounts.insert_depth + _EPS,
        f"{mounts.screw_name} engages {mounts.screw_engagement:.2f} mm of the "
        f"{mounts.insert_depth:.2f} mm insert across the {mounts.screw_grip:.2f} "
        f"mm plate (grip); needs {nominal:.1f} <= engagement <= "
        f"{mounts.insert_depth:.2f}",
    )

    report.add(
        "keyboard-mounts-head",
        *_head_verdict(mounts, config, budget, keyboard, placements),
    )

    joint = budget.chassis_joint
    bases = [m.boss_z0 for m in mounts.mounts]
    standoffs = len(keyboard.mounting_holes()) if keyboard is not None else 0
    report.add(
        "keyboard-mounts-parting",
        bool(bases)
        and min(bases) > joint.parting_z + _EPS
        and standoffs == 0,
        f"lowest plate boss base {min(bases) if bases else float('nan'):.2f} > "
        f"Parting plane {joint.parting_z:.2f} (plate bottom "
        f"{budget.well.plate_bottom:.2f}); {standoffs} floor standoffs -- no "
        "printed plate fastener column crosses the plane (only the screw "
        "heads dip into the Tray, checked by keyboard-mounts-head)",
    )


def run_slider_checks(
    budget: Any,
    config: Any,
    placements: list[Any],
    *,
    mounts: Any | None = None,
) -> ValidationReport:
    """Run the slider's HARD checks and report its GOAL metrics.

    The face-height budget is a derivation, but it is still asserted: a config
    or component change that breaks a relationship must fail the build rather
    than silently produce a larger device. The remaining checks are derived
    from the resolved placements (the lid's open edge, the keycap gap, the
    clamp corridor, the sweep) so they can catch a layout regression that the
    budget alone would not see.

    ``mounts`` is the Well-mount pattern (``geometry.well_mounts.WellMounts``)
    the pipeline injected into the plate. When omitted it is derived here from
    the keyboard's placement, so a caller that only has the budget still gets
    the ADR-0014 mounts checks.
    """
    report = ValidationReport()
    slide = config.slide
    keyboard = _by_role(placements, "keyboard")
    display = _by_role(placements, "display")
    device_front = (
        keyboard.box[1] - budget.well_front_margin if keyboard is not None else 0.0
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
        # The corridor is the inboard face of the moving head: the rods are
        # under the display now, so a rear-band part would hit the head long
        # before it reached the shell wall.
        corridor = budget.rod_x - budget.hardware_width / 2.0
        report.add(
            "slide-clamp-clear",
            extent <= corridor + 1e-6,
            f"rear-band extent {extent:.2f} <= clamp corridor "
            f"{corridor:.2f} (rod {budget.rod_x:.2f} - head half "
            f"{budget.hardware_width / 2.0:.2f})",
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

    # The moving head passes *under* the display now, so the clearance is a Z
    # stack: the head's crown, the component gap, the sag allowance and the FPC
    # guard plate all sit between the back panel and the display's back. The
    # guard is bonded to the display, so its underside is the surface the head
    # must never reach.
    if display is not None and keyboard is not None:
        display_z0 = display.z_bounds()[0]
        guard_underside = display_z0 - budget.fpc_guard.total
        panel_inner = keyboard.z_bounds()[1] + slide.lid_clearance + slide.lid_back
        crown = panel_inner + budget.head_crown
        required = crown + slide.component_gap + budget.fpc_guard.sag_allowance
        report.add(
            "slide-display-guide-clear",
            guard_underside - required >= -1e-6,
            f"head crown {crown:.2f} + gap {slide.component_gap:.2f} + sag "
            f"{budget.fpc_guard.sag_allowance:.2f} <= guard underside "
            f"{guard_underside:.2f} (panel inner {panel_inner:.2f})",
        )
        clamp_clear = min(
            _rect_gap(
                (display.box[0], display.box[1], display.box[2], display.box[3]),
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

    # The FPC guard: a floor thick enough to print, a channel that swallows the
    # measured ribbon stack, and a planform that covers everything the moving
    # head can sweep over the ribbon.
    guard = budget.fpc_guard
    flex = config.display.flex
    min_feature = config.material.minimum_feature
    stack_ok = (
        flex is not None
        and guard.recess >= flex.stack - 1e-6
        and guard.floor >= min_feature - 1e-6
    )
    report.add(
        "slide-fpc-guard-stack",
        stack_ok,
        f"guard {guard.total:.2f} = floor {guard.floor:.2f} + channel "
        f"{guard.recess:.2f} (ribbon stack "
        f"{flex.stack if flex is not None else float('nan'):.2f}, min feature "
        f"{min_feature:.2f})",
    )
    if display is not None and flex is not None:
        display_cx = (display.box[0] + display.box[2]) / 2.0
        display_cy = (display.box[1] + display.box[3]) / 2.0
        gx0, gy0, gx1, gy1 = budget.guard_planform
        guard_rect = (display_cx + gx0, display_cy + gy0,
                      display_cx + gx1, display_cy + gy1)
        ribbon_half = flex.width / 2.0
        slot_rect = (
            budget.rod_x - budget.hardware_width / 2.0,
            -1e9,
            budget.rod_x + budget.hardware_width / 2.0,
            1e9,
        )
        ribbon_margin = min(
            (display_cy - ribbon_half) - guard_rect[1],
            guard_rect[3] - (display_cy + ribbon_half),
        )
        slot_margin = min(
            slot_rect[0] - guard_rect[0],
            guard_rect[2] - slot_rect[2],
        )
        inside_x = budget.width / 2.0 - config.wall_thickness
        inside_y = budget.lid_height / 2.0 - config.wall_thickness
        report.add(
            "slide-fpc-guard-cover",
            min(ribbon_margin, slot_margin) >= guard.margin - 1e-6
            and abs(guard_rect[0]) <= inside_x + 1e-6
            and abs(guard_rect[2]) <= inside_x + 1e-6
            and abs(guard_rect[1]) <= inside_y + 1e-6
            and abs(guard_rect[3]) <= inside_y + 1e-6,
            f"guard covers the ribbon (+{ribbon_margin:.2f}) and the slot band "
            f"(+{slot_margin:.2f}) with margin {guard.margin:.2f}, inside the "
            f"lid wall {inside_x:.2f} x {inside_y:.2f}",
        )
    else:
        report.add("slide-fpc-guard-cover", False, "display/ribbon is not placed")

    # The Deck's Bearing-clamp seat moved inboard with the rods; it must not
    # merge with the chassis band's corner boss. The pair is Z-separated (the
    # boss stands in the band, the seat sits on the Deck top), so this is the
    # plan-space guard the two inboard features need.
    seat_half_x = (
        budget.clamp_width / 2.0
        + slide.bearing_clamp.seat_fit
        + slide.bearing_clamp.seat_wall
    )
    seat_half_y = (
        slide.bearing_clamp.foot_length / 2.0
        + slide.bearing_clamp.seat_fit
        + slide.bearing_clamp.seat_wall
    )
    seat_rect = (
        budget.rod_x - seat_half_x,
        budget.clamp_center_y - seat_half_y,
        budget.rod_x + seat_half_x,
        budget.clamp_center_y + seat_half_y,
    )
    closest = float("inf")
    for station in budget.chassis_joint.corner_stations:
        radius = station.boss / 2.0
        boss_rect = (
            station.x - radius,
            station.y - radius,
            station.x + radius,
            station.y + radius,
        )
        closest = min(closest, _rect_gap(seat_rect, boss_rect))
    report.add(
        "slide-chassis-seat-clear",
        closest >= min_feature - 1e-6,
        f"Deck seat to chassis band corner boss {closest:.2f} >= "
        f"{min_feature:.2f} (plan guard; the boss top "
        f"{budget.chassis_joint.parting_z + budget.chassis_joint.boss_height:.2f}"
        f" is below the Deck top {budget.chassis_top:.2f})",
    )

    bounds = budget.rod_x_bounds
    report.add(
        "slide-guide-stance",
        budget.rod_x <= bounds.tightest - slide.rod.side_margin + 1e-6,
        f"rod x {budget.rod_x:.2f} <= tightest bound {bounds.tightest_name} "
        f"{bounds.tightest:.2f} - margin {slide.rod.side_margin:.2f} "
        f"(post {bounds.post:.2f}, seat {bounds.seat:.2f}, head "
        f"{bounds.head:.2f})",
    )
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
        # The lid's back panel is no longer the lowest lid placement (the driver
        # floats under the panel now), so the keycap gap comes from the
        # keyboard plus the configured clearance, and the display's back is
        # checked against the cavity the budget derived from the head + guard.
        keycap_top = keyboard.z_bounds()[1]
        panel_inner = keycap_top + slide.lid_clearance + slide.lid_back
        display_back = display.z_bounds()[0]
        gap = display_back - panel_inner
        report.add(
            "slide-keycap-clearance",
            slide.lid_clearance >= MIN_LID_CLEARANCE - 1e-6
            and abs(gap - budget.display_cavity) <= 1e-6,
            f"lid back {panel_inner - slide.lid_back:.2f} - keycap top "
            f"{keycap_top:.2f} = {slide.lid_clearance:.2f} >= "
            f"{MIN_LID_CLEARANCE:.1f}; display back {display_back:.2f} sits at "
            f"the derived cavity {budget.display_cavity:.2f}",
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
        "slide-lid-joint-post-inboard",
        joint.post_x[1] <= budget.width / 2.0 - config.wall_thickness + 1e-6
        and joint.post_x[0] >= budget.rod_x + budget.rod_clamp_width / 2.0
        + joint.corner_clearance - 1e-6,
        f"corner post {joint.post_x[0]:.2f}..{joint.post_x[1]:.2f} sits between "
        f"the Rod clamp {budget.rod_x + budget.rod_clamp_width / 2.0:.2f} and "
        f"the cavity wall {budget.width / 2.0 - config.wall_thickness:.2f}",
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
    checked = 0
    for station in cj.stations:
        radius = max(station.boss, station.base_boss) / 2.0
        for placement in placements:
            z0, z1 = placement.z_bounds()
            if z1 <= 0.0 or z0 >= joint_z1:
                continue
            checked += 1
            # The real notched footprint when the component can describe it;
            # otherwise its bounding box (conservative, and said out loud).
            material = _footprint_material(placement)
            if material is None:
                material = [placement.box]
                message = (
                    f"{placement.component.name} has no notched plan "
                    "footprint; slide-chassis-joint-clear used its bounding box"
                )
                if message not in report.warnings:
                    report.warn(message)
            gap = min(
                (
                    _circle_rect_gap(station.x, station.y, radius, piece)
                    for piece in material
                ),
                default=0.0,
            )
            if gap < tightest_clear:
                tightest_clear = gap
                culprit = placement.component.name
    report.add(
        "slide-chassis-joint-clear",
        checked > 0 and tightest_clear > 0.0,
        (
            f"closest joint station to {culprit}: {tightest_clear:.2f} mm"
            if checked
            else "no placement survived the Z filter below the band's top -- "
            "the stations' clearance cannot be proven"
        ),
    )

    # -- ADR-0014: the Well, the plate and its eight mounts ---------------
    keyboard_placement = _by_role(placements, "keyboard")
    keyboard_component = (
        keyboard_placement.component if keyboard_placement is not None else None
    )
    plate_model = None
    plate_model_error = ""
    getter = getattr(keyboard_component, "plate_model", None)
    if getter is not None:
        try:
            plate_model = getter()
        except (ValueError, KeyError) as exc:
            plate_model_error = str(exc)
    # The plate's real openings are part of the mounting pattern: the ears must
    # clear them and the sheet must stay connected around them, so the pattern
    # is derived with them here exactly as the pipeline injects it.
    from geometry.well_mounts import plate_cutouts

    cutouts = (
        plate_cutouts(plate_model) if plate_model is not None else ()
    )
    if mounts is None and keyboard_placement is not None:
        try:
            from geometry.well_mounts import well_mounts

            mounts = well_mounts(
                config,
                budget,
                placement=keyboard_placement,
                cutouts=cutouts,
            )
        except (ValueError, KeyError):
            # The plate/Well derivation is the one source for the pattern; if
            # it cannot run, the mount checks below fail with that verdict.
            mounts = None
    _add_well_checks(report, config, budget)
    _add_plate_checks(report, config, budget, plate_model)
    if plate_model is None and plate_model_error:
        report.warn(
            "the plate model could not be generated: " + plate_model_error
        )
    _add_mount_checks(
        report,
        config,
        budget,
        mounts,
        keyboard=keyboard_component,
        placements=placements,
    )

    report.goals["closed-face-height"] = budget.closed_face_height
    report.goals["open-face-height"] = budget.open_face_height
    report.goals["thickness"] = budget.thickness
    report.goals["width"] = budget.width
    report.goals["lid-thickness"] = budget.lid_thickness
    report.goals["display-cavity"] = budget.display_cavity
    report.goals["rod-x"] = budget.rod_x
    return report


__all__ = ["BUILD_VOLUME", "MIN_LID_CLEARANCE", "SWEEP_SAMPLES", "run_slider_checks"]
