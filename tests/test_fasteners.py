"""Tests for the fastener library."""

from utilities.fasteners import screw, heat_insert, SCREWS, HEAT_INSERTS


def test_screw_sizes():
    for size in ("M2", "M2.5", "M3"):
        s = screw(size)
        assert s.size == size
        assert s.clearance > 0
        assert s.head_diameter > 0


def test_screw_clearance():
    assert screw("M2").clearance == 2.2
    assert screw("M2.5").clearance == 2.7
    assert screw("M3").clearance == 3.2


def test_heat_insert():
    hi = heat_insert("M2.5")
    assert hi.size == "M2.5"
    assert hi.outside_diameter > 0
    assert hi.depth > 0
