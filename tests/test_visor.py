"""Visor: fills the wedge between a flat Lid underside and the sloped Deck."""

import math

from geometry.visor import VisorProfile
from utilities.validation import ValidationReport, check_visor_flush

REAR, KNEE, FRONT = -60.0, -20.0, 60.0
SLOPE = math.tan(math.radians(6.0))


def deck_top(y):
    """Deck top: flat behind the knee, rising toward the rear in front of it."""
    return 30.0 + (FRONT - max(y, KNEE)) * SLOPE


def profile():
    return VisorProfile(((REAR, 0.0), (KNEE, 0.0), (FRONT, deck_top(KNEE) - deck_top(FRONT))))


def test_height_interpolates_and_clamps():
    p = profile()
    assert p.height_at(REAR) == 0.0 and p.height_at(KNEE) == 0.0
    assert math.isclose(p.height_at(FRONT), 80.0 * SLOPE)
    assert math.isclose(p.height_at(20.0), 40.0 * SLOPE)
    assert p.height_at(FRONT + 5) == p.height_at(FRONT)
    assert p.max_height == p.height_at(FRONT)


def test_flush_check_passes_for_matching_profile():
    r = ValidationReport()
    p = profile()
    check_visor_flush(deck_top, p.height_at, REAR, FRONT, r)
    assert r.passed and len(r.checks) == 3


def test_flush_check_fails_for_flat_profile():
    r = ValidationReport()
    check_visor_flush(deck_top, lambda y: 0.0, REAR, FRONT, r)
    assert [c.name for c in r.failures] == ["visor-closes-flush"]


def test_flush_check_fails_when_visor_nonzero_at_hinge():
    r = ValidationReport()
    check_visor_flush(deck_top, lambda y: 1.0 + (30.0 + 1.0 - deck_top(y)) * 0, REAR, FRONT, r)
    assert "visor-zero-at-hinge" in [c.name for c in r.failures]


def test_goal_metric_is_reported_not_failed():
    r = ValidationReport()
    r.goals["closed thickness (mm)"] = 42.0
    assert r.passed and "[goal] closed thickness (mm): 42.00" in r.summary()
