"""Tests for the 8-check validation suite."""

from utilities.validation import (
    ValidationReport,
    check_collisions,
    check_floating_bosses,
    check_minimum_wall_thickness,
    check_screw_clearance,
    check_cable_bend,
    check_connectors_accessible,
    check_lid_clearance,
    check_hinge_clearance,
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


def test_hinge_clearance_pass():
    r = ValidationReport()
    check_hinge_clearance(5.0, 10.0, r)
    assert r.passed


def test_hinge_clearance_fail():
    r = ValidationReport()
    check_hinge_clearance(5.0, 3.0, r)
    assert not r.passed
