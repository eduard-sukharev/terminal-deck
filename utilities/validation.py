"""Placement and geometry validation.

Every build runs these checks before and after enclosure generation:

* No collisions between placed components
* No floating bosses (every boss backed by a wall)
* Minimum wall thickness preserved
* Minimum screw clearance
* Minimum cable bend radius
* No connector blocked by another component or the shell
* Lid closes (lid interior clears the highest placed component)
* Hinge clears (hinge geometry does not intersect components)

The checks operate on pure data (placements + component specs) so they run
without a CAD library.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Protocol


def _rotated_footprint(width: float, depth: float, rotation: float) -> tuple[float, float]:
    """Axis-aligned world-frame ``(width, depth)`` of a box rotated about Z.

    Duplicated from ``layouts.base.rotated_footprint`` rather than imported:
    ``utilities`` sits below ``layouts`` in the import graph (``layouts``
    already imports from ``components``, which imports from ``utilities``),
    so importing back from ``layouts`` here would be circular.
    """
    rad = math.radians(rotation)
    eff_w = abs(width * math.cos(rad)) + abs(depth * math.sin(rad))
    eff_d = abs(width * math.sin(rad)) + abs(depth * math.cos(rad))
    return eff_w, eff_d


def _volume_footprint(placement: Any, box: Any) -> tuple[float, float]:
    """World-frame XY extent of one sub-volume under a placement's transform.

    Mirrors ``layouts.base.volume_footprint``; kept local because
    ``utilities`` sits below ``layouts`` in the import graph (see
    :func:`_rotated_footprint`).
    """
    eff_w, eff_d = _rotated_footprint(box.width, box.depth, placement.rotation)
    tilt = getattr(placement, "tilt_x", 0.0)
    if tilt:
        rad = math.radians(tilt)
        eff_d = abs(eff_d * math.cos(rad)) + abs(box.height * math.sin(rad))
    return eff_w, eff_d


def _volume_z_span(placement: Any, box: Any, center_z: float) -> tuple[float, float]:
    """World-frame Z range of one sub-volume whose transformed origin sits at
    ``center_z``. Mirrors ``layouts.base.volume_z_span``.
    """
    z0, z1 = (
        (center_z - box.height, center_z) if placement.flip_x
        else (center_z, center_z + box.height)
    )
    tilt = getattr(placement, "tilt_x", 0.0)
    if not tilt:
        return (z0, z1)
    _, depth = _rotated_footprint(box.width, box.depth, placement.rotation)
    half = abs(depth / 2.0 * math.sin(math.radians(tilt)))
    return (z0 - half, z1 + half)


class SizedComponent(Protocol):
    """Minimal component surface needed by validation."""

    def size(self) -> Any: ...
    def keepout(self) -> Any: ...
    def mounting_holes(self) -> list[Any]: ...
    def connectors(self) -> list[Any]: ...


@dataclass(frozen=True)
class CheckResult:
    """Outcome of a single validation check."""

    name: str
    passed: bool
    message: str = ""


@dataclass
class ValidationReport:
    """Aggregated results of all checks for one build."""

    checks: list[CheckResult] = field(default_factory=list)
    #: GOAL metrics: reported, never a failure.
    goals: dict[str, float] = field(default_factory=dict)
    #: SOFT findings: reported, never a failure.
    warnings: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return all(check.passed for check in self.checks)

    @property
    def failures(self) -> list[CheckResult]:
        return [check for check in self.checks if not check.passed]

    def add(self, name: str, passed: bool, message: str = "") -> None:
        self.checks.append(CheckResult(name=name, passed=passed, message=message))

    def warn(self, message: str) -> None:
        """Record a SOFT finding: reported in the summary, never fails the build."""
        self.warnings.append(message)

    def summary(self) -> str:
        lines = [f"{len(self.checks)} checks: {'PASS' if self.passed else 'FAIL'}"]
        for check in self.checks:
            marker = "ok  " if check.passed else "FAIL"
            lines.append(f"  [{marker}] {check.name}: {check.message}")
        for name, value in self.goals.items():
            lines.append(f"  [goal] {name}: {value:.2f}")
        for message in self.warnings:
            lines.append(f"  [warn] {message}")
        return "\n".join(lines)


def _overlap_xy(
    ax: float,
    ay: float,
    aw: float,
    ad: float,
    bx: float,
    by: float,
    bw: float,
    bd: float,
) -> bool:
    """True if two axis-aligned rectangles overlap in the XY plane."""
    ax0, ax1 = ax - aw / 2, ax + aw / 2
    ay0, ay1 = ay - ad / 2, ay + ad / 2
    bx0, bx1 = bx - bw / 2, bx + bw / 2
    by0, by1 = by - bd / 2, by + bd / 2
    return not (ax1 <= bx0 or bx1 <= ax0 or ay1 <= by0 or by1 <= ay0)


def check_collisions(placements: list[Any], report: ValidationReport) -> None:
    """Fail if any two placements overlap in both XY and Z.

    The clamshell overlaps the lid (display) over the base (keyboard) in XY;
    those only conflict when their Z ranges also overlap. Comparison uses each
    component's solid sub-volumes (``occupied_volumes``) so hollow parts (e.g.
    the raised keyboard plate) only collide where they actually occupy space.
    """
    for i in range(len(placements)):
        for j in range(i + 1, len(placements)):
            pa, pb = placements[i], placements[j]
            a, b = pa.component, pb.component
            for ax, ay, az, abox in a.occupied_volumes():
                for bx, by, bz, bbox in b.occupied_volumes():
                    # World-frame volume centers (rotation + flip aware).
                    wx, wy, wz = pa.world_offset(ax, ay, az)
                    vx, vy, vz = pb.world_offset(bx, by, bz)
                    # Flipped components hang below their origin.
                    a_z0, a_z1 = _volume_z_span(pa, abox, wz)
                    b_z0, b_z1 = _volume_z_span(pb, bbox, vz)
                    z_overlap = not (a_z1 <= b_z0 or b_z1 <= a_z0)
                    aw, ad = _volume_footprint(pa, abox)
                    bw, bd = _volume_footprint(pb, bbox)
                    if z_overlap and _overlap_xy(wx, wy, aw, ad, vx, vy, bw, bd):
                        report.add(
                            "no-collisions",
                            False,
                            f"{a.name} overlaps {b.name}",
                        )
                        return
    report.add("no-collisions", True)


def check_boss_collisions(
    bosses: list[tuple[float, float, float, float, Any]],
    placements: list[Any],
    report: ValidationReport,
) -> None:
    """Fail if a boss overlaps a component it isn't attached to.

    A boss (a component's own mounting boss, or a deck-mount standoff) is
    case-build-time geometry generated from ``mounting_holes()``/the deck
    layout — it is never itself a placed component, so ``check_collisions``
    (which compares placed components against each other) never sees it.
    Nothing else previously caught one landing inside a part it doesn't
    support: this was found by hand, once, with an ad hoc script built
    specifically to check it — this makes that check permanent.

    Parameters
    ----------
    bosses : list of (x, y, diameter, height, owner)
        World-frame boss geometry, e.g. from ``case.base.Base.all_bosses``.
        ``owner`` is the component the boss supports (skipped in that
        component's own check — a mounting boss legitimately touches the
        part it holds up) or ``None`` for a deck-mount standoff, which
        belongs to no single component and is checked against all of them.
    """
    for bx, by, diameter, height, owner in bosses:
        for placement in placements:
            component = placement.component
            if component is owner:
                continue
            for ax, ay, az, abox in component.occupied_volumes():
                wx, wy, wz = placement.world_offset(ax, ay, az)
                z0, z1 = _volume_z_span(placement, abox, wz)
                if z1 <= 0.0 or height <= z0:
                    continue
                w, d = _volume_footprint(placement, abox)
                if _overlap_xy(bx, by, diameter, diameter, wx, wy, w, d):
                    report.add(
                        "no-boss-collisions",
                        False,
                        f"boss at ({bx:.1f}, {by:.1f}) overlaps {component.name}",
                    )
                    return
    report.add("no-boss-collisions", True)


def check_floating_bosses(
    placements: list[Any], shell_depths: dict[str, float], report: ValidationReport
) -> None:
    """Fail if a mounting boss has no wall beneath it.

    ``shell_depths`` maps a component name to the wall/support depth beneath
    its bosses; a depth of 0 means no wall exists.
    """
    for placement in placements:
        component = placement.component
        if not component.mounting_holes():
            # No bosses to support (e.g. bezel-held display).
            continue
        depth = shell_depths.get(component.name, 0.0)
        if depth <= 0.0:
            report.add(
                "no-floating-bosses",
                False,
                f"{component.name} has mounting holes but no supporting wall",
            )
            return
    report.add("no-floating-bosses", True)


def check_minimum_wall_thickness(config: Any, report: ValidationReport) -> None:
    """Fail if wall thickness falls below the configured minimum."""
    minimum = config.wall.thickness
    report.add(
        "minimum-wall-thickness",
        minimum >= 2.0,
        f"wall_thickness={minimum}",
    )


def check_screw_clearance(config: Any, report: ValidationReport) -> None:
    """Fail if configured screw clearance is below the printable minimum."""
    minimum = config.material.minimum_feature
    clearance = config.clearance.screw
    report.add(
        "minimum-screw-clearance",
        clearance >= minimum,
        f"screw_clearance={clearance}, printable_min={minimum}",
    )


def check_cable_bend(radius: float, minimum_radius: float, report: ValidationReport) -> None:
    """Fail if a routed cable bend is tighter than the minimum radius."""
    report.add(
        "minimum-cable-bend",
        radius >= minimum_radius,
        f"bend_radius={radius}, minimum={minimum_radius}",
    )


def check_connectors_accessible(
    placements: list[Any], shell_opening: list[str], report: ValidationReport
) -> None:
    """Fail if an externally-accessible connector has no matching shell opening.

    ``shell_opening`` lists connector type identifiers that have a cutout in
    the shell. Internal connectors (``Connector.internal``) mate to parts
    inside the case and need no opening.
    """
    for placement in placements:
        for connector in placement.component.connectors():
            if connector.internal:
                continue
            if connector.type not in shell_opening:
                report.add(
                    "no-blocked-connector",
                    False,
                    f"{placement.component.name} connector {connector.type} has no shell opening",
                )
                return
    report.add("no-blocked-connector", True)


def check_lid_clearance(
    max_component_height: float, lid_interior_height: float, report: ValidationReport
) -> None:
    """Fail if the lid interior does not clear the tallest placed component."""
    report.add(
        "lid-closes",
        max_component_height <= lid_interior_height,
        f"component_z={max_component_height}, lid_interior_z={lid_interior_height}",
    )


def check_torque_hinge(
    hinge: Any,
    report: ValidationReport,
    *,
    case_width: float,
    case_depth: float,
    base_top: float,
    parting: float,
    lid_height: float,
    wall: float,
    minimum_feature: float,
    base_placements: list[Any],
    axis_world: tuple[float, float],
    lid_placements: list[Any],
    lid_axis: tuple[float, float],
    deck_seams: list[float],
    deck_columns: list[tuple[float, float, float, float]] = (),
) -> None:
    """HARD checks that the case can take the Torque hinges (ADR 0007).

    Heights are in the hinge frame (axis at 0, closed, Base below): the Deck
    top ``base_top``, the Parting plane ``parting`` and the Lid's back
    ``lid_height``. ``axis_world`` is the axis ``(y, z)`` in the world frame
    of ``base_placements``; ``lid_axis`` the same in the Lid's own (turned
    over) frame of ``lid_placements``.
    """
    rear_y = -case_depth / 2.0
    insert = hinge.insert()
    sides = ("left", "right")

    # Each insert bore fits between its Leaf and the shell's outer surface.
    rooms = {
        "base": hinge.insert_room("base", base_top, minimum_feature),
        "lid": hinge.insert_room("lid", lid_height, minimum_feature),
    }
    short = [f"{w} {r:.1f} mm" for w, r in rooms.items() if r < insert.depth - 1e-9]
    report.add(
        "hinge-insert-depth", not short,
        f"room for the {insert.size} inserts: "
        + ", ".join(f"{w} {r:.1f} mm" for w, r in rooms.items())
        + (f" (< {insert.depth:g} mm: {', '.join(short)})" if short else ""),
    )

    # The Base leaf stays above the Parting plane (it belongs to the Deck);
    # the Lid leaf stays inside the Lid's back.
    base_low = hinge.leaf_z("base")[0] - hinge.fit
    lid_high = hinge.leaf_z("lid")[1] + hinge.fit
    report.add(
        "hinge-leaf-in-shell",
        base_low >= parting - 1e-9 and lid_high <= lid_height - wall + 1e-9,
        f"Base leaf down to {base_low:.1f} mm (Parting plane {parting:.1f}), "
        f"Lid leaf up to {lid_high:.1f} mm (Lid back {lid_height - wall:.1f})",
    )

    # Every hole's insert sits in the pad, inside the case, with a skin round it.
    bad = []
    r = insert.outside_diameter / 2.0 + minimum_feature
    for which in ("base", "lid"):
        for side in sides:
            for x, y, _ in hinge.holes(which, rear_y, side):
                if y - r < rear_y - 1e-9 or abs(x) + r > case_width / 2.0 - wall + 1e-9:
                    bad.append(f"{which} {side} ({x:.1f}, {y:.1f})")
    report.add(
        "hinge-holes-in-material", not bad,
        "every Leaf hole's insert sits inside the case" if not bad
        else f"insert outside the case: {', '.join(bad)}",
    )

    # The Lid swings clear of the Base through its whole travel.
    hits = hinge.sweep_hits(lid_depth=case_depth, lid_height=lid_height)
    report.add(
        "hinge-sweep-clears", not hits,
        f"the Lid swings clear through {hinge.travel:g} deg" if not hits
        else f"the Lid enters the Base at {hits[0][0]:.0f} deg ({len(hits)} sample hits)",
    )

    # The travel stop: the Lid lands on it at `travel` and not before, along
    # its rear face, and the ribs stay clear of the Cable guard.
    if hinge.has_stop:
        hits = hinge.stop_hits(lid_depth=case_depth, lid_height=lid_height, parting=parting)
        problems = []
        if hits:
            problems.append(f"the Lid meets a stop rib at {hits[0][0]:.0f} deg, before {hinge.travel:g}")
        if hinge.stop_face > lid_height + 1e-9:
            problems.append(f"stop face {hinge.stop_face:g} mm longer than the Lid's rear face {lid_height:.1f}")
        if hinge.guard is not None:
            gx0, gx1 = hinge.guard.span()
            problems += [
                f"{side} rib overlaps the Cable guard"
                for side in sides
                if gx0 < hinge.stop_span(side)[1] and gx1 > hinge.stop_span(side)[0]
            ]
        report.add(
            "hinge-stop", not problems,
            f"the Lid lands on the stop ribs at {hinge.travel:g} deg" if not problems
            else "; ".join(problems),
        )

    # No component inside a Leaf or its pad (Base: world frame; Lid: its own).
    hits = []
    for which, placements, (ay, az), flip in (
        ("base", base_placements, axis_world, 1.0),
        ("lid", lid_placements, lid_axis, -1.0),
    ):
        z0, z1 = hinge.leaf_z(which)
        pad_z = (base_top, z0) if which == "base" else (z1, lid_height)
        lo, hi = min(z0, pad_z[0], pad_z[1]), max(z1, pad_z[0], pad_z[1])
        zs = sorted((az + flip * lo, az + flip * hi))
        for side in sides:
            kx0, kx1, ky0, ky1 = hinge.pad_rect(which, rear_y, side)
            for p in placements:
                x0, y0, x1, y1 = p.box
                pz0, pz1 = p.z_bounds()
                if x0 < kx1 and x1 > kx0 and y0 < ky1 and y1 > ky0 and pz0 < zs[1] and pz1 > zs[0]:
                    hits.append(f"{p.component.__class__.__name__} in the {side} {which} leaf pad")
    for side in sides:
        kx0, kx1, ky0, ky1 = hinge.pad_rect("base", rear_y, side)
        for cx0, cx1, cy0, cy1 in deck_columns:
            if cx0 < kx1 and cx1 > kx0 and cy0 < ky1 and cy1 > ky0:
                hits.append(f"Deck column ({(cx0 + cx1) / 2:.1f}, {(cy0 + cy1) / 2:.1f}) in the {side} base leaf pad")
    report.add(
        "hinge-clears", not hits,
        f"components inside the hinge: {', '.join(hits)}" if hits
        else "no component or Deck column inside a Leaf or its pad",
    )

    guard = hinge.guard
    if guard is not None:
        gx0, gx1 = guard.span()
        crossing = []
        for side in sides:
            x0, x1, _, _ = hinge.pad_rect("base", rear_y, side)
            if gx0 < x1 and gx1 > x0:
                crossing.append(f"{side} hinge")
        crossing += [f"Deck Seam x={x:g}" for x in deck_seams if gx0 - wall < x < gx1 + wall]
        report.add(
            "cable-guard-clear", not crossing,
            f"Cable guard {gx0:.1f}..{gx1:.1f} clear of the hinges and Deck Seams" if not crossing
            else f"Cable guard {gx0:.1f}..{gx1:.1f} overlaps {', '.join(crossing)}",
        )


def check_hinge_fits(
    diameter: float, base_rear_height: float, lid_height: float, report: ValidationReport
) -> None:
    """Fail if the hinge barrel, centred on the closed interface plane, would
    reach past the Base's bottom or the Lid's back (half a diameter each side)."""
    radius = diameter / 2.0
    room = min(base_rear_height, lid_height)
    report.add(
        "hinge-fits",
        radius <= room,
        f"barrel radius {radius:.2f} mm vs rear room {room:.2f} mm "
        f"(Base {base_rear_height:.2f}, Lid {lid_height:.2f})",
    )


def check_dimension_consistency(
    placements: list[Any],
    config: Any,
    report: ValidationReport,
) -> None:
    """Fail if component dimensions contradict each other.

    Checks:
    1. Keyboard plate and display widths are compatible (they share the hinge
       axis — the lid and base must have similar widths).
    2. Every placed component fits within the enclosure envelope.
    """
    wall = config.wall_thickness
    clearance = config.clearance.shell

    kb_placement = None
    display_placement = None
    for p in placements:
        name = p.component.name.lower()
        if "keyboard" in name:
            kb_placement = p
        if "display" in name:
            display_placement = p

    if kb_placement and display_placement:
        kb = kb_placement.component.size()
        disp = display_placement.component.size()
        kb_env = kb.width + 2 * (wall + clearance)
        disp_env = disp.width + 2 * (wall + clearance)
        ratio = max(kb_env, disp_env) / min(kb_env, disp_env)
        report.add(
            "dimension-consistency",
            ratio <= 1.15,
            f"keyboard envelope={kb_env:.1f} x {kb.depth:.1f}, "
            f"display envelope={disp_env:.1f} x {disp.depth:.1f}, "
            f"width ratio={ratio:.3f}",
        )
    else:
        report.add("dimension-consistency", True, "keyboard/display not both present — skipped")


#: Parts screwed to each other, whose Seams must not line up (ADR 0003): the
#: Tray carries the Deck and the keyboard plate; the Lid shell carries the
#: Bezel. Base and Lid parts are free to coincide in X, and so are the Deck and
#: the keyboard plate (the plate is supported independently on Tray standoffs).
STAGGERED_PAIRS: tuple[tuple[str, str], ...] = (("tray", "deck"), ("lid_shell", "bezel"))


def _part_ranges(split: Any) -> list[tuple[float, float]]:
    return [seam.x_range for seam in split.seams()]


Segment = tuple[float, float, float]  # (y0, y1, x)


def _seam_lines(
    segments: list[Segment],
) -> list[tuple[float, float, float, float]]:
    """A Seam as axis-aligned lines ``(x0, x1, y0, y1)``: its segments and the
    jog between each pair."""
    lines = [(x, x, y0, y1) for y0, y1, x in segments]
    for (_, ya, xa), (_, _, xb) in zip(segments, segments[1:]):
        lines.append((min(xa, xb), max(xa, xb), ya, ya))
    return lines


def _line_gap(a: tuple[float, float, float, float], b: tuple[float, float, float, float]) -> float:
    dx = max(a[0] - b[1], b[0] - a[1], 0.0)
    dy = max(a[2] - b[3], b[2] - a[3], 0.0)
    return math.hypot(dx, dy)


def seams_gap(a: list[Segment], b: list[Segment]) -> float:
    """Closest approach (mm) between two Seams given as ``(y0, y1, x)`` segments."""
    return min(_line_gap(la, lb) for la in _seam_lines(a) for lb in _seam_lines(b))


def check_seams(
    config: Any,
    case_width: float,
    report: ValidationReport,
    plate_seam: list[Segment] | None = None,
    case_depth: float = 100.0,
) -> None:
    """Fail if Seams of screwed-together parts line up or cut a protected spot.

    * Seams are staggered between parts screwed to each other
      (:data:`STAGGERED_PAIRS`, plus Tray vs keyboard plate when
      ``plate_seam`` is given as world-frame ``(y0, y1, x)`` segments): the
      Seam lines, jogs included, stay at least ``4 * wall`` apart, so no single
      weak line runs through a joined assembly.
    * The Tray Seams avoid every foot recess.
    * The Bezel Seam lies inside the display opening.
    """
    splits = config.split
    min_gap = 4.0 * config.wall_thickness

    def lines(part: str) -> list[list[Segment]]:
        return [seam.segments(case_depth) for seam in splits[part].seams()]

    clashes = []
    for a, b in STAGGERED_PAIRS:
        if a in splits and b in splits:
            if any(seams_gap(sa, sb) < min_gap for sa in lines(a) for sb in lines(b)):
                clashes.append(f"{a}/{b}")
    if plate_seam is not None and "tray" in splits:
        if any(seams_gap(sa, plate_seam) < min_gap for sa in lines("tray")):
            clashes.append("tray/keyboard_plate")
    report.add(
        "seams-staggered", not clashes,
        f"no screwed-together Seams within {min_gap:g} mm" if not clashes
        else f"Seams too close: {', '.join(clashes)}",
    )

    if "tray" in splits:
        feet = config.feet
        hit = [
            fx for fx in (-1, 1)
            for cx in [fx * (case_width / 2.0 - feet.inset_x)]
            for x0, x1 in _part_ranges(splits["tray"])
            if x1 > cx - feet.diameter / 2.0 and x0 < cx + feet.diameter / 2.0
        ]
        ranges = ", ".join(f"{x0:g}..{x1:g}" for x0, x1 in _part_ranges(splits["tray"]))
        report.add("seam-avoids-feet", not hit, f"tray Seam x={ranges}")

    if "bezel" in splits:
        half_open = (config.display.width - 2.0 * config.bezel.inset) / 2.0
        ranges = _part_ranges(splits["bezel"])
        report.add(
            "seam-in-display-opening",
            all(-half_open <= x0 and x1 <= half_open for x0, x1 in ranges),
            f"bezel Seam x={ranges[0][0]:g}..{ranges[-1][1]:g}, opening +-{half_open:g}",
        )


@dataclass(frozen=True)
class Feature:
    """A structural feature's XY footprint (mm), for Seam clearance.

    ``kind`` is rib, boss, standoff, column, cradle, vent, lug or hinge.
    ``joins`` names the Seam (``"<part>:<index>"``, as keyed by
    :func:`seam_bands`) that a Seam-joint lug is *meant* to straddle; that one
    Seam is exempt, every other Seam must still keep clear of it. ``part``
    names the part the feature is made of (``"tray"``, ``"deck"``); only that
    part's Seams can cross it. ``None`` means every part (a column is a Tray
    post and a Deck boss at once).
    """

    kind: str
    name: str
    x0: float
    x1: float
    y0: float
    y1: float
    joins: str | None = None
    part: str | None = None


def seam_bands(
    splits: dict[str, Any], depths: dict[str, float], wall: float
) -> dict[str, list[tuple[float, float, float, float]]]:
    """``(x0, x1, y0, y1)`` rectangles covering each Seam ± its steps ± one wall.

    Keyed ``"<part>:<index>"`` (Seams left to right). A stepped Seam is a
    rectangle per segment plus one per jog face, so the band follows the
    ``__--__--__`` line rather than its bounding box.
    """
    bands: dict[str, list[tuple[float, float, float, float]]] = {}
    for part, split in splits.items():
        depth = depths[part]
        for i, seam in enumerate(split.seams()):
            rects = []
            segs = seam.segments(depth)
            for y0, y1, x in segs:
                rects.append((x - wall, x + wall, y0, y1))
            for (_, ya, xa), (_, _, xb) in zip(segs, segs[1:]):
                rects.append((min(xa, xb) - wall, max(xa, xb) + wall, ya - wall, ya + wall))
            bands[f"{part}:{i}"] = rects
    return bands


def check_seam_clearance(
    bands: dict[str, list[tuple[float, float, float, float]]],
    features: list[Feature],
    report: ValidationReport,
    tolerance: float = 1e-6,
) -> None:
    """Fail if any Seam band crosses a structural feature (ADR 0003).

    A Seam may never thin a rib, boss, standoff, column, cradle, vent or lug;
    the one exemption is a lug meant for that very Seam (``Feature.joins``).
    """
    hits = []
    for seam_id, rects in bands.items():
        for feature in features:
            if feature.joins == seam_id:
                continue
            if feature.part is not None and not seam_id.startswith(feature.part + ":"):
                continue
            for x0, x1, y0, y1 in rects:
                if (
                    feature.x0 < x1 - tolerance and feature.x1 > x0 + tolerance
                    and feature.y0 < y1 - tolerance and feature.y1 > y0 + tolerance
                ):
                    hits.append(f"{seam_id} crosses {feature.kind} {feature.name}")
                    break
    report.add(
        "seams-clear-of-features", not hits,
        "; ".join(hits) if hits
        else f"{len(bands)} Seam band(s) clear of {len(features)} feature(s)",
    )


def _point_seam_gap(x: float, y: float, segments: list[Segment]) -> tuple[float, str]:
    """Distance (mm) from a point to a Seam line and which side of it the point is on."""
    lines = _seam_lines(segments)
    gap = min(_line_gap((x, x, y, y), line) for line in lines)
    at_y = [lx0 for lx0, lx1, ly0, ly1 in lines if ly0 - 1e-6 <= y <= ly1 + 1e-6]
    ref = min(at_y) if at_y and x < min(at_y) else (max(at_y) if at_y else 0.0)
    return gap, "left" if x < ref else "right"


def check_plate_seam_screws(
    holes: list[tuple[float, float]],
    seam: list[Segment],
    unit: float,
    report: ValidationReport,
    expected_total: int | None = None,
) -> None:
    """Fail unless each plate Section has a screw in each half within ``unit`` of the Seam.

    ``holes`` are plate-local ``(x, y)``; ``seam`` the plate Seam as
    ``(y0, y1, x)`` segments. "Lower"/"upper" halves are split at the plate's
    middle row line. With ``expected_total``, the plate must also carry exactly
    that many screws (eight: four at the edges, four at the Seam).
    """
    y_mid = (min(s[0] for s in seam) + max(s[1] for s in seam)) / 2.0
    covered: set[tuple[str, str]] = set()
    for x, y in holes:
        gap, side = _point_seam_gap(x, y, seam)
        if gap > unit + 1e-9:
            continue
        covered.add((side, "lower" if y < y_mid else "upper"))
    missing = [
        f"{side} {half}" for side in ("left", "right") for half in ("lower", "upper")
        if (side, half) not in covered
    ]
    problems = []
    if missing:
        problems.append(f"no screw within {unit:g} mm of the Seam for: {', '.join(missing)}")
    if expected_total is not None and len(holes) != expected_total:
        problems.append(f"{len(holes)} plate screws, expected {expected_total}")
    report.add(
        "plate-seam-screws", not problems,
        "; ".join(problems) if problems
        else f"{len(holes)} plate screws, a lower and an upper one within {unit:g} mm of the Seam per Section",
    )


def check_screw_heads_clear_of_feet(
    heads: list[tuple[float, float, float]],
    feet: list[tuple[float, float, float]],
    report: ValidationReport,
) -> None:
    """Fail if any bottom screw head ``(x, y, radius)`` overlaps a foot recess."""
    hits = [
        f"head at ({hx:.1f}, {hy:.1f}) in foot recess at ({fx:.1f}, {fy:.1f})"
        for hx, hy, hr in heads for fx, fy, fr in feet
        if math.hypot(hx - fx, hy - fy) < hr + fr
    ]
    report.add(
        "screw-heads-clear-of-feet", not hits,
        "; ".join(hits) if hits else f"{len(heads)} bottom screw head(s) clear of {len(feet)} foot recess(es)",
    )


def check_deck_screw(size: str, grip: float, report: ValidationReport) -> None:
    """Fail unless a stock screw of ``size`` engages the Deck insert across ``grip``."""
    from geometry.parting import deck_screw

    try:
        screw = deck_screw(size, grip)
    except ValueError as exc:
        report.add("deck-screw-length", False, str(exc))
        return
    report.add(
        "deck-screw-length", True,
        f"{screw.name}: {screw.engagement:g} mm into the insert across a {grip:g} mm grip",
    )


def check_visor_flush(
    deck_top_at: Any,
    visor_height_at: Any,
    rear_y: float,
    front_y: float,
    report: ValidationReport,
    samples: int = 21,
    tolerance: float = 1e-6,
) -> None:
    """Fail unless the Visor closes the Deck's slope into a box.

    Closed, ``deck_top + visor_height`` must be one constant plane along Y
    (Lid underside parallel to the Deck's base), the Visor must never be
    negative, and it must vanish at the hinge end.
    """
    ys = [rear_y + (front_y - rear_y) * i / (samples - 1) for i in range(samples)]
    tops = [deck_top_at(y) + visor_height_at(y) for y in ys]
    flat = max(tops) - min(tops)
    report.add(
        "visor-closes-flush", flat <= tolerance,
        f"Lid underside varies {flat:.3g} mm over the Deck",
    )
    report.add(
        "visor-zero-at-hinge", abs(visor_height_at(rear_y)) <= tolerance,
        f"Visor height at hinge {visor_height_at(rear_y):.3g} mm",
    )
    report.add(
        "visor-non-negative", all(visor_height_at(y) >= -tolerance for y in ys),
        "Visor height >= 0 everywhere",
    )


def run_all(
    placements: list[Any],
    config: Any,
    shell_depths: dict[str, float] | None = None,
    shell_opening: list[str] | None = None,
    max_component_height: float = 0.0,
    lid_interior_height: float = 0.0,
) -> ValidationReport:
    """Run the full validation suite over a placement set.

    Geometry-dependent inputs (lid interior height, cable bend)
    default to ``0`` and should be supplied by the assembly/case stage.
    """
    report = ValidationReport()
    check_collisions(placements, report)
    check_floating_bosses(
        placements, shell_depths or {}, report
    )
    check_minimum_wall_thickness(config, report)
    check_screw_clearance(config, report)
    check_cable_bend(0.0, 0.0, report)  # filled by routing stage
    check_connectors_accessible(placements, shell_opening or [], report)
    check_lid_clearance(max_component_height, lid_interior_height, report)
    check_dimension_consistency(placements, config, report)
    return report
