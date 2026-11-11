"""First-generation slider case geometry (issue #3).

The case must be a closed solid inside the derived budget, split into two
printable Sections that add back to the whole, with the guide hardware in the
right place. These are shape-level assertions, not a golden-master volume.
"""

import pytest

from case.chassis import Chassis
from case.screen_lid import ScreenLid
from case.slider_frame import SliderFrame
from components.slide import (
    build_bearing_clamp,
    build_guide_rod,
    build_linear_bearing,
    build_rod_clamp,
    compute_slide_budget,
)
from layouts import make_layout
from main import BuildPipeline
from utilities import cad_helpers as ch
from utilities.fasteners import screw as screw_spec
from utilities.slider_validation import BUILD_VOLUME


@pytest.fixture(scope="module")
def data():
    pipeline = BuildPipeline("config/default.yaml", layout_name="slider")
    config = pipeline.load_config()
    components = pipeline.load_components()
    placements = make_layout("slider", components, config=config).placements()
    budget = compute_slide_budget(config, components)
    frame = SliderFrame.from_data(config, budget, components, placements)
    return config, components, budget, frame


@pytest.fixture(scope="module")
def solids(data):
    config, _, _, frame = data
    chassis = Chassis(config, frame).build()
    lid = ScreenLid(config, frame).build()
    return chassis, lid


@pytest.fixture(scope="module")
def bearing_clamp(data):
    config, _, _, frame = data
    return build_bearing_clamp(
        frame.bearing_outer,
        config.slide.clamp_wall,
        frame.rod_raise,
        frame.clamp_len,
        frame.foot_length,
        frame.foot_thickness,
        frame.foot_top,
        config.slide.bearing_clamp.screw,
        config.slide.bearing_clamp.screw_span_y,
        config.slide.bearing_clamp.corner_chamfer,
        config.slide.bearing_clamp.top_chamfer,
    )


def test_chassis_bbox_matches_the_budget(data, solids):
    _, _, budget, frame = data
    chassis, _ = solids
    x, y, z = ch.bounding_box_mm(chassis)
    assert x == pytest.approx(budget.width, abs=0.1)
    assert y == pytest.approx(budget.chassis_height, abs=0.1)
    # The bearing-clamp seats hang below the Deck, inside the shell.
    assert z == pytest.approx(frame.chassis_top, abs=0.1)
    assert ch.volume_mm3(chassis) > 0


def test_screen_lid_bbox_matches_the_budget(data, solids):
    _, _, budget, frame = data
    _, lid = solids
    x, y, z = ch.bounding_box_mm(lid)
    assert x == pytest.approx(budget.width, abs=0.1)
    assert y == pytest.approx(budget.lid_height, abs=0.1)
    assert z == pytest.approx(frame.lid_thickness, abs=0.1)
    assert ch.volume_mm3(lid) > 0


def _width_at(shape, z):
    slab = ch.translate(ch.box_centered(1000.0, 1000.0, 0.01), 0.0, 0.0, z)
    return ch.bounding_box_mm(ch.intersect(shape, slab))[0]


def test_side_walls_are_drafted_toward_the_closed_face(data, solids):
    """The Tray widens from its base to its band; the Deck is prismatic."""
    _, _, _, frame = data
    chassis, lid = solids
    assert 5.0 <= frame.draft_angle <= 10.0

    c_base = _width_at(chassis, 0.5)
    c_top = _width_at(chassis, frame.chassis_top - 0.5)
    assert c_top > c_base + 1.0
    taper_half = ch.draft_inset(frame.draft_angle, 0.5)
    assert c_base == pytest.approx(
        frame.chassis_base_width + 2.0 * taper_half, abs=0.1
    )
    # The Deck (from the Parting plane up) is prismatic: it stays at the
    # closed-face width instead of flaring back out.
    assert c_top == pytest.approx(frame.width, abs=0.1)
    assert _width_at(chassis, frame.chassis_band_z0 + 0.5) == pytest.approx(
        frame.width, abs=0.1
    )

    l_bottom = _width_at(lid, frame.lid_bottom + 0.5)
    l_top = _width_at(lid, frame.lid_bottom + frame.lid_thickness - 0.5)
    assert l_bottom > l_top + 1.0
    # The Back plate and the joint band are prismatic (ADR-0011): the lid is
    # widest at the closed face, and only the Bezel above the band tapers
    # toward the display face.
    assert l_bottom == pytest.approx(frame.width, abs=0.1)
    assert _width_at(lid, frame.band_z0 + 0.5) == pytest.approx(
        frame.width, abs=0.1
    )
    assert l_top == pytest.approx(
        frame.lid_face_width + 2.0 * taper_half, abs=0.1
    )


