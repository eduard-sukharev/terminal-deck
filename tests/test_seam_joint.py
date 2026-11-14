"""Glued filament pins across a Seam (ADR 0003, 0006).

The primitive is two parallel printed fins with a slot between them: the pin is
a length of filament glued into the slot, so there is no bore, no sleeve and no
lug. These tests own the profile's numbers, the slot fit, the chamfer, and the
fact that every Section keeps its half of every fin.
"""

import pytest

from utilities import cad_helpers

pytestmark = pytest.mark.skipif(
    not cad_helpers.cad_available(), reason="build123d not available"
)

from geometry.seam_joint import (  # noqa: E402
    SINK,
    add_pins,
    fin_profile,
    fins,
    pocket_rect,
    pocket_z,
    site_on_straight_run,
)
from geometry.split import split_sections  # noqa: E402
from utilities.config_loader import Seam, SeamPin  # noqa: E402

PIN = SeamPin()

WIDTH, DEPTH, HEIGHT, WALL = 120.0, 80.0, 20.0, 2.0
FLOOR_TOP = -HEIGHT / 2.0 + WALL
SITES = (-20.0, 10.0)


def _tray():
    outer = cad_helpers.box_centered(WIDTH, DEPTH, HEIGHT)
    cavity = cad_helpers.translate(
        cad_helpers.box_centered(WIDTH - 2 * WALL, DEPTH - 2 * WALL, HEIGHT),
        0, 0, WALL,
    )
    return cad_helpers.cut(outer, cavity)


def _material(shape, x, y, z, size=0.2):
    probe = cad_helpers.translate(cad_helpers.box_centered(size, size, size), x, y, z)
    return cad_helpers.volume_mm3(cad_helpers.intersect(shape, probe)) > 1e-6


# -- the profile -------------------------------------------------------


def test_the_slot_is_the_configured_gap_between_two_fins():
    low = fin_profile(PIN, -1)
    high = fin_profile(PIN, +1)
    # The slot face (inner wall) is at gap/2.
    assert min(y for y, _ in high) == pytest.approx(PIN.gap / 2.0)
    # The outermost point of the profile is at the base where chamfer flares out.
    outer = PIN.gap / 2.0 + PIN.fin
    assert max(y for y, _ in high) == pytest.approx(outer + PIN.chamfer)
    assert min(y for y, _ in low) == pytest.approx(-(outer + PIN.chamfer))
    # The slot itself is empty by construction: no profile vertex inside it.
    for y, _ in low + high:
        assert abs(y) >= PIN.gap / 2.0 - 1e-9


def test_the_fins_are_sunk_into_the_substrate_and_reach_the_configured_height():
    for side in (-1, 1):
        zs = [z for _, z in fin_profile(PIN, side)]
        assert min(zs) == pytest.approx(-SINK)
        assert max(zs) == pytest.approx(PIN.height)


def test_only_the_base_edge_is_chamfered():
    """The slot face is square all the way; the wall thickness is constant.
    The chamfer is a triangular expansion at the base -- outward into the floor.
    """
    for side in (-1, 1):
        profile = fin_profile(PIN, side)
        inner = side * PIN.gap / 2.0
        outer = side * (PIN.gap / 2.0 + PIN.fin)
        # The slot face (inner wall) runs square from the substrate to the free end.
        assert (inner, -SINK) in profile
        assert (inner, PIN.height) in profile
        # The outer wall maintains constant thickness ``fin`` from top to bottom.
        assert (outer, PIN.height) in profile
        assert (outer, -SINK + PIN.chamfer) in profile
        # The chamfer extends outward at the substrate surface.
        assert (outer + side * PIN.chamfer, -SINK) in profile
        # The 45° chamfer diagonal: substrate → base of fin wall.
        assert (outer + side * PIN.chamfer, -SINK) in profile
        assert (outer, -SINK + PIN.chamfer) in profile


def test_top_corner_is_square():
    """The outer top edge is not chamfered; the wall thickness is constant."""
    outer = PIN.gap / 2.0 + PIN.fin
    prof = fin_profile(PIN, +1)
    # The top edge runs from (outer, height) → (inner, height) — full wall width.
    assert (outer, PIN.height) in prof
    # A top chamfer would remove this point.
    assert (outer, PIN.height - PIN.chamfer) not in prof


def test_a_zero_chamfer_keeps_the_fin_rectangular():
    square = fin_profile(SeamPin(chamfer=0.0), +1)
    # With no chamfer the profile is a 4-corner rectangle.
    assert len(square) == 4
    assert (PIN.gap / 2.0 + PIN.fin, PIN.height) in square


def test_the_chamfer_extends_outward_at_the_base():
    """Chamfer is a triangular flare at the substrate, not a cut into the wall."""
    for side in (-1, 1):
        profile = fin_profile(PIN, side)
        outer = side * (PIN.gap / 2.0 + PIN.fin)
        # The outermost point at substrate (z = -SINK) extends beyond the wall edge.
        substrate_ys = [y for y, z in profile if abs(z - (-SINK)) < 1e-9]
        # For side=-1 the max y is the inner wall; for side=+1 the max y is the outer.
        # Take the point with the largest absolute y.
        extreme = max(substrate_ys, key=abs)
        assert extreme == pytest.approx(outer + side * PIN.chamfer)


