"""Purchased Torque hinges described in config (ADR 0007) and the Cable guard."""

import math

import pytest

from components.cable_guard import CableGuard
from components.hinge import Hinge, TorqueHinge
from utilities import cad_helpers
from utilities.config_loader import load_config

REAR_Y = -60.0


def cfg():
    return load_config("config/default.yaml")


def guard(x=-48.5):
    c = cfg()
    return CableGuard(c.cable_guard, wall_thickness=c.wall_thickness, x=x, travel=c.hinge.travel)


def hinge(with_guard=True):
    c = cfg()
    return Hinge(c.hinge, wall_thickness=c.wall_thickness, guard=guard() if with_guard else None)


# -- the part, as data --------------------------------------------------------


def test_reference_part_parses_from_config():
    part = TorqueHinge.from_config(cfg().hinge.part)
    assert part.barrel_diameter == 16.0
    assert [h.u for h in part.leaves["base"].holes] == [14.0, 27.0]
    assert set(part.leaves) == {"base", "lid"}


def test_hole_outside_its_leaf_is_rejected():
    data = dict(cfg().hinge.part)
    leaves = {k: dict(v) for k, v in data["leaves"].items()}
    leaves["base"]["holes"] = [[40.0, 0.0, 4.3]]
    data["leaves"] = leaves
    with pytest.raises(ValueError, match="outside"):
        TorqueHinge.from_config(data)


# -- placement ----------------------------------------------------------------


def test_left_hinge_mirrors_the_right_about_the_centerline():
    h = hinge()
    left, right = h.centers()
    assert left == -right == -cfg().hinge.x
    lh, rh = (sorted(h.holes("base", REAR_Y, side)) for side in ("left", "right"))
    assert [(-x, y) for x, y, _ in lh] == pytest.approx(sorted((x, y) for x, y, _ in rh))


def test_holes_mirror_their_v_offset_on_the_left():
    data = dict(cfg().hinge.part)
    leaves = {k: dict(v) for k, v in data["leaves"].items()}
    leaves["base"]["holes"] = [[14.0, 3.0, 4.3]]
    data["leaves"] = leaves
    c = cfg()
    from dataclasses import replace
    h = Hinge(replace(c.hinge, part=data), wall_thickness=c.wall_thickness)
    (xl, _, _), = h.holes("base", REAR_Y, "left")
    (xr, _, _), = h.holes("base", REAR_Y, "right")
    assert xr == pytest.approx(c.hinge.x + 3.0) and xl == pytest.approx(-xr)


def test_axis_sets_back_past_the_barrel_and_the_guard():
    h = hinge()
    clear = cfg().hinge.swing_clearance
    assert h.setback == pytest.approx(
        max(h.part.barrel_diameter / 2.0, h.guard.outer_radius) + clear
    )
    assert hinge(with_guard=False).setback == pytest.approx(h.part.barrel_diameter / 2.0 + clear)


def test_leaf_runs_from_the_set_back_axis_into_the_case():
    h = hinge()
    x0, x1, y0, y1 = h.leaf_rect("base", REAR_Y, "right")
    leaf = h.part.leaves["base"]
    assert (x1 - x0) == pytest.approx(leaf.width)
    assert y0 == pytest.approx(REAR_Y - h.setback + leaf.start)
    assert y1 - y0 == pytest.approx(leaf.length)


def test_leaf_z_span_below_the_axis_for_base_above_for_lid():
    h = hinge()
    t = h.part.leaf_thickness
    off = h.part.leaves["base"].offset
    assert h.leaf_z("base") == pytest.approx((-off - t, -off))
    off = h.part.leaves["lid"].offset
    assert h.leaf_z("lid") == pytest.approx((off, off + t))


# -- sweep --------------------------------------------------------------------


def test_lid_swings_clear_of_the_base_with_the_axis_set_back():
    h = hinge()
    assert h.sweep_hits(lid_depth=120.0, lid_height=15.8) == []


def test_lid_hits_the_base_with_the_axis_on_the_rear_face():
    h = hinge()
    hits = h.sweep_hits(lid_depth=120.0, lid_height=15.8, setback=0.0, travel=196.0)
    assert hits


# -- Cable guard --------------------------------------------------------------


def test_guard_radii_nest_core_coil_deck_ring_lid_ring():
    g = guard()
    c = cfg().cable_guard
    wall = cfg().wall_thickness
    assert g.core_radius == c.min_bend_radius
    coil = g.core_radius + c.turns * c.fpc_thickness + c.fit
    assert g.deck_ring == pytest.approx((coil, coil + wall))
    assert g.lid_ring == pytest.approx((coil + wall + c.fit, coil + 2 * wall + c.fit))
    assert g.outer_radius == g.lid_ring[1]


def test_guard_sectors_never_cover_an_entry_through_the_travel():
    g = guard()
    e, travel = cfg().cable_guard.entry_angle, cfg().hinge.travel
    d0, d1 = g.deck_sector()
    l0, l1 = g.lid_sector()
    # Deck ring (static) stays out of the Lid entry's sweep and the Base entry.
    assert d0 >= e + travel - 1e-9 and d1 <= 360.0 - e + 1e-9
    # Lid ring (turns with the Lid) never reaches the Base entry.
    assert l0 >= e - 1e-9 and l1 + travel <= 360.0 - e + 1e-9


def test_guard_span_centres_on_its_x_with_discs_outside_the_lid_ring():
    g = guard(x=-48.5)
    c = cfg().cable_guard
    wall = cfg().wall_thickness
    x0, x1 = g.span()
    assert (x0 + x1) / 2.0 == pytest.approx(-48.5)
    assert x1 - x0 == pytest.approx(c.fpc_width + 2 * c.fit + 2 * c.fit + 2 * wall)
    r0, r1 = g.lid_ring_span()
    assert r1 - r0 == pytest.approx(c.fpc_width + 2 * c.fit)


def test_guard_and_hinges_do_not_overlap_in_x():
    h = hinge()
    g = h.guard
    gx0, gx1 = g.span()
    for side in ("left", "right"):
        x0, x1, _, _ = h.leaf_rect("base", REAR_Y, side)
        assert gx1 <= x0 or x1 <= gx0


# -- CAD ----------------------------------------------------------------------


@pytest.mark.skipif(not cad_helpers.cad_available(), reason="build123d not installed")
def test_hinge_body_is_one_solid_per_instance():
    h = hinge()
    body = h.build_part("right")
    assert cad_helpers.solid_count(body) == 1
    x, _, _ = cad_helpers.bounding_box_mm(body)
    assert x == pytest.approx(h.part.barrel_length, rel=1e-3)


@pytest.mark.skipif(not cad_helpers.cad_available(), reason="build123d not installed")
def test_pad_carries_an_insert_bore_per_hole():
    h = hinge()
    pad = h.build_pad("base", "right", support=0.0)
    insert = h.insert()
    off = h.part.leaves["base"].offset
    x0, x1, _, _ = h.leaf_rect("base", 0.0, "right")
    # Pad volume is the slab less one bore per hole.
    w = h.part.leaves["base"].width + 2 * h.wall_thickness
    assert cad_helpers.solid_count(pad) == 1
    assert cad_helpers.volume_mm3(pad) < w * (h.part.leaves["base"].length + 2 * h.wall_thickness) * off


def test_guard_rejects_an_entry_angle_outside_0_to_90():
    from dataclasses import replace
    c = cfg()
    with pytest.raises(ValueError, match="entry_angle"):
        CableGuard(replace(c.cable_guard, entry_angle=90.0), wall_thickness=2.0, x=0.0, travel=90.0)