def test_drafted_walls_keep_their_thickness(data, solids):
    """The cavity follows the drafted outer face, so no wall thins out.

    A cavity lofted between the nominal widths instead of the drafted ones
    would eat the side walls toward the Deck: the probe just inside the
    outer face must stay solid at every height and the probe a wall further
    in must be in the cavity.
    """
    config, _, _, frame = data
    chassis, _ = solids
    wall = config.wall_thickness
    # Probe away from the joint stations (which stand against every wall), so
    # only the plain wall section is measured.
    y_probe = 30.0
    for z in (1.5 * wall, frame.chassis_top / 2.0, frame.chassis_top - 2.5 * wall):
        outer_half = _width_at(chassis, z) / 2.0
        assert _material_at(chassis, outer_half - wall / 2.0, y_probe, z) > 0
        assert _material_at(
            chassis, outer_half - wall - 1.0, y_probe, z
        ) == pytest.approx(0)


def _chamfer_faces(shape):
    """The flat 45 degree faces of the drafted outside corners.

    The drafted side walls tilt each chamfer slightly out of vertical, so the
    test keys on the plan-view signature (equal |nx| and |ny|) rather than a
    zero Z component.
    """
    found = []
    for face in ch.faces(shape):
        if not ch.is_planar(face):
            continue
        nx, ny, nz = ch.face_normal(face)
        if abs(abs(nx) - abs(ny)) < 0.02 and abs(nx) > 0.55:
            found.append(face)
    return found


def _material_at(shape, x, y, z):
    probe = ch.translate(ch.box_centered(0.4, 0.4, 0.4), x, y, z)
    return ch.volume_mm3(ch.intersect(shape, probe))


def test_outer_corners_are_chamfered_not_filleted(data, solids):
    """Chamfer-first: the case corners are chopped, never rounded."""
    config, _, _, frame = data
    chassis, lid = solids
    assert config.corners.chamfer > 0
    # A flat 45 degree face at each outside corner — a fillet would be curved.
    for part in (chassis, lid):
        assert len(_chamfer_faces(part)) >= 4

    # The square corner is removed at every height, including the Deck rim;
    # the wall just inboard of the chamfer stays.
    hx, hy = frame.width / 2, frame.depth / 2
    zmid = frame.chassis_top / 2
    zdeck = frame.chassis_top - config.wall.thickness / 2
    for z in (zmid, zdeck):
        assert _material_at(chassis, hx - 0.3, hy - 0.3, z) == pytest.approx(0)
    # The wall just inboard of the chamfer stays (at zmid the drafted outer
    # face is already inside the nominal half-width, hence hx - 3.0).
    assert _material_at(chassis, hx - 3.0, hy - 6.0, zmid) > 0

    zc = frame.lid_bottom + frame.lid_thickness / 2
    y_front = frame.lid_y_center - frame.lid_height / 2
    y_rear = frame.lid_y_center + frame.lid_height / 2
    assert _material_at(lid, hx - 0.3, y_front + 0.3, zc) == pytest.approx(0)
    assert _material_at(lid, hx - 0.3, y_rear - 0.3, zc) == pytest.approx(0)


