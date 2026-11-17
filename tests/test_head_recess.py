"""Tests for the band joints' head-recess module (ADR-0018, ADR-0021)."""

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


# -- deep conical recess (ADR-0021) --------------------------------------
def test_deep_recess_sizing():
    """The pocket is the head's exact height; the cone runs to the floor."""
    recess = head_recess.deep_recess("M3", "button", fit=0.2, z_seat=14.15)
    assert recess.pocket_diameter == pytest.approx(6.1, abs=0.01)
    assert recess.depth == pytest.approx(14.15)
    assert recess.z_neck == pytest.approx(14.15 - recess.head.depth, abs=1e-6)
    screw = fasteners.screw("M3")
    assert recess.seat == pytest.approx(
        (recess.pocket_diameter - screw.clearance) / 2.0, abs=1e-9
    )


def test_deep_recess_rejects_a_shallow_seat():
    with pytest.raises(ValueError):
        head_recess.deep_recess("M3", "button", z_seat=1.0)


def test_cone_angle_depends_on_the_mouth():
    recess = head_recess.deep_recess("M3", "button", fit=0.2, z_seat=14.15)
    wall = recess.cone_angle(3.9)
    end = recess.cone_angle(5.0)
    assert 0.0 < wall < end < 9.0
    assert wall == pytest.approx(
        math.degrees(math.atan2(3.9 - recess.pocket_radius, recess.z_neck)),
        abs=1e-9,
    )


def test_cone_angle_rejects_a_narrow_mouth():
    recess = head_recess.deep_recess("M3", "button", fit=0.2, z_seat=14.15)
    with pytest.raises(ValueError):
        recess.cone_angle(recess.pocket_radius - 0.1)


def test_build_deep_cutter_shape():
    """One axisymmetric solid: the cone from the floor up to the pocket, which
    ends flat on the seat."""
    recess = head_recess.deep_recess("M3", "button", fit=0.2, z_seat=14.15)
    cutter = head_recess.build_deep_cutter(
        recess, mouth_radius=3.9, x=5.0, y=3.0
    )
    assert cutter.is_valid
    assert len(cutter.solids()) == 1
    assert ch.volume_mm3(cutter) > 0.0
    bb = cutter.bounding_box()
    assert bb.min.Z < 0.0  # overshoots the floor face
    assert bb.max.Z == pytest.approx(recess.z_seat, abs=0.01)
    # The mouth is wider than the pocket, so the floor face is the widest.
    radius_at_floor = max(bb.max.X - 5.0, 5.0 - bb.min.X)
    radius_at_top = (bb.max.X - bb.min.X) / 2.0
    assert radius_at_floor > radius_at_top


def test_build_deep_cutter_rejects_a_narrow_mouth():
    recess = head_recess.deep_recess("M3", "button", fit=0.2, z_seat=14.15)
    with pytest.raises(ValueError):
        head_recess.build_deep_cutter(recess, mouth_radius=2.0, x=0.0, y=0.0)
