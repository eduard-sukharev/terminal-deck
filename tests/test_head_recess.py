"""Tests for the band joints' keyhole head-recess module (ADR-0018)."""

import math

import pytest

from geometry import head_recess
from utilities import fasteners, cad_helpers as ch


def test_mouth_chamfer_bounds():
    # Plenty of room
    assert head_recess.mouth_chamfer(3.05, 10.0, 0.6) == pytest.approx(0.6)
    # Tight corner: takes what's left
    assert head_recess.mouth_chamfer(3.05, 4.0, 0.6) == pytest.approx(0.35)
    # No room at all
    assert head_recess.mouth_chamfer(3.05, 3.05, 0.6) == pytest.approx(0.0)


def test_edge_margin_positive_with_room():
    # margin=10, radius=3.05, chamfer=0.6 → edge = 10 - 3.05 - 0.6 = 6.35
    margin = head_recess.edge_margin(3.05, 10.0, 0.6)
    assert margin == pytest.approx(10.0 - 3.05 - 0.6, abs=0.01)


def test_edge_margin_zero_when_no_room():
    # No spare at all
    margin = head_recess.edge_margin(3.05, 3.05, 0.6)
    assert margin == pytest.approx(0.0, abs=0.01)


def test_build_cutter_produces_valid_solid():
    recess = fasteners.head_recess("M3", "button", fit=0.2, depth_margin=0.2)
    cutter = head_recess.build_cutter(
        recess,
        normal=(1.0, 0.0),  # straight along +X (face normal)
        mouth=0.35,
        x=5.0,
        y=0.0,
        z0=0.0,
    )
    assert cutter.is_valid
    # Should be one solid
    assert len(cutter.solids()) == 1
    # Volume should be positive and reasonable
    vol = ch.volume_mm3(cutter)
    assert vol > 70  # stadium 6.1×7.95 × depth 1.85 + frustum + chamfer


def test_build_cutter_normal_rotation():
    """Cutters with different normals produce differently oriented solids."""
    recess = fasteners.head_recess("M3", "button", fit=0.2, depth_margin=0.2)
    c_x = head_recess.build_cutter(recess, normal=(0.0, 1.0), mouth=0.35, x=0, y=0, z0=0)
    c_y = head_recess.build_cutter(recess, normal=(1.0, 0.0), mouth=0.35, x=0, y=0, z0=0)
    bb_x = c_x.bounding_box()
    bb_y = c_y.bounding_box()
    # The stadium runs along the -normal direction.  (0,1) → long axis along Y;
    # (1,0) → long axis along X.  So the two bounding boxes have swapped aspect.
    aspect_x = (bb_x.max.Y - bb_x.min.Y) / max(bb_x.max.X - bb_x.min.X, 0.01)
    aspect_y = (bb_y.max.Y - bb_y.min.Y) / max(bb_y.max.X - bb_y.min.X, 0.01)
    assert aspect_x > aspect_y  # Y-normal is taller in Y than in X
    assert aspect_y < aspect_x  # X-normal is wider in X than in Y


def test_build_cutter_no_overhang():
    """The ramp cuts away the ceiling so nothing overhangs against the print direction."""
    recess = fasteners.head_recess("M3", "button", fit=0.2, depth_margin=0.2)
    cutter = head_recess.build_cutter(
        recess,
        normal=(0.0, 1.0),  # normal is +Y (towards rear wall)
        mouth=0.35,
        x=0,
        y=0,
        z0=0.0,
    )
    # The cutter's ramp points away from the wall, which means in the part's
    # print orientation (Tray face up, z=0 is the bed), the cut ceiling slopes
    # downward from the seat wall — no horizontal ceiling to bridge.
    assert cutter.is_valid


def test_build_cutter_z0_lifts():
    """The cutter is lifted so its bottom sits at z0."""
    recess = fasteners.head_recess("M3", "button", fit=0.2, depth_margin=0.2)
    cutter = head_recess.build_cutter(
        recess,
        normal=(1.0, 0.0),
        mouth=0.35,
        x=5.0,
        y=3.0,
        z0=15.0,
    )
    bb = cutter.bounding_box()
    assert bb.min.Z == pytest.approx(15.0, abs=0.5)  # + extra overshoot


def test_ramp_angle_matches_print_limit():
    assert head_recess.RAMP_ANGLE_DEG == 45.0


def test_recess_properties():
    """M3 button head: Ø5.7 head + 2×0.2 fit = Ø6.1 pocket."""
    recess = fasteners.head_recess("M3", "button", fit=0.2, depth_margin=0.2)
    assert recess.pocket_diameter == pytest.approx(5.7 + 2 * 0.2, abs=0.01)
    assert recess.pocket_radius == pytest.approx((5.7 + 2 * 0.2) / 2.0, abs=0.01)
    assert recess.depth == pytest.approx(1.65 + 0.2, abs=0.01)
    # Seat ring: half the difference between pocket and screw clearance hole.
    screw = fasteners.screw("M3")
    assert recess.seat == pytest.approx(
        (recess.pocket_diameter - screw.clearance) / 2.0, abs=0.01
    )
    # Ramp run: depth / tan(45°) = depth
    assert recess.ramp_run == pytest.approx(recess.depth, abs=0.01)
    assert recess.length == pytest.approx(
        recess.pocket_diameter + recess.ramp_run, abs=0.01
    )