def test_lid_and_chassis_share_the_closed_face(data, solids):
    """Neither half overhangs the other: the lid defines the footprint."""
    _, _, budget, frame = data
    chassis, lid = solids
    chassis_box = ch.bounding_box(chassis)
    lid_box = ch.bounding_box(lid)
    assert chassis_box.ymin == pytest.approx(lid_box.ymin, abs=0.01)
    assert chassis_box.ymax == pytest.approx(lid_box.ymax, abs=0.01)
    assert chassis_box.ymin == pytest.approx(frame.front, abs=0.01)
    assert chassis_box.ymax - chassis_box.ymin == pytest.approx(
        budget.chassis_height, abs=0.1
    )


def test_chassis_sections_rejoin(data, solids):
    config, _, _, _ = data
    chassis, _ = solids
    left, right = ch.split_sections(chassis, config.slide.split.get("chassis"))
    assert ch.volume_mm3(left) + ch.volume_mm3(right) == pytest.approx(
        ch.volume_mm3(chassis), rel=1e-3
    )


def test_screen_lid_sections_rejoin(data, solids):
    config, _, _, _ = data
    _, lid = solids
    left, right = ch.split_sections(lid, config.slide.split.get("screen_lid"))
    assert ch.volume_mm3(left) + ch.volume_mm3(right) == pytest.approx(
        ch.volume_mm3(lid), rel=1e-3
    )


def test_sections_have_a_stepped_seam(data, solids):
    config, _, _, _ = data
    chassis, lid = solids
    step = config.slide.split["chassis"].step
    for part, name in ((chassis, "chassis"), (lid, "screen_lid")):
        left, right = ch.split_sections(part, config.slide.split.get(name))
        left_box = ch.bounding_box(left)
        right_box = ch.bounding_box(right)
        # A straight Seam stops at x=0; a stepped one crosses it by step/2.
        assert left_box.xmax > step / 2.0 - 1e-6
        assert right_box.xmin < -step / 2.0 + 1e-6


def test_sections_fit_the_build_volume(data, solids):
    config, _, _, _ = data
    chassis, lid = solids
    for part, name in ((chassis, "chassis"), (lid, "screen_lid")):
        left, right = ch.split_sections(part, config.slide.split.get(name))
        for section in (left, right):
            x, y, z = ch.bounding_box_mm(section)
            assert x <= BUILD_VOLUME[0] + 1e-6
            assert y <= BUILD_VOLUME[1] + 1e-6
            assert z <= BUILD_VOLUME[2] + 1e-6


def test_rod_covers_bearing_at_both_poses(data):
    """The rod must stay over the bearing when the lid slides open."""
    _, _, budget, frame = data
    half_bearing = budget.bearing_length / 2.0
    half_rod = budget.rod_usable / 2.0
    bearing = (
        frame.clamp_center_y - half_bearing,
        frame.clamp_center_y + half_bearing,
    )
    closed = (frame.rod_y - half_rod, frame.rod_y + half_rod)
    opened = (
        frame.rod_y + budget.travel - half_rod,
        frame.rod_y + budget.travel + half_rod,
    )
    for span in (closed, opened):
        assert span[0] <= bearing[0] + 1e-6
        assert span[1] >= bearing[1] - 1e-6


def test_guide_hardware(data):
    config, _, budget, _ = data
    rod = build_guide_rod(config.slide.rod.diameter, budget.rod_usable)
    x, y, z = ch.bounding_box_mm(rod)
    assert x == pytest.approx(config.slide.rod.diameter, abs=0.01)
    assert y == pytest.approx(budget.rod_usable, abs=0.01)
    assert z == pytest.approx(config.slide.rod.diameter, abs=0.01)

    bearing = build_linear_bearing(
        config.slide.bearing.outer_diameter,
        config.slide.bearing.bore,
        config.slide.bearing.length,
    )
    bx, by, bz = ch.bounding_box_mm(bearing)
    assert bx == pytest.approx(config.slide.bearing.outer_diameter, abs=0.01)
    assert by == pytest.approx(config.slide.bearing.length, abs=0.01)
    assert bz == pytest.approx(config.slide.bearing.outer_diameter, abs=0.01)
    # Hollow: the bushing is its outer cylinder minus the bore.
    import math

    outer_volume = math.pi * (config.slide.bearing.outer_diameter / 2.0) ** 2 * config.slide.bearing.length
    bore_volume = math.pi * (config.slide.bearing.bore / 2.0) ** 2 * config.slide.bearing.length
    assert ch.volume_mm3(bearing) == pytest.approx(
        outer_volume - bore_volume, rel=0.01
    )


