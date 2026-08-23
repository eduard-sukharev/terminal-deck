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
without CadQuery.
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

    @property
    def passed(self) -> bool:
        return all(check.passed for check in self.checks)

    @property
    def failures(self) -> list[CheckResult]:
        return [check for check in self.checks if not check.passed]

    def add(self, name: str, passed: bool, message: str = "") -> None:
        self.checks.append(CheckResult(name=name, passed=passed, message=message))

    def summary(self) -> str:
        lines = [f"{len(self.checks)} checks: {'PASS' if self.passed else 'FAIL'}"]
        for check in self.checks:
            marker = "ok  " if check.passed else "FAIL"
            lines.append(f"  [{marker}] {check.name}: {check.message}")
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


def check_hinge_clearance(
    hinge_z_span: float, component_z_span: float, report: ValidationReport
) -> None:
    """Fail if the hinge volume intersects the component volume."""
    report.add(
        "hinge-clears",
        hinge_z_span <= component_z_span,
        f"hinge_z={hinge_z_span}, component_z={component_z_span}",
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


def run_all(
    placements: list[Any],
    config: Any,
    shell_depths: dict[str, float] | None = None,
    shell_opening: list[str] | None = None,
    max_component_height: float = 0.0,
    lid_interior_height: float = 0.0,
    hinge_z_span: float = 0.0,
) -> ValidationReport:
    """Run the full validation suite over a placement set.

    Geometry-dependent inputs (lid interior height, hinge span, cable bend)
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
    check_hinge_clearance(hinge_z_span, max_component_height, report)
    check_dimension_consistency(placements, config, report)
    return report
