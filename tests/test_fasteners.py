"""Tests for the fastener library."""

from utilities.fasteners import (
    HEAT_INSERTS,
    SCREWS,
    SQUARE_NUTS,
    SquareNut,
    head,
    head_recess,
    heat_insert,
    screw,
    square_nut,
)


def test_screw_sizes():
    for size in ("M2", "M2.5", "M3"):
        s = screw(size)
        assert s.size == size
        assert s.clearance > 0
        assert head(size).diameter > 0


def test_screw_clearance():
    assert screw("M2").clearance == 2.2
    assert screw("M2.5").clearance == 2.7
    assert screw("M3").clearance == 3.2


def test_heat_insert():
    hi = heat_insert("M2.5")
    assert hi.size == "M2.5"
    assert hi.outside_diameter > 0
    assert hi.depth > 0


def test_square_nut():
    nut = square_nut("M4")
    assert isinstance(nut, SquareNut)
    assert nut is SQUARE_NUTS["M4"]
    # DIN 562 M4: 7.0 mm across the flats, 2.2 mm thick.
    assert nut.across_flats == 7.0
    assert nut.height == 2.2
    assert nut.pocket == nut.across_flats + nut.clearance