def test_rod_clamps_hold_both_rod_ends(data):
    """Two clamps per rod, one at each end, inside the lid's cavity."""
    config, _, budget, frame = data
    clamp = build_rod_clamp(
        config.slide.rod.diameter,
        frame.rod_raise,
        frame.rod_clamp_len,
        frame.rod_clamp_height,
        frame.rod_clamp_width,
        config.slide.rod_clamp.screw,
        frame.rod_clamp_screw_span,
        config.slide.rod_clamp.set_screw,
    )
    x, y, z = ch.bounding_box_mm(clamp)
    assert x == pytest.approx(frame.rod_clamp_width, abs=0.01)
    assert y == pytest.approx(frame.rod_clamp_len, abs=0.01)
    assert z == pytest.approx(frame.rod_clamp_height, abs=0.01)

    rod_ends = (frame.rod_y - frame.rod_length / 2.0,
                frame.rod_y + frame.rod_length / 2.0)
    assert frame.rod_clamp_y[0] - frame.rod_clamp_len / 2.0 == pytest.approx(
        rod_ends[0], abs=1e-6
    )
    assert frame.rod_clamp_y[1] + frame.rod_clamp_len / 2.0 == pytest.approx(
        rod_ends[1], abs=1e-6
    )
    # The rod is inset from the lid's ends so the end wall stays solid.
    assert rod_ends[0] > frame.front
    assert rod_ends[1] < frame.front + frame.lid_height
    # The clamps clear the cavity end walls.
    assert frame.rod_clamp_y[0] - frame.rod_clamp_len / 2.0 > frame.front + frame.wall
    assert frame.rod_clamp_y[1] + frame.rod_clamp_len / 2.0 < (
        frame.front + frame.lid_height - frame.wall
    )


def test_bearing_clamp_straddles_the_back_panel(data, bearing_clamp):
    """The clamp's head is a cylinder at the neck width; its foot sits below."""
    config, _, budget, frame = data
    clamp = bearing_clamp
    x, y, z = ch.bounding_box_mm(clamp)
    assert x == pytest.approx(frame.clamp_body_width, abs=0.01)
    assert frame.clamp_body_width == pytest.approx(frame.clamp_width)
    assert y == pytest.approx(frame.foot_length, abs=0.01)
    assert budget.slot_fits
    # The head no longer overhangs the slot: the rod through the bearing is
    # what retains the lid.
    assert frame.clamp_body_width < frame.slot_width
    # The foot reaches below the Deck top into the seat pocket, and its top
    # face is flush with the Deck top.
    assert frame.foot_bottom_z < frame.chassis_top
    assert frame.pocket_depth == pytest.approx(frame.foot_thickness)
    assert frame.foot_top_z == pytest.approx(frame.chassis_top)


def test_bearing_clamp_base_is_flush_with_the_deck(data, bearing_clamp):
    """The base's top face lands level with the chassis top surface."""
    _, _, _, frame = data
    # The physical solid ends at foot_top; the world pose puts the deck top
    # exactly there, so the base does not stand proud of the chassis.
    assert frame.foot_top == pytest.approx(-(frame.panel_inner_z - frame.chassis_top))
    assert frame.foot_top_z == pytest.approx(frame.chassis_top)
    probe = ch.box_centered(0.1, 0.1, 0.1)
    # Just above the foot's top face (still inside the pocket mouth) is air.
    at = ch.translate(
        probe,
        0.0,
        frame.foot_length / 2.0 - 2.0,
        frame.foot_top_z - frame.panel_inner_z + 0.2,
    )
    assert ch.volume_mm3(ch.intersect(bearing_clamp, at)) == pytest.approx(
        0.0, abs=1e-6
    )


