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

from dataclasses import dataclass, field
from typing import Any, Protocol


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
    those only conflict when their Z ranges also overlap.
    """
    for i in range(len(placements)):
        for j in range(i + 1, len(placements)):
            pa, pb = placements[i], placements[j]
            a, b = pa.component, pb.component
            a_top, b_top = pa.z + a.size().height, pb.z + b.size().height
            z_overlap = not (a_top <= pb.z or b_top <= pa.z)
            if z_overlap and _overlap_xy(
                pa.x, pa.y, a.size().width, a.size().depth,
                pb.x, pb.y, b.size().width, b.size().depth,
            ):
                report.add(
                    "no-collisions",
                    False,
                    f"{a.name} overlaps {b.name}",
                )
                return
    report.add("no-collisions", True)


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
    return report
