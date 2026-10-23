"""Nearest free spot search."""

import math

from geometry.spot_search import drop_close, nearest_free_spot

BOUNDS = (-50.0, -50.0, 50.0, 50.0)


def test_a_free_target_is_returned_as_is():
    assert nearest_free_spot((3.0, 4.0), lambda x, y: False, BOUNDS) == (3.0, 4.0)


def test_a_blocked_target_moves_to_the_nearest_free_point():
    blocked = lambda x, y: math.hypot(x, y) < 10.0
    x, y = nearest_free_spot((0.0, 0.0), blocked, BOUNDS)
    assert 10.0 <= math.hypot(x, y) < 11.5


def test_the_search_finds_gaps_off_to_the_side():
    # A wall across the straight path to the origin, with a gap to the east.
    blocked = lambda x, y: -30 < y < 30 and x < 20
    x, y = nearest_free_spot((-40.0, 0.0), blocked, BOUNDS)
    assert not blocked(x, y)


def test_bounds_are_respected_even_for_the_target():
    assert nearest_free_spot((0.0, 0.0), lambda x, y: False, (10.0, 10.0, 20.0, 20.0)) is not None
    x, y = nearest_free_spot((0.0, 0.0), lambda x, y: False, (10.0, 10.0, 20.0, 20.0))
    assert 10.0 <= x <= 20.0 and 10.0 <= y <= 20.0


def test_nothing_free_returns_none():
    assert nearest_free_spot((0.0, 0.0), lambda x, y: True, BOUNDS) is None


def test_close_spots_are_dropped_in_order():
    spots = [(0.0, 0.0), (1.0, 0.0), (10.0, 0.0), (10.5, 0.5)]
    assert drop_close(spots, 5.0) == [(0.0, 0.0), (10.0, 0.0)]