def test_the_pin_must_leave_room_for_glue():
    with pytest.raises(ValueError):
        SeamPin(gap=1.75)


def test_the_chamfer_must_not_exceed_the_height():
    with pytest.raises(ValueError):
        SeamPin(fin=1.4, height=1.0, chamfer=1.0)


# -- the pocket --------------------------------------------------------


def test_the_pocket_straddles_the_seam_with_equal_engagement():
    x0, x1, y0, y1 = pocket_rect(PIN, 10.0, -20.0)
    assert x0 == pytest.approx(10.0 - PIN.engagement)
    assert x1 == pytest.approx(10.0 + PIN.engagement)
    assert y0 == pytest.approx(-20.0 - PIN.pocket_width / 2.0)
    assert y1 == pytest.approx(-20.0 + PIN.pocket_width / 2.0)


def test_the_pocket_reaches_into_the_substrate_from_either_side():
    up = pocket_z(PIN, 2.0, upward=True)
    down = pocket_z(PIN, 30.0, upward=False)
    assert up == pytest.approx((2.0 - SINK, 2.0 + PIN.height))
    assert down == pytest.approx((30.0 - PIN.height, 30.0 + SINK))


def test_a_site_on_a_diagonal_is_not_a_straight_run():
    seam = Seam(((0.0, 0.5, 10.0), (8.5, 40.0, 18.0)))
    # The middle of the second run is fine; the diagonal is not.
    assert site_on_straight_run(seam, 40.0, 20.0, PIN)
    assert not site_on_straight_run(seam, 40.0, 4.0, PIN)


def test_a_site_too_close_to_the_run_end_is_rejected():
    seam = Seam.straight(0.0)
    assert site_on_straight_run(seam, DEPTH, 0.0, PIN)
    # The pocket needs half its width of straight run on each side.
    assert not site_on_straight_run(
        seam, DEPTH, DEPTH / 2.0 - PIN.pocket_width / 2.0 + 0.1, PIN
    )


# -- the built fins ----------------------------------------------------


def test_the_fins_stand_on_the_floor_and_leave_the_slot_empty():
    seam = Seam.straight(0.0)
    body = add_pins(_tray(), seam, PIN, SITES, FLOOR_TOP, upward=True)
    z = FLOOR_TOP + PIN.height / 2.0
    for y in SITES:
        # Slot center is empty; fin walls are at ±(gap/2 + fin/2).
        assert not _material(body, 0.0, y, z)
        assert _material(body, 0.0, y + PIN.gap / 2.0 + PIN.fin / 2.0, z)
        assert _material(body, 0.0, y - PIN.gap / 2.0 - PIN.fin / 2.0, z)


def test_the_filament_fits_the_slot():
    seam = Seam.straight(0.0)
    body = add_pins(_tray(), seam, PIN, SITES, FLOOR_TOP, upward=True)
    z = FLOOR_TOP + PIN.height / 2.0
    rod = cad_helpers.rotate_y(
        cad_helpers.cylinder_centered(PIN.pin, PIN.length - 1.0), 90
    )
    for y in SITES:
        probe = cad_helpers.translate(rod, 0.0, y, z)
        assert cad_helpers.volume_mm3(
            cad_helpers.intersect(body, probe)
        ) == pytest.approx(0.0, abs=1e-6)


def test_each_section_keeps_its_half_of_every_fin():
    seam = Seam.straight(0.0)
    plain = _tray()
    jointed = add_pins(plain, seam, PIN, SITES, FLOOR_TOP, upward=True)
    plain_left, plain_right = split_sections(plain, [seam], DEPTH)
    left, right = split_sections(jointed, [seam], DEPTH)
    assert left.volume > plain_left.volume
    assert right.volume > plain_right.volume
    # Half of every fin on each side of the Seam.
    z = FLOOR_TOP + PIN.height / 2.0
    half = PIN.engagement - 0.5
    for y in SITES:
        fin_y = y + PIN.gap / 2.0 + PIN.fin / 2.0
        assert _material(left, -half, fin_y, z)
        assert _material(right, +half, fin_y, z)
        assert not _material(left, +half, fin_y, z)
        assert not _material(right, -half, fin_y, z)


def test_no_sites_leaves_the_part_untouched():
    body = _tray()
    assert add_pins(body, Seam.straight(0.0), PIN, (), FLOOR_TOP, True) is body


def test_fins_hang_from_a_ceiling():
    slab = cad_helpers.translate(cad_helpers.box_centered(60.0, 40.0, 4.0), 0.0, 0.0, 10.0)
    ceiling = 8.0
    seam = Seam.straight(0.0)
    body = add_pins(slab, seam, PIN, (-10.0,), ceiling, upward=False)
    z = ceiling - PIN.height / 2.0
    fin_y = -10.0 + PIN.gap / 2.0 + PIN.fin / 2.0
    assert _material(body, 0.0, fin_y, z)
    assert not _material(body, 0.0, -10.0, z)
    # The fins reach *down* from the ceiling, not up into the slab.
    assert _material(body, 0.0, fin_y, ceiling - 1.0)
    assert not _material(body, 0.0, fin_y, ceiling - PIN.height - 1.0)
