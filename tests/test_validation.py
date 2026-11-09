"""Tests for the validation suite."""

import pytest

from utilities.validation import (
    ValidationReport,
    check_collisions,
    check_floating_bosses,
    check_minimum_wall_thickness,
    check_screw_clearance,
    check_cable_bend,
    check_connectors_accessible,
    check_lid_clearance,
)
from layouts.base import Placement
from components.base import Component, BoundingBox, Hole, Connector


class _Box(Component):
    name = "Box"
    def __init__(self, w=10, d=10, h=10):
        self._w, self._d, self._h = w, d, h
    def size(self):
        return BoundingBox(self._w, self._d, self._h)


class _WithHoles(_Box):
    def mounting_holes(self):
        return [Hole(0, 0, 3.0)]


class _WithConnector(_Box):
    def connectors(self):
        return [Connector("USB", 0, 0, 0, (0, -1, 0), 8, 4, 6)]


class _Config:
    class wall: thickness = 2.5
    class material: minimum_feature = 0.6
    class clearance: screw = 0.6


def test_no_collisions_pass():
    a, b = _Box(), _Box()
    r = ValidationReport()
    check_collisions([Placement(a, 0, 0), Placement(b, 100, 0)], r)
    assert r.passed


def test_no_collisions_fail():
    a, b = _Box(), _Box()
    r = ValidationReport()
    check_collisions([Placement(a, 0, 0), Placement(b, 0, 0)], r)
    assert not r.passed


def test_no_floating_bosses_pass():
    r = ValidationReport()
    check_floating_bosses([Placement(_WithHoles(), 0, 0)], {"Box": 2.5}, r)
    assert r.passed


def test_no_floating_bosses_fail():
    r = ValidationReport()
    check_floating_bosses([Placement(_WithHoles(), 0, 0)], {}, r)
    assert not r.passed


def test_minimum_wall_thickness():
    r = ValidationReport()
    check_minimum_wall_thickness(_Config(), r)
    assert r.passed


def test_screw_clearance():
    r = ValidationReport()
    check_screw_clearance(_Config(), r)
    assert r.passed


def test_cable_bend_pass():
    r = ValidationReport()
    check_cable_bend(30.0, 15.0, r)
    assert r.passed


def test_cable_bend_fail():
    r = ValidationReport()
    check_cable_bend(5.0, 15.0, r)
    assert not r.passed


def test_connectors_accessible_pass():
    r = ValidationReport()
    check_connectors_accessible([], [], r)
    assert r.passed


def test_lid_clearance_pass():
    r = ValidationReport()
    check_lid_clearance(10.0, 15.0, r)
    assert r.passed


def test_lid_clearance_fail():
    r = ValidationReport()
    check_lid_clearance(20.0, 15.0, r)
    assert not r.passed


STEPPED3 = {"sections": 3, "x": 40.0, "style": "stepped", "step": 4.0, "steps": 6}
STRAIGHT0 = {"sections": 2, "x": 0.0, "style": "straight"}


# -- Seam clearance of structural features ------------------------------------

def _bands(**kw):
    from utilities.config_loader import Split
    from utilities.validation import seam_bands

    return seam_bands({k: Split(**v) for k, v in kw.items()}, {k: 100.0 for k in kw}, 2.0)


def _feature(x0, x1, y0=-5.0, y1=5.0, kind="rib", joins=None):
    from utilities.validation import Feature

    return Feature(kind, f"{kind}@{x0:g}", x0, x1, y0, y1, joins=joins)


def test_seam_band_is_seam_plus_steps_plus_one_wall():
    bands = _bands(tray=STEPPED3)
    xs = [(min(r[0] for r in rects), max(r[1] for r in rects)) for rects in bands.values()]
    assert sorted(xs) == [(-46.0, -38.0), (38.0, 46.0)]


@pytest.mark.parametrize("kind", ["rib", "boss", "standoff", "column", "cradle", "vent", "lug"])
def test_every_structural_kind_is_caught_in_a_seam_band(kind):
    from utilities.validation import check_seam_clearance

    r = ValidationReport()
    check_seam_clearance(_bands(tray=STEPPED3), [_feature(-41.0, -39.0, kind=kind)], r)
    assert [c.name for c in r.failures] == ["seams-clear-of-features"]


def test_feature_clear_of_the_band_passes():
    from utilities.validation import check_seam_clearance

    r = ValidationReport()
    # Band is -46..-38 (Seam -44..-40 plus a wall each side).
    check_seam_clearance(_bands(tray=STEPPED3), [_feature(-48.5, -46.5), _feature(-20, -19)], r)
    assert r.passed, r.summary()


def test_one_wall_margin_is_enforced():
    from utilities.validation import check_seam_clearance

    r = ValidationReport()
    # Seam segment at x=-44 (y -33..-17); its band runs to -46, a wall beyond.
    check_seam_clearance(_bands(tray=STEPPED3), [_feature(-47.0, -45.5, y0=-25.0, y1=-24.0)], r)
    assert not r.passed
    ok = ValidationReport()
    check_seam_clearance(_bands(tray=STEPPED3), [_feature(-48.0, -46.5, y0=-25.0, y1=-24.0)], ok)
    assert ok.passed, ok.summary()


