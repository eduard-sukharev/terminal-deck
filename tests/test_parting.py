"""Parting plane height and Deck screw sizing (ADR 0003)."""

import pytest

from geometry.parting import deck_screw, parting_height
from utilities import fasteners
from utilities.config_loader import Parting, load_config


def test_height_is_the_fraction_of_the_front_wall():
    p = Parting(front_wall_fraction=0.5, min=6.0, max=30.0)
    assert parting_height(p, front_deck_level=20.0) == pytest.approx(10.0)


def test_height_clamps_to_min_and_max():
    p = Parting(front_wall_fraction=0.5, min=8.0, max=12.0)
    assert parting_height(p, front_deck_level=10.0) == 8.0   # 5 -> min
    assert parting_height(p, front_deck_level=40.0) == 12.0  # 20 -> max
    assert parting_height(p, front_deck_level=20.0) == 10.0  # unclamped


def test_parting_rejects_inverted_clamp_or_bad_fraction():
    with pytest.raises(ValueError):
        Parting(front_wall_fraction=0.5, min=12.0, max=8.0)
    with pytest.raises(ValueError):
        Parting(front_wall_fraction=1.5, min=1.0, max=8.0)


def test_default_config_has_a_parting_section():
    p = load_config("config/default.yaml").parting
    assert 0 < p.front_wall_fraction < 1
    assert 0 < p.min <= p.max


def test_deck_screw_length_comes_from_column_and_insert():
    screw = deck_screw("M3", grip=6.5)
    insert = fasteners.heat_insert("M3")
    # Never bottoms out in the insert, and reaches at least one thread diameter in.
    assert screw.length in fasteners.STANDARD_LENGTHS["M3"]
    assert 3.0 <= screw.engagement <= insert.depth
    assert screw.length == pytest.approx(screw.engagement + 6.5)


def test_deck_screw_picks_the_longest_stock_length_that_fits():
    # grip 6.5 + insert 4.0 = 10.5 -> stock 10.
    assert deck_screw("M3", grip=6.5).length == 10
    # grip 8 + 4 = 12 -> stock 12.
    assert deck_screw("M3", grip=8.0).length == 12


def test_deck_screw_with_no_fitting_stock_length_fails():
    with pytest.raises(ValueError):
        deck_screw("M3", grip=40.0)  # beyond the longest stock M3 screw