def test_bearing_clamp_screws_clear_the_bearing(data, bearing_clamp):
    """The foot's screw holes sit outside the bearing, so tips miss the bore."""
    config, _, budget, frame = data
    spec = screw_spec(config.slide.bearing_clamp.screw)
    inner_edge = (
        config.slide.bearing_clamp.screw_span_y / 2.0 - spec.pilot_hole / 2.0
    )
    assert inner_edge > budget.bearing_length / 2.0
    assert config.slide.bearing_clamp.screw_span_y / 2.0 < frame.foot_length / 2.0


def test_bearing_clamp_chamfers(data, bearing_clamp):
    """The foot's vertical corners are broken and the head is cylindrical."""
    config, _, _, frame = data
    cc = config.slide.bearing_clamp
    probe = ch.box_centered(0.5, 0.5, 0.5)
    foot_mid_z = frame.foot_top_z - frame.panel_inner_z - cc.foot_thickness / 2.0
    # Nominal foot corner: removed by the 5 mm corner chamfer.
    at = ch.translate(
        probe,
        frame.clamp_width / 2.0 - 0.5,
        frame.foot_length / 2.0 - 0.5,
        foot_mid_z,
    )
    assert ch.volume_mm3(ch.intersect(bearing_clamp, at)) == pytest.approx(
        0.0, abs=1e-6
    )
    # The straight part of the same end is still solid.
    at = ch.translate(probe, 0.0, frame.foot_length / 2.0 - 0.5, foot_mid_z)
    assert ch.volume_mm3(ch.intersect(bearing_clamp, at)) > 0.0
    # The head is a cylinder around the bearing: the corner of its bounding
    # box is air, while the wall between the bore and the outer surface is
    # solid.
    body_z = frame.rod_raise + frame.clamp_width / 2.0
    at = ch.translate(
        probe,
        frame.clamp_body_width / 2.0 - 0.1,
        0.0,
        body_z / 2.0,
    )
    assert ch.volume_mm3(ch.intersect(bearing_clamp, at)) == pytest.approx(
        0.0, abs=1e-6
    )
    at = ch.translate(probe, 6.0, 0.0, body_z / 2.0)
    assert ch.volume_mm3(ch.intersect(bearing_clamp, at)) > 0.0


def test_bearing_clamp_top_edges_are_chamfered(data, bearing_clamp):
    """The foot's exposed top perimeter gets the small mouth relief."""
    config, _, _, frame = data
    foot_top = frame.foot_top_z - frame.panel_inner_z
    probe = ch.box_centered(0.1, 0.1, 0.1)
    at = ch.translate(
        probe, 0.0, frame.foot_length / 2.0 - 0.1, foot_top - 0.1
    )
    assert ch.volume_mm3(ch.intersect(bearing_clamp, at)) == pytest.approx(
        0.0, abs=1e-6
    )
    at = ch.translate(
        probe, 0.0, frame.foot_length / 2.0 - 1.0, foot_top - 0.1
    )
    assert ch.volume_mm3(ch.intersect(bearing_clamp, at)) > 0.0


def test_bearing_clamp_pocket_mouth_is_chamfered(data, solids):
    """The pocket mouth is broken to match the clamp foot's top edge."""
    config, _, _, frame = data
    chassis, _ = solids
    probe = ch.box_centered(0.1, 0.1, 0.1)
    x = frame.rod_x + frame.pocket_width / 2.0 + 0.1
    at = ch.translate(probe, x, frame.clamp_center_y, frame.chassis_top - 0.1)
    assert ch.volume_mm3(ch.intersect(chassis, at)) == pytest.approx(
        0.0, abs=1e-6
    )
    at = ch.translate(probe, x, frame.clamp_center_y, frame.chassis_top - 0.6)
    assert ch.volume_mm3(ch.intersect(chassis, at)) > 0.0


