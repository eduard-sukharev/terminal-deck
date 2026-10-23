"""Merged boss: classification by wall gap, bore-to-skin margin (ADR 0003)."""

import pytest

from geometry.merged_boss import (
    WallBounds, bore_center_limits, merge_walls, min_bore_gap,
)
from utilities.config_loader import MergedBoss, load_config

WALL = 2.0
BOUNDS = WallBounds(-100.0, 100.0, -50.0, 50.0)  # interior wall faces
RULE = MergedBoss(threshold_factor=2.0, bore_margin=0.5)


def test_a_boss_clear_of_every_wall_is_free():
    assert merge_walls(0.0, 0.0, 4.0, BOUNDS, WALL, RULE) == ()


def test_gap_below_two_walls_merges():
    # Outer edge 3.9 mm from the left wall face: < 2*wall = 4.
    assert merge_walls(-100.0 + 4.0 + 3.9, 0.0, 4.0, BOUNDS, WALL, RULE) == ("left",)


def test_gap_at_the_threshold_does_not_merge():
    assert merge_walls(-100.0 + 4.0 + 4.0, 0.0, 4.0, BOUNDS, WALL, RULE) == ()


def test_corner_boss_merges_into_both_walls():
    walls = merge_walls(100.0 - 5.0, -50.0 + 5.0, 4.0, BOUNDS, WALL, RULE)
    assert set(walls) == {"right", "rear"}


def test_all_four_walls_are_distinguished():
    assert merge_walls(0.0, 50.0 - 5.0, 4.0, BOUNDS, WALL, RULE) == ("front",)
    assert merge_walls(0.0, -50.0 + 5.0, 4.0, BOUNDS, WALL, RULE) == ("rear",)
    assert merge_walls(100.0 - 5.0, 0.0, 4.0, BOUNDS, WALL, RULE) == ("right",)


def test_bore_may_sit_closer_to_the_wall_than_a_free_boss():
    # Free boss: center no closer than outer radius (+ 2 wall gap to stay free).
    # Merged: bore edge only has to stay `margin` off the wall's inner face.
    gap = min_bore_gap(WALL, RULE)
    assert gap == pytest.approx(0.5)
    lo_x, hi_x, lo_y, hi_y = bore_center_limits(1.6, BOUNDS, RULE)
    assert lo_x == pytest.approx(-100.0 + 1.6 + 0.5)
    assert hi_x == pytest.approx(100.0 - 1.6 - 0.5)
    assert lo_y == pytest.approx(-50.0 + 1.6 + 0.5)
    assert hi_y == pytest.approx(50.0 - 1.6 - 0.5)


def test_wall_plus_half_a_millimetre_remains_to_the_outer_skin():
    # The rule as stated: bore edge to outer skin >= wall + 0.5.
    lo_x, *_ = bore_center_limits(1.6, BOUNDS, RULE)
    bore_edge = lo_x - 1.6
    outer_skin = BOUNDS.x0 - WALL
    assert bore_edge - outer_skin >= WALL + 0.5 - 1e-9


def test_default_config_has_the_rule():
    cfg = load_config("config/default.yaml")
    assert cfg.merged_boss.threshold_factor == 2.0
    assert cfg.merged_boss.bore_margin == 0.5
    assert cfg.edges.chamfer_factor == 0.5
    assert cfg.edges.bed_chamfer == 0.5
