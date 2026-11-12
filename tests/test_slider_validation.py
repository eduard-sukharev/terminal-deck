"""ADR-0014 Well/plate/mount invariants as HARD slider checks (issue #16).

The shipped design must pass every check; each check is then forced to fail
with a synthetic violation (a deeper Parting plane, a thin ring, a station
inside a cutout, ...) so the report cannot silently lose an invariant. All
checks are data-layer: no CAD import.
"""

import dataclasses

import pytest

from components.slide import compute_slide_budget
from geometry.well_mounts import well_mounts
from layouts import make_layout
from main import BuildPipeline
from utilities.slider_validation import (
    _add_mount_checks,
    _add_plate_checks,
    _add_well_checks,
    run_slider_checks,
)
from utilities.validation import ValidationReport

#: Every new HARD check from the ADR-0014 validation ticket.
NEW_CHECKS = (
    "keyboard-well-parting",
    "keyboard-well-ring",
    "keyboard-well-cutout",
    "keyboard-plate-overhang",
    "keyboard-plate-border",
    "keyboard-plate-seam",
    "keyboard-plate-sections",
    "keyboard-mounts-stations",
    "keyboard-mounts-fit",
    "keyboard-mounts-parting",
)


@pytest.fixture(scope="module")
def shipped():
    """The real shipped design, in the pipeline's own order (issue #16)."""
    pipeline = BuildPipeline("config/default.yaml", layout_name="slider")
    config = pipeline.load_config()
    components = pipeline.load_components()
    placements = make_layout("slider", components, config=config).placements()
    budget = compute_slide_budget(config, components)
    keyboard = components["keyboard"]
    placement = next(p for p in placements if p.component is keyboard)
    mounts = well_mounts(config, budget, placement=placement)
    keyboard.set_well_mounts(mounts)
    report = run_slider_checks(budget, config, placements, mounts=mounts)
    return config, components, placements, budget, mounts, report


def _check(report, name):
    return next(check for check in report.checks if check.name == name)


def _report_for(
    check_name, config, budget, *, mounts=None, model=None, keyboard=None
):
    """A report holding just the check under test, for a synthetic input."""
    report = ValidationReport()
    if check_name.startswith("keyboard-well-"):
        _add_well_checks(report, config, budget)
    elif check_name.startswith("keyboard-plate-"):
        _add_plate_checks(report, config, budget, model)
    else:
        _add_mount_checks(report, config, budget, mounts, keyboard=keyboard)
    return report


@dataclasses.dataclass
class _Metadata:
    width: float
    height: float
    cutout: tuple[float, float, float, float]
    edge_margins: tuple[float, float, float, float]
    plate_thickness: float = 1.5


@dataclasses.dataclass
class _Model:
    """The minimal plate model the validation checks read (duck-typed)."""

    metadata: _Metadata
    plate_outline: list[tuple[float, float]]
    seam: object | None = None
    section_outlines: list[list[tuple[float, float]]] = dataclasses.field(
        default_factory=list
    )


@pytest.fixture(scope="module")
def plate_model(shipped):
    _, components, _, _, _, _ = shipped
    return components["keyboard"].plate_model()


@pytest.mark.parametrize("name", NEW_CHECKS)
def test_new_checks_are_hard_and_pass_on_the_shipped_design(shipped, name):
    *_, report = shipped
    check = _check(report, name)
    assert check.passed, check.message
    assert check.message, "a HARD check must report its measured values"


# ── Well ───────────────────────────────────────────────────────────────


def test_well_parting_fails_when_the_plane_cuts_the_well(shipped):
    config, _, _, budget, _, _ = shipped
    well = budget.well
    joint = dataclasses.replace(
        budget.chassis_joint, parting_z=well.plate_bottom + 0.5
    )
    broken = dataclasses.replace(budget, chassis_joint=joint)
    report = _report_for("keyboard-well-parting", config, broken)
    check = _check(report, "keyboard-well-parting")
    assert not check.passed
    assert f"{joint.parting_z:.2f}" in check.message
    assert f"{well.plate_bottom:.2f}" in check.message


def test_well_ring_fails_when_a_side_is_thinner_than_the_wall(shipped):
    config, _, _, budget, _, _ = shipped
    well = budget.well
    wall = config.wall.thickness
    thin = wall - 0.5
    broken_well = dataclasses.replace(
        well,
        ring=thin,
        plate_width=well.cutout_width + 2.0 * thin,
        plate_depth=well.cutout_depth + 2.0 * thin,
    )
    broken = dataclasses.replace(budget, well=broken_well)
    report = _report_for("keyboard-well-ring", config, broken)
    check = _check(report, "keyboard-well-ring")
    assert not check.passed
    assert f"{thin:.2f}" in check.message
    assert f"{wall:.2f}" in check.message


def test_well_cutout_fails_when_it_is_not_the_keycap_plus_wobble(shipped):
    config, _, _, budget, _, _ = shipped
    well = budget.well
    broken = dataclasses.replace(
        budget, well=dataclasses.replace(well, cutout_width=well.cutout_width + 1.0)
    )
    report = _report_for("keyboard-well-cutout", config, broken)
    check = _check(report, "keyboard-well-cutout")
    assert not check.passed
    assert f"{well.wobble:.2f}" in check.message