def test_bearing_clamp_pocket_has_chamfered_corners(data, solids):
    """The pocket's corners are chamfered to match the clamp's foot."""
    config, _, _, frame = data
    chassis, _ = solids
    probe = ch.box_centered(0.5, 0.5, 0.5)
    z_mid = frame.chassis_top - frame.pocket_depth / 2.0
    at = ch.translate(
        probe,
        frame.rod_x + frame.pocket_width / 2.0 - 0.5,
        frame.clamp_center_y + frame.pocket_length / 2.0 - 0.5,
        z_mid,
    )
    # A square pocket would be air here; the chamfer leaves seat material.
    assert ch.volume_mm3(ch.intersect(chassis, at)) > 0.0


def test_bearing_clamp_fits_its_chassis_pocket(data, solids, bearing_clamp):
    """The foot (with its corner chamfers) drops into the pocket cleanly."""
    _, _, _, frame = data
    chassis, _ = solids
    placed = ch.translate(
        bearing_clamp, frame.rod_x, frame.clamp_center_y, frame.panel_inner_z
    )
    assert ch.volume_mm3(ch.intersect(chassis, placed)) == pytest.approx(
        0.0, abs=1e-3
    )


def test_bearing_never_reaches_the_rod_clamps(data):
    """The short bearing stops short of the end clamps at both poses."""
    config, _, budget, frame = data
    half = frame.bearing_length / 2.0
    closed = (frame.clamp_center_y - half, frame.clamp_center_y + half)
    opened = (closed[0] - budget.travel, closed[1] - budget.travel)
    bottom_inner = frame.rod_clamp_y[0] + frame.rod_clamp_len / 2.0
    top_inner = frame.rod_clamp_y[1] - frame.rod_clamp_len / 2.0
    clearance = config.slide.rod_clamp.clearance
    assert top_inner - closed[1] >= clearance - 1e-6
    assert opened[0] - bottom_inner >= clearance - 1e-6


def test_bearing_clamp_seat_sits_forward_of_the_rear_wall(data):
    """The extended chassis leaves the clamp seat slightly forward of the rear."""
    _, _, _, frame = data
    rear_inner = frame.front + frame.depth - frame.wall
    seat_front = frame.clamp_center_y - frame.seat_length / 2.0
    seat_rear = frame.clamp_center_y + frame.seat_length / 2.0
    assert seat_rear < rear_inner
    assert rear_inner - seat_rear > frame.wall
    # The seat still clears the keyboard well (the whole rear band is behind
    # the well, and the clamp body is behind the SBC row).
    assert seat_front > frame.keyboard_y + frame.keyboard_d / 2.0


def test_back_panel_has_a_through_slot_between_the_rod_clamps(data, solids):
    config, _, budget, frame = data
    _, lid = solids
    slot_y = (frame.slot_y0 + frame.slot_y1) / 2.0
    z_mid = (frame.panel_outer_z + frame.panel_inner_z) / 2.0
    probe = ch.box_centered(2.0, 2.0, 2.0)
    in_slot = ch.translate(probe, frame.rod_x, slot_y, z_mid)
    assert ch.volume_mm3(ch.intersect(lid, in_slot)) == pytest.approx(0.0, abs=1e-6)
    # The panel beside the slot is solid.
    beside = ch.translate(
        probe, frame.rod_x - (frame.slot_width / 2.0 + 3.0), slot_y, z_mid
    )
    assert ch.volume_mm3(ch.intersect(lid, beside)) == pytest.approx(8.0, rel=0.01)


def test_chassis_has_a_bearing_clamp_seat(data, solids):
    config, _, budget, frame = data
    chassis, _ = solids
    probe = ch.box_centered(2.0, 2.0, 2.0)
    z_mid = frame.chassis_top - frame.pocket_depth / 2.0
    in_pocket = ch.translate(probe, frame.rod_x, frame.clamp_center_y, z_mid)
    assert ch.volume_mm3(ch.intersect(chassis, in_pocket)) == pytest.approx(0.0, abs=1e-6)
    wall_x = frame.rod_x + frame.seat_width / 2.0 - 1.0
    in_wall = ch.translate(probe, wall_x, frame.clamp_center_y, z_mid)
    assert ch.volume_mm3(ch.intersect(chassis, in_wall)) > 1.0
