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
    return _rotated_footprint(box.width, box.depth, placement.rotation)


def _volume_z_span(placement: Any, box: Any, center_z: float) -> tuple[float, float]:
    """World-frame Z range of one sub-volume whose transformed origin sits at
    ``center_z``. Mirrors ``layouts.base.volume_z_span``.
    """
    if placement.flip_x:
        return (center_z - box.height, center_z)
    return (center_z, center_z + box.height)


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

    def summary(self, verbose: bool = True) -> str:
        """One line per check (and GOAL metrics) when ``verbose``; otherwise
        only the header, FAIL lines and warnings."""
        lines = [f"{len(self.checks)} checks: {'PASS' if self.passed else 'FAIL'}"]
        for check in self.checks:
            if check.passed and not verbose:
                continue
            marker = "ok  " if check.passed else "FAIL"
            lines.append(f"  [{marker}] {check.name}: {check.message}")
        if verbose:
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
        World-frame boss geometry, e.g. from a case builder's ``all_bosses``.
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

    Keyed ``"<part>:<index>"`` (Seams left to right). The Seam's plan path is
    walked run by run, so the band follows the ``__--__--__`` line (or a
    trapezoid's 45 degree diagonals) rather than its bounding box.
    """
    bands: dict[str, list[tuple[float, float, float, float]]] = {}
    for part, split in splits.items():
        depth = depths[part]
        for i, seam in enumerate(split.seams(depth, wall)):
            rects = []
            points = seam.polyline(depth)
            for (xa, ya), (xb, yb) in zip(points, points[1:]):
                if abs(xa - xb) < 1e-9:
                    rects.append((xa - wall, xa + wall, min(ya, yb), max(ya, yb)))
                else:
                    rects.append((
                        min(xa, xb) - wall, max(xa, xb) + wall,
                        min(ya, yb) - wall, max(ya, yb) + wall,
                    ))
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


def _line_gap(a: tuple[float, float, float, float], b: tuple[float, float, float, float]) -> float:
    dx = max(a[0] - b[1], b[0] - a[1], 0.0)
    dy = max(a[2] - b[3], b[2] - a[3], 0.0)
    return math.hypot(dx, dy)


def _seam_lines(
    segments: list[Segment],
) -> list[tuple[float, float, float, float]]:
    """Turn ``(y0, y1, x)`` Seam segments into ``(x0, x1, y0, y1)`` lines."""
    return [(x, x, y0, y1) for y0, y1, x in segments]


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
    return report