def test_step_jog_faces_are_inside_the_band():
    from utilities.validation import check_seam_clearance

    # Seam segment x=-44 spans y -33.3..-16.7 (band -46..-42); the jog back to
    # x=-40 at y=-16.7 sweeps -44..-40. A feature at x=-41, only ever near the
    # jog, is caught there but not mid-segment.
    on_jog, mid = ValidationReport(), ValidationReport()
    check_seam_clearance(_bands(tray=STEPPED3), [_feature(-41.5, -40.5, y0=-18.0, y1=-17.2)], on_jog)
    check_seam_clearance(_bands(tray=STEPPED3), [_feature(-41.5, -40.5, y0=-26.0, y1=-25.0)], mid)
    assert not on_jog.passed
    assert mid.passed, mid.summary()


def test_a_lug_may_straddle_its_own_seam_but_not_another():
    from utilities.validation import check_seam_clearance

    bands = _bands(tray=STEPPED3)
    own = sorted(bands)[0]
    other = sorted(bands)[1]
    lug_on_left = _feature(-45.0, -37.0, kind="lug", joins=own)
    ok, bad = ValidationReport(), ValidationReport()
    check_seam_clearance(bands, [lug_on_left], ok)
    check_seam_clearance(bands, [_feature(-45.0, -37.0, kind="lug", joins=other)], bad)
    assert ok.passed, ok.summary()
    assert not bad.passed


# -- Deck screws and feet -------------------------------------------------------

def test_deck_screw_check_reports_the_stock_length():
    from utilities.validation import check_deck_screw

    r = ValidationReport()
    check_deck_screw("M3", grip=8.5, report=r)
    assert r.passed and "M3x12" in r.checks[0].message
    bad = ValidationReport()
    check_deck_screw("M3", grip=40.0, report=bad)
    assert not bad.passed


def test_a_feature_is_only_crossed_by_its_own_parts_seams():
    from utilities.validation import Feature, check_seam_clearance

    bands = {"tray:0": [(-2.0, 2.0, -50.0, 50.0)], "deck:0": [(8.0, 12.0, -50.0, 50.0)]}
    on_tray_seam = Feature("boss", "a", -1.0, 1.0, 0.0, 1.0, part="deck")
    on_deck_seam = Feature("boss", "b", 9.0, 11.0, 0.0, 1.0, part="deck")
    on_both = Feature("column", "c", -1.0, 1.0, 0.0, 1.0)
    ok, bad, both = ValidationReport(), ValidationReport(), ValidationReport()
    check_seam_clearance(bands, [on_tray_seam], ok)       # a Deck feature under the Tray Seam
    check_seam_clearance(bands, [on_deck_seam], bad)
    check_seam_clearance(bands, [on_both], both)
    assert ok.passed and not bad.passed and not both.passed


# -- Keyboard plate Seam screws ---------------------------------------------------

PLATE_SEAM = [(-40.0, -20.0, 0.0), (-20.0, 0.0, 4.76), (0.0, 20.0, -4.76), (20.0, 40.0, -50.6)]
UNIT = 19.05


def _plate_holes(**over):
    holes = {
        "edge": [(-90.0, -19.0), (80.0, -19.0), (-80.0, 19.0), (95.0, 19.0)],
        "left_lower": (-18.0, -19.0), "right_lower": (7.0, -19.0),
        "left_upper": (-52.7, 19.0), "right_upper": (-2.7, 19.0),
    }
    holes.update(over)
    return holes["edge"] + [holes[k] for k in ("left_lower", "right_lower", "left_upper", "right_upper") if holes[k]]


def test_plate_seam_screws_pass_when_every_section_has_an_upper_and_a_lower():
    from utilities.validation import check_plate_seam_screws

    r = ValidationReport()
    check_plate_seam_screws(_plate_holes(), PLATE_SEAM, UNIT, r, expected_total=8)
    assert r.passed, r.summary()


def test_plate_seam_screw_more_than_a_unit_from_the_seam_fails():
    from utilities.validation import check_plate_seam_screws

    r = ValidationReport()
    check_plate_seam_screws(_plate_holes(left_lower=(-26.0, -19.0)), PLATE_SEAM, UNIT, r)
    assert [c.name for c in r.failures] == ["plate-seam-screws"]
    assert "left" in r.failures[0].message and "lower" in r.failures[0].message


def test_a_plate_section_missing_a_seam_screw_fails():
    from utilities.validation import check_plate_seam_screws

    r = ValidationReport()
    check_plate_seam_screws(_plate_holes(right_upper=None), PLATE_SEAM, UNIT, r)
    assert not r.passed and "right upper" in r.failures[0].message


def test_plate_needs_the_expected_total_of_screws():
    from utilities.validation import check_plate_seam_screws

    r = ValidationReport()
    check_plate_seam_screws(_plate_holes(right_upper=None), PLATE_SEAM, UNIT, r, expected_total=8)
    assert not r.passed
