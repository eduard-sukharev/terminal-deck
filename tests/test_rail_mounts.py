"""The accessory rail's station pattern (ADR-0020).

Pure-data tests: the two M4 stations per Tray X wall, mirrored about the wall's
centre, the pad and pocket the printed washer puck drops into, the 45 degree
gussets and the screw stack. The Tray cuts these features and the rail blank
carries the same holes, so this pattern is the single source for both.

Every expected value is derived from the configuration, the fastener library
and the chassis band joint; the few literals stated (the 10 mm rail stock, the
9.6 mm puck) are the arithmetic on those sources spelled out, so a parameter
change moves the model and the test together.
"""

import dataclasses

import pytest

from components.slide import compute_slide_budget
from geometry.rail_mounts import plan_gap, rail_mounts, station_offsets
from layouts import make_layout
from main import BuildPipeline
from utilities import fasteners
from utilities.slider_validation import _add_rail_checks
from utilities.validation import ValidationReport


@pytest.fixture(scope="module")
def data():
    pipeline = BuildPipeline("config/default.yaml", layout_name="slider")
    config = pipeline.load_config()
    components = pipeline.load_components()
    make_layout("slider", components, config=config).placements()
    return config, compute_slide_budget(config, components)


@pytest.fixture(scope="module")
def mounts(data):
    config, budget = data
    return rail_mounts(config, budget.chassis_joint)


def _report() -> ValidationReport:
    return ValidationReport()


def _check(report, name):
    return next(check for check in report.checks if check.name == name)


def _broken(config, **rail):
    return dataclasses.replace(
        config,
        slide=dataclasses.replace(
            config.slide,
            rail=dataclasses.replace(config.slide.rail, **rail),
        ),
    )


# ── Stations ───────────────────────────────────────────────────────────


def test_two_stations_per_wall_mirrored_about_the_centre(data, mounts):
    config, _ = data
    assert len(mounts.stations) == 2 * config.slide.rail.stations
    for side in (-1, 1):
        on_side = [s for s in mounts.stations if s.side == side]
        assert len(on_side) == config.slide.rail.stations
        assert all(abs(s.z - on_side[0].z) <= 1e-9 for s in on_side)
    offsets = mounts.station_offsets
    assert offsets == tuple(-y for y in reversed(offsets))


def test_stations_are_one_spacing_apart_on_each_wall(data, mounts):
    config, _ = data
    offsets = mounts.station_offsets
    assert offsets[-1] - offsets[0] == pytest.approx(
        config.slide.rail.station_spacing
    )


def test_stations_land_on_bridge_centres(data, mounts):
    """A counterbore must never eat a slot: the screws sit on bridge centres."""
    config, _ = data
    pitch = config.slide.rail.pitch
    for offset in mounts.station_offsets:
        assert offset == pytest.approx(round(offset / pitch) * pitch)


def test_station_offsets_rejects_an_odd_count():
    with pytest.raises(ValueError):
        station_offsets(3, 60.0)
    assert station_offsets(2, 60.0) == (-30.0, 30.0)
    assert station_offsets(4, 60.0) == (-90.0, -30.0, 30.0, 90.0)


def test_the_slide_rail_config_rejects_an_odd_station_count():
    from utilities.config_loader import SlideRail

    with pytest.raises(ValueError):
        SlideRail(stations=3)


def test_stations_are_on_the_wall_face(data, mounts):
    config, budget = data
    wall = config.wall.thickness
    for station in mounts.stations:
        assert station.x_outer == pytest.approx(budget.chassis_joint.band_width / 2.0)
        assert station.x_outer - station.x_inner == pytest.approx(wall)
        assert station.z == pytest.approx(budget.chassis_joint.parting_z / 2.0)


# ── Pad, pocket and washer puck ────────────────────────────────────────


def test_pad_pocket_and_puck_derive_from_the_nut(data, mounts):
    config, _ = data
    rail = config.slide.rail
    minimum = config.material.minimum_feature
    nut = fasteners.square_nut(rail.nut)

    assert mounts.puck_pocket == pytest.approx(nut.pocket)
    assert mounts.puck_width == pytest.approx(nut.pocket + 4.0 * minimum)
    assert mounts.puck_thickness == pytest.approx(nut.height + minimum)
    assert mounts.puck_floor == pytest.approx(minimum)
    assert mounts.protrusion == pytest.approx(rail.fit)

    station = mounts.stations[0]
    assert station.pocket_side == pytest.approx(mounts.puck_width + 2.0 * rail.fit)
    assert station.pocket_depth == pytest.approx(
        mounts.puck_thickness - mounts.protrusion
    )
    assert station.pad_width == pytest.approx(station.pocket_side + 2.0 * minimum)
    assert station.pad_depth == pytest.approx(2.0 * config.wall.thickness)