# ── plate ──────────────────────────────────────────────────────────────


def test_plate_overhang_fails_when_the_plate_is_too_narrow(shipped, plate_model):
    config, _, _, budget, _, _ = shipped
    meta = plate_model.metadata
    narrow = dataclasses.replace(
        meta, width=meta.width - 1.0
    )
    model = _Model(narrow, list(plate_model.plate_outline))
    report = _report_for("keyboard-plate-overhang", config, budget, model=model)
    check = _check(report, "keyboard-plate-overhang")
    assert not check.passed
    assert f"{config.wall.thickness:.2f}" in check.message


def test_plate_border_fails_when_a_cutout_enters_it(shipped, plate_model):
    config, _, _, budget, _, _ = shipped
    meta = plate_model.metadata
    margins = list(meta.edge_margins)
    margins[2] = config.wall.thickness - 0.5
    model = _Model(
        dataclasses.replace(meta, edge_margins=tuple(margins)),
        list(plate_model.plate_outline),
    )
    report = _report_for("keyboard-plate-border", config, budget, model=model)
    check = _check(report, "keyboard-plate-border")
    assert not check.passed
    assert f"{margins[2]:.2f}" in check.message


def test_plate_seam_fails_when_it_cuts_a_switch_cutout(shipped, plate_model):
    from keyboard.geometry.seam import RowSeam

    config, _, _, budget, _, _ = shipped
    cut = plate_model.switch_cutouts[0]
    # A straight seam through the first cutout's centre: the bug the
    # row-jogging path exists to prevent (ADR-0014, issue #9).
    broken = dataclasses.replace(
        plate_model,
        seam=RowSeam(((cut.y - 1.0, cut.y + 1.0, cut.x),)),
    )
    report = _report_for("keyboard-plate-seam", config, budget, model=broken)
    check = _check(report, "keyboard-plate-seam")
    assert not check.passed
    assert "cuts cutout" in check.message


def test_plate_sections_fail_when_one_exceeds_the_build_volume(
    shipped, plate_model
):
    config, _, _, budget, _, _ = shipped
    oversize = [
        [(-150.0, -45.0), (150.0, -45.0), (150.0, 45.0), (-150.0, 45.0)]
    ] + [list(points) for points in plate_model.section_outlines[1:]]
    model = _Model(
        plate_model.metadata,
        list(plate_model.plate_outline),
        section_outlines=oversize,
    )
    report = _report_for("keyboard-plate-sections", config, budget, model=model)
    check = _check(report, "keyboard-plate-sections")
    assert not check.passed
    assert "300.00" in check.message


# ── mounts ─────────────────────────────────────────────────────────────


def test_mounts_stations_fail_when_a_station_is_missing(shipped):
    config, _, _, budget, mounts, _ = shipped
    broken = dataclasses.replace(mounts, mounts=mounts.mounts[:-1])
    report = _report_for(
        "keyboard-mounts-stations", config, budget, mounts=broken
    )
    check = _check(report, "keyboard-mounts-stations")
    assert not check.passed
    assert "7 stations" in check.message


def test_mounts_fit_fails_when_the_pattern_reports_a_reason(shipped):
    config, _, _, budget, mounts, _ = shipped
    broken = dataclasses.replace(
        mounts, failures=("front-outer-left: synthetic clash",)
    )
    report = _report_for("keyboard-mounts-fit", config, budget, mounts=broken)
    check = _check(report, "keyboard-mounts-fit")
    assert not check.passed
    assert "synthetic clash" in check.message


def test_mounts_parting_fails_when_a_boss_starts_below_the_plane(shipped):
    config, components, _, budget, mounts, _ = shipped
    parting = budget.chassis_joint.parting_z
    lowered = dataclasses.replace(
        mounts.mounts[0], boss_z0=parting - 1.0, boss_z1=parting + 4.0
    )
    broken = dataclasses.replace(
        mounts, mounts=(lowered,) + mounts.mounts[1:]
    )
    report = _report_for(
        "keyboard-mounts-parting",
        config,
        budget,
        mounts=broken,
        keyboard=components["keyboard"],
    )
    check = _check(report, "keyboard-mounts-parting")
    assert not check.passed
    assert f"{parting - 1.0:.2f}" in check.message


def test_mounts_parting_fails_when_floor_standoffs_come_back(shipped):
    config, components, _, budget, mounts, _ = shipped
    keyboard = components["keyboard"]

    def _standoffs():
        return [object()]

    original = keyboard.mounting_holes
    keyboard.mounting_holes = _standoffs
    try:
        report = _report_for(
            "keyboard-mounts-parting",
            config,
            budget,
            mounts=mounts,
            keyboard=keyboard,
        )
    finally:
        keyboard.mounting_holes = original
    check = _check(report, "keyboard-mounts-parting")
    assert not check.passed
    assert "1 floor standoffs" in check.message