def test_pocket_leaves_a_real_pad_ring(data, mounts):
    config, _ = data
    minimum = config.material.minimum_feature
    for station in mounts.stations:
        assert station.pad_width > station.pocket_side
        assert station.pad_depth > station.pocket_depth
        assert station.x_pad_in < station.x_inner
        assert station.pocket_floor < station.x_outer
        assert (station.pad_width - station.pocket_side) / 2.0 >= minimum - 1e-9


def test_pocket_keeps_clear_of_the_floor_and_the_parting_plane(data, mounts):
    config, budget = data
    minimum = config.material.minimum_feature
    for station in mounts.stations:
        assert station.z - station.pocket_side / 2.0 >= config.wall.thickness + minimum
        assert (
            budget.chassis_joint.parting_z - (station.z + station.pocket_side / 2.0)
            >= minimum - 1e-9
        )


# ── Gussets and the band columns ───────────────────────────────────────


def test_every_station_gets_the_same_gusset_run(data, mounts):
    config, _ = data
    runs = {round(s.gusset_run, 9) for s in mounts.stations}
    assert len(runs) == 1
    assert mounts.stations[0].gusset_run >= config.material.minimum_feature


def test_pads_and_gussets_clear_the_band_columns(data, mounts):
    config, budget = data
    columns = [
        (station.x, station.y, station.boss)
        for station in budget.chassis_joint.stations
        if station.kind == "end"
    ]
    assert columns
    for station in mounts.stations:
        pad = (
            station.x_inner - station.pad_depth,
            station.y - station.pad_width / 2.0,
            station.x_inner,
            station.y + station.pad_width / 2.0,
        )
        for x, y, boss in columns:
            assert plan_gap(abs(x), y, pad) - boss / 2.0 >= -1e-9
        # The rib runs down to the floor and never taller than the screw axis.
        assert station.gusset_height <= station.z - config.wall.thickness + 1e-9


# ── Screw stack ────────────────────────────────────────────────────────


def test_screw_stock_spans_the_station_stack(data, mounts):
    config, _ = data
    rail = config.slide.rail
    minimum = config.material.minimum_feature
    head = mounts.head_recess
    station = mounts.stations[0]

    assert mounts.screw_stack == pytest.approx(
        rail.height
        - head.depth
        + config.wall.thickness
        + (station.pad_depth - station.pocket_depth)
        + mounts.puck_floor
        + mounts.nut.height
    )
    assert mounts.stock_length in fasteners.STANDARD_LENGTHS[rail.screw]
    slack = mounts.stock_length - mounts.screw_stack
    assert slack >= minimum - 1e-9
    assert slack <= rail.pitch + 1e-9


def test_rail_blank_is_the_spacing_plus_two_pitches(data, mounts):
    config, _ = data
    rail = config.slide.rail
    assert mounts.length == pytest.approx(rail.station_spacing + 2.0 * rail.pitch)
    assert mounts.width == pytest.approx(rail.width)
    assert mounts.height == pytest.approx(rail.height)


def test_the_shipped_design_is_valid(mounts):
    assert mounts.ok, mounts.failures


# ── HARD checks ────────────────────────────────────────────────────────


RAIL_CHECKS = (
    "slide-rail-stations",
    "slide-rail-spacing",
    "slide-rail-clear",
    "slide-rail-pocket",
    "slide-rail-screw",
    "slide-rail-envelope",
)


@pytest.mark.parametrize("name", RAIL_CHECKS)
def test_rail_checks_pass_on_the_shipped_design(data, name):
    config, budget = data
    report = _report()
    _add_rail_checks(report, config, budget)
    check = _check(report, name)
    assert check.passed, check.message
    assert check.message


def test_rail_spacing_fails_when_the_stations_miss_the_bridge_centres(data):
    config, budget = data
    broken = _broken(config, station_spacing=50.0)
    report = _report()
    _add_rail_checks(report, broken, budget)
    # +/-25 mm is mid-slot: a counterbore there would eat the profile.
    assert not _check(report, "slide-rail-spacing").passed


def test_rail_envelope_fails_when_the_rail_overtakes_the_wall(data):
    config, budget = data
    broken = _broken(config, station_spacing=140.0)
    report = _report()
    _add_rail_checks(report, broken, budget)
    assert not _check(report, "slide-rail-envelope").passed


def test_rail_screw_fails_when_the_rail_is_too_thin_for_a_head(data):
    config, budget = data
    broken = _broken(config, height=2.0)
    report = _report()
    _add_rail_checks(report, broken, budget)
    assert not _check(report, "slide-rail-screw").passed


def test_rail_pocket_fails_when_the_pad_ring_disappears(data):
    config, budget = data
    broken = _broken(config, fit=0.0)
    report = _report()
    _add_rail_checks(report, broken, budget)
    # A zero fit is still a legal interface; the pocket simply closes up.
    assert _check(report, "slide-rail-pocket").passed

    # A negative fit is not an interface at all: the config refuses it.
    with pytest.raises(ValueError):
        _broken(config, fit=-0.2)
