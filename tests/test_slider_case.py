"""First-generation slider case geometry (issue #3).

The case must be a closed solid inside the derived budget, split into two
printable Sections that add back to the whole, with the guide hardware in the
right place. These are shape-level assertions, not a golden-master volume.
"""

import math

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
from geometry.printability import PrintOrientation, check_bed_face
from geometry.well_mounts import well_mounts
from layouts import make_layout
from main import BuildPipeline
from utilities import cad_helpers as ch
from utilities.fasteners import screw as screw_spec
from utilities.slider_validation import BUILD_VOLUME
from utilities.validation import ValidationReport


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
def pieces(data):
    """The four printed shell pieces, each with its own Seam (ADR-0015)."""
    config, _, _, frame = data
    chassis = Chassis(config, frame)
    lid = ScreenLid(config, frame)
    return {
        "chassis_tray": (chassis.build_tray(), frame.depth),
        "chassis_deck": (chassis.build_deck(), frame.depth),
        "screen_lid_bezel": (lid.build_bezel(), frame.lid_height),
        "screen_lid_back": (lid.build_back(), frame.lid_height),
    }


@pytest.fixture(scope="module")
def solids(pieces):
    return (
        ch.make_compound(
            [pieces["chassis_tray"][0], pieces["chassis_deck"][0]]
        ),
        ch.make_compound(
            [pieces["screen_lid_bezel"][0], pieces["screen_lid_back"][0]]
        ),
    )


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


def test_each_shell_keeps_a_wall_at_its_chamfered_corners(data, pieces):
    """The cavity corners follow the outer chop (ADR-0016).

    A square cavity corner meets the 4 mm outer chamfer at a knife edge on the
    2 mm wall: the corner prints as a hole. The cavity carries the derived
    inner chamfer, so a full wall stands behind every chopped corner.
    """
    config, _, _, frame = data
    root = math.sqrt(0.5)
    outer_face = config.corners.chamfer * root
    specs = (
        (
            "chassis_tray",
            frame.chassis_band_width / 2.0,
            0.0,
            frame.depth / 2.0,
            frame.parting_z - 1.5,
        ),
        (
            "chassis_deck",
            frame.chassis_band_width / 2.0,
            0.0,
            frame.depth / 2.0,
            frame.parting_z + 1.5,
        ),
        (
            "screen_lid_bezel",
            frame.width / 2.0,
            frame.lid_y_center,
            frame.lid_height / 2.0,
            (frame.band_z0 + frame.band_z1) / 2.0,
        ),
    )
    for name, hx, y_centre, hy, z in specs:
        part = pieces[name][0]
        for sx in (-1, 1):
            for sy in (-1, 1):
                ax, ay = sx * hx, y_centre + sy * hy
                nx, ny = sx * root, sy * root

                def at(d: float) -> float:
                    return _material_at(part, ax - nx * d, ay - ny * d, z)

                assert at(outer_face - 0.4) == pytest.approx(0), (
                    f"{name}: no chamfer at ({ax:.1f}, {ay:.1f})"
                )
                for d in (outer_face + 0.4, outer_face + 0.8):
                    assert at(d) > 0, (
                        f"{name}: the corner at ({ax:.1f}, {ay:.1f}) is open "
                        f"{d - outer_face:.2f} mm behind the chop"
                    )


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


def test_chassis_sections_rejoin(data, pieces):
    config, _, _, frame = data
    wall = config.wall.thickness
    from geometry.split import split_part

    for name in ("chassis_tray", "chassis_deck"):
        part, depth = pieces[name]
        left, right = split_part(part, config.slide.split[name], depth, wall)
        assert ch.volume_mm3(left) + ch.volume_mm3(right) == pytest.approx(
            ch.volume_mm3(part), rel=1e-3
        )


def test_screen_lid_sections_rejoin(data, pieces):
    config, _, _, frame = data
    wall = config.wall.thickness
    from geometry.split import split_part

    for name in ("screen_lid_bezel", "screen_lid_back"):
        part, depth = pieces[name]
        left, right = split_part(part, config.slide.split[name], depth, wall)
        assert ch.volume_mm3(left) + ch.volume_mm3(right) == pytest.approx(
            ch.volume_mm3(part), rel=1e-3
        )


def test_sections_are_cut_on_each_parts_own_staggered_seam(data, pieces):
    """ADR-0015: the Tray and Deck (and Bezel and Back) never share a Seam."""
    from geometry.split import split_part

    config, _, _, _ = data
    wall = config.wall.thickness
    cut = {}
    for name, (part, depth) in pieces.items():
        spec = config.slide.split[name]
        left, right = split_part(part, spec, depth, wall)
        lo, hi = spec.x_range
        cut[name] = (lo, hi)
        # The left Section reaches the Seam's furthest +X run, the right one its
        # furthest -X run: the cut really is the configured path.
        assert ch.bounding_box(left).xmax == pytest.approx(hi, abs=0.05)
        assert ch.bounding_box(right).xmin == pytest.approx(lo, abs=0.05)

    # The two Seams of each screwed pair run on opposite sides of the centre.
    assert cut["chassis_tray"][0] > cut["chassis_deck"][1]
    assert cut["screen_lid_back"][0] > cut["screen_lid_bezel"][1]


def test_sections_fit_the_build_volume(data, pieces):
    from geometry.split import split_part

    config, _, _, _ = data
    wall = config.wall.thickness
    for name, (part, depth) in pieces.items():
        spec = config.slide.split[name]
        for section in split_part(part, spec, depth, wall):
            x, y, z = ch.bounding_box_mm(section)
            assert x <= BUILD_VOLUME[0] + 1e-6
            assert y <= BUILD_VOLUME[1] + 1e-6
            assert z <= BUILD_VOLUME[2] + 1e-6


def test_every_piece_carries_its_half_of_every_seam_pin(data, pieces):
    """ADR-0006: the fins straddle the Seam, so each Section prints a half."""
    from geometry.seam_joint import pocket_rect, pocket_z
    from geometry.split import split_part

    config, _, _, frame = data
    wall = config.wall.thickness
    pin = config.seam_pin

    def material(shape, x, y, z, size=0.2):
        probe = ch.translate(ch.box_centered(size, size, size), x, y, z)
        return ch.volume_mm3(ch.intersect(shape, probe)) > 1e-6

    # Wall thickness is constant (``fin``); chamfer is a base flare only.
    fin_mid = pin.gap / 2.0 + pin.fin / 2.0
    for name, (part, depth) in pieces.items():
        seam = config.slide.split[name].seams(depth, wall)[0]
        substrate, upward = frame.seam_pin_planes[name]
        z0, z1 = pocket_z(pin, substrate, upward)
        z = substrate + (pin.height / 2.0 if upward else -pin.height / 2.0)
        left, right = split_part(part, config.slide.split[name], depth, wall)
        for y in config.slide.seam_pin_sites[name]:
            x = seam.x_at(y)
            x0, x1, y0, y1 = pocket_rect(pin, x, y)
            fin_z = z
            # Slot center empty; fin walls at ±fin_mid.
            assert not material(part, x, y, fin_z)
            assert material(part, x, y - fin_mid, fin_z)
            assert material(part, x, y + fin_mid, fin_z)
            # Each Section keeps its half of the fin.
            half = pin.engagement - 0.5
            assert material(left, x - half, y - fin_mid, fin_z)
            assert material(right, x + half, y + fin_mid, fin_z)
            assert not material(left, x + half, y - fin_mid, fin_z)
            assert not material(right, x - half, y + fin_mid, fin_z)


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


# -- the FPC guard -------------------------------------------------------


@pytest.fixture(scope="module")
def guard(data):
    config, _, _, frame = data
    return ScreenLid(config, frame).build_fpc_guard()


def test_fpc_guard_matches_the_budget(data, guard):
    """A flat plate: the budget's planform, `total` thick."""
    _, _, _, frame = data
    g = frame.fpc_guard
    gx0, gy0, gx1, gy1 = frame.guard_planform
    x, y, z = ch.bounding_box_mm(guard)
    assert x == pytest.approx(gx1 - gx0, abs=0.05)
    assert y == pytest.approx(gy1 - gy0, abs=0.05)
    assert z == pytest.approx(g.total, abs=1e-6)
    assert g.floor == pytest.approx(g.total - g.recess)


def test_fpc_guard_has_a_ribbon_channel_and_free_end(data, guard):
    """The channel is recessed from the display-facing side, open at both ends."""
    _, _, _, frame = data
    g = frame.fpc_guard
    gx0, gy0, gx1, gy1 = frame.guard_planform
    x0, x1 = gx0 - frame.display_x, gx1 - frame.display_x
    xc = (x0 + x1) / 2.0
    # Local origin: the display's back face, on its centre; z = -total..0. The
    # plate starts at the driver's FPC connector, so it is not centred on X.
    for x in (xc, x0 + 0.2, x1 - 0.2):
        assert _material_at(guard, x, 0.0, -g.recess / 2.0) == pytest.approx(0)
    # The grille floor under the channel is solid.
    assert _material_at(guard, xc, 0.0, -g.recess - g.floor / 2.0) > 0


def test_fpc_guard_is_a_grille_not_a_solid_plate(data, guard):
    """Blind slots on the underside leave struts between them."""
    config, _, _, frame = data
    g = frame.fpc_guard
    gx0, gy0, gx1, gy1 = frame.guard_planform
    xc = (gx0 + gx1) / 2.0 - frame.display_x
    gy0 = gy0 - frame.display_y
    inset = config.material.minimum_feature + g.grille_slot / 2.0
    slot_y = gy0 + inset
    strut_y = slot_y + frame.guard_slot_pitch / 2.0
    z = -g.total + frame.guard_slot_depth / 2.0
    assert _material_at(guard, xc, slot_y, z) == pytest.approx(0)
    assert _material_at(guard, xc, strut_y, z) > 0
    assert frame.guard_slot_depth == pytest.approx(
        g.floor - config.material.minimum_feature
    )


def test_fpc_guard_covers_the_slot_band_and_clears_the_head(data, guard):
    """In the assembly frame: covers the ribbon and the slot band, and the
    moving head's crown stays `gap + sag` below its underside."""
    config, _, budget, frame = data
    g = frame.fpc_guard
    world = ch.translate(guard, frame.display_x, frame.display_y, frame.display_z0)
    gx0, gy0, gx1, gy1 = frame.guard_planform
    ribbon_half = config.display.flex.width / 2.0
    assert gx0 <= budget.rod_x - budget.hardware_width / 2.0 - g.margin + 1e-6
    assert gx1 >= budget.rod_x + budget.hardware_width / 2.0 + g.margin - 1e-6
    assert gy0 <= frame.display_y - ribbon_half - g.margin + 1e-6
    assert gy1 >= frame.display_y + ribbon_half + g.margin - 1e-6
    # Its top face is the display's back, and its underside is what the head
    # must clear.
    box = ch.bounding_box(world)
    assert box.zmax == pytest.approx(frame.display_z0, abs=1e-6)
    assert box.zmax - box.zmin == pytest.approx(g.total, abs=1e-6)
    underside = frame.display_z0 - g.total
    crown = frame.panel_inner_z + frame.head_crown
    assert underside - crown >= (
        config.slide.component_gap + g.sag_allowance - 1e-6
    )


def test_fpc_guard_does_not_touch_the_bearing_clamp_head(data, guard, bearing_clamp):
    """The guard is the sacrificial part: the head stops short of it."""
    _, _, _, frame = data
    world = ch.translate(guard, frame.display_x, frame.display_y, frame.display_z0)
    head = ch.translate(
        bearing_clamp, frame.rod_x, frame.clamp_center_y, frame.panel_inner_z
    )
    assert ch.volume_mm3(ch.intersect(world, head)) == pytest.approx(0, abs=1e-6)


def test_lid_sweeps_clear_of_the_chassis_over_the_whole_travel(data, solids):
    """A real solid sweep, not the placement boxes: the shells never touch."""
    _, _, budget, _ = data
    chassis, lid = solids
    for step in range(4):
        shift = budget.travel * step / 3.0
        assert ch.volume_mm3(
            ch.intersect(ch.translate(lid, 0.0, shift, 0.0), chassis)
        ) == pytest.approx(0, abs=1e-3)


def test_fpc_guard_stays_clear_of_the_head_over_the_whole_travel(data, guard, bearing_clamp):
    """The guard slides with the lid; the head is fixed to the Deck."""
    _, _, budget, frame = data
    world = ch.translate(guard, frame.display_x, frame.display_y, frame.display_z0)
    head = ch.translate(
        bearing_clamp, frame.rod_x, frame.clamp_center_y, frame.panel_inner_z
    )
    for step in range(9):
        shift = budget.travel * step / 8.0
        assert ch.volume_mm3(
            ch.intersect(ch.translate(world, 0.0, shift, 0.0), head)
        ) == pytest.approx(0, abs=1e-6)


# -- the Well in the Deck (ADR-0014) -------------------------------------


@pytest.fixture(scope="module")
def deck(data):
    config, _, _, frame = data
    return Chassis(config, frame).build_deck()


@pytest.fixture(scope="module")
def mounts(data):
    config, _, budget, frame = data
    return well_mounts(config, budget, frame=frame.plate_frame)


def _material_bounds(shape, x0, y0, x1, y1, z0, z1):
    """Bounding box of the solid inside a probe box, or None when empty."""
    probe = ch.box_centered(x1 - x0, y1 - y0, z1 - z0)
    probe = ch.translate(
        probe, (x0 + x1) / 2.0, (y0 + y1) / 2.0, (z0 + z1) / 2.0
    )
    hit = ch.intersect(shape, probe)
    if ch.volume_mm3(hit) < 1e-9:
        return None
    return ch.bounding_box(hit)


def _cylinder_faces(shape):
    """Every cylindrical face as (radius, axis XY, axis direction, z-span).

    Read from the solid's topology, not from a volume or a centre of mass: a
    bore's own axis is what the screw has to follow.
    """
    from OCP.BRepAdaptor import BRepAdaptor_Surface

    found = []
    for face in ch.faces(shape):
        if "CYLINDER" not in str(face.geom_type):
            continue
        cylinder = BRepAdaptor_Surface(face.wrapped).Cylinder()
        axis = cylinder.Axis()
        location = axis.Location()
        direction = axis.Direction()
        box = face.bounding_box()
        found.append(
            {
                "radius": cylinder.Radius(),
                "x": location.X(),
                "y": location.Y(),
                "z0": box.min.Z,
                "z1": box.max.Z,
                "axis": (direction.X(), direction.Y(), direction.Z()),
            }
        )
    return found


def _well_z_bands(data, deck, mounts):
    """The four ring bands, measured on the real solid at mid-Well height."""
    _, _, _, frame = data
    cut = mounts.cutout_rect
    z = (mounts.plate_top + frame.chassis_top) / 2.0
    # Probe the front/rear bands half-way between the centreline and the side:
    # the centreline band boss (ADR-0015) merges into the ring at x=0.
    probe_x = cut.x0 / 2.0
    return {
        "front": _material_bounds(
            deck, probe_x - 0.5, cut.y0 - 3.0, probe_x + 0.5, cut.y0 + 3.0,
            z - 0.1, z + 0.1,
        ),
        "rear": _material_bounds(
            deck, probe_x - 0.5, cut.y1 - 3.0, probe_x + 0.5, cut.y1 + 3.0,
            z - 0.1, z + 0.1,
        ),
        "left": _material_bounds(
            deck, cut.x0 - 3.0, mounts.frame.cy - 0.5, cut.x0 + 3.0,
            mounts.frame.cy + 0.5, z - 0.1, z + 0.1,
        ),
        "right": _material_bounds(
            deck, cut.x1 - 3.0, mounts.frame.cy - 0.5, cut.x1 + 3.0,
            mounts.frame.cy + 0.5, z - 0.1, z + 0.1,
        ),
    }


def test_well_ring_is_one_wall_thick_on_all_four_sides(data, deck, mounts):
    """The Well descends as a `wall.thickness` ring around the Cutout."""
    config, _, _, _ = data
    wall = config.wall.thickness
    cut = mounts.cutout_rect
    plate = mounts.frame.rect
    bands = _well_z_bands(data, deck, mounts)

    assert bands["front"] is not None, "no front Well wall"
    assert bands["rear"] is not None, "no rear Well wall"
    assert bands["left"] is not None, "no left Well wall"
    assert bands["right"] is not None, "no right Well wall"

    assert bands["front"].ymax - bands["front"].ymin == pytest.approx(wall, abs=1e-3)
    assert bands["rear"].ymax - bands["rear"].ymin == pytest.approx(wall, abs=1e-3)
    assert bands["left"].xmax - bands["left"].xmin == pytest.approx(wall, abs=1e-3)
    assert bands["right"].xmax - bands["right"].xmin == pytest.approx(wall, abs=1e-3)

    # Outer faces are the plate outline; inner faces are the Cutout.
    assert bands["front"].ymin == pytest.approx(plate.y0, abs=1e-3)
    assert bands["front"].ymax == pytest.approx(cut.y0, abs=1e-3)
    assert bands["rear"].ymin == pytest.approx(cut.y1, abs=1e-3)
    assert bands["rear"].ymax == pytest.approx(plate.y1, abs=1e-3)
    assert bands["left"].xmin == pytest.approx(plate.x0, abs=1e-3)
    assert bands["left"].xmax == pytest.approx(cut.x0, abs=1e-3)
    assert bands["right"].xmin == pytest.approx(cut.x1, abs=1e-3)
    assert bands["right"].xmax == pytest.approx(plate.x1, abs=1e-3)


def test_well_ring_reaches_from_the_deck_top_to_the_plate_top(data, deck, mounts):
    """The ring's lower faces are the plate's bearing: no ledge, no floor."""
    _, _, _, frame = data
    cut = mounts.cutout_rect
    probe_x = cut.x0 / 2.0
    band = _material_bounds(
        deck, probe_x - 0.5, cut.y0 - 3.0, probe_x + 0.5, cut.y0 + 3.0,
        frame.parting_z - 2.0, frame.chassis_top + 2.0,
    )
    assert band is not None
    assert band.zmin == pytest.approx(mounts.plate_top, abs=1e-3)
    assert band.zmax == pytest.approx(frame.chassis_top, abs=1e-3)
    # Nothing of the ring hangs below the plate's top face.
    assert band.zmin > frame.parting_z


def test_well_cutout_is_the_keycap_footprint_not_the_shell_clearance(data, deck, mounts):
    """The opening is sized by the keycaps + wobble, not `clearance.shell`."""
    _, _, _, frame = data
    cut = mounts.cutout_rect
    bands = _well_z_bands(data, deck, mounts)

    width = bands["right"].xmin - bands["left"].xmax
    depth = bands["rear"].ymin - bands["front"].ymax
    assert width == pytest.approx(cut.width, abs=1e-3)
    assert depth == pytest.approx(cut.depth, abs=1e-3)
    assert width == pytest.approx(mounts.frame.width - 2.0 * mounts.ring, abs=1e-3)
    assert depth == pytest.approx(mounts.frame.depth - 2.0 * mounts.ring, abs=1e-3)
    assert width != pytest.approx(frame.keyboard_w + 2.0 * frame.clearance, abs=0.1)
    assert depth != pytest.approx(frame.keyboard_d + 2.0 * frame.clearance, abs=0.1)


def test_eight_insert_holes_at_the_well_stations(data, deck, mounts):
    """Each T1b station carries an M2 insert bore, read from the topology."""
    insert_radius = mounts.insert_hole_diameter / 2.0
    boss_radius = mounts.boss_diameter / 2.0
    cylinders = _cylinder_faces(deck)
    holes = [
        c
        for c in cylinders
        if abs(c["radius"] - insert_radius) < 1e-3
        and abs(c["axis"][2] - 1.0) < 1e-6
    ]
    assert len(holes) == len(mounts.mounts) == 8

    for mount in mounts.mounts:
        matches = [
            h
            for h in holes
            if abs(h["x"] - mount.x) < 1e-2 and abs(h["y"] - mount.y) < 1e-2
        ]
        assert len(matches) == 1, f"no insert bore at {mount.name}"
        hole = matches[0]
        assert hole["z0"] == pytest.approx(mounts.plate_top, abs=1e-3)
        assert hole["z1"] == pytest.approx(
            mounts.plate_top + mount.insert_depth, abs=1e-3
        )

        bosses = [
            c
            for c in cylinders
            if abs(c["radius"] - boss_radius) < 1e-3
            and abs(c["x"] - mount.x) < 1e-2
            and abs(c["y"] - mount.y) < 1e-2
        ]
        assert bosses, f"no merged boss at {mount.name}"
        assert min(b["z0"] for b in bosses) == pytest.approx(
            mounts.plate_top, abs=1e-3
        )
        assert max(b["z1"] for b in bosses) == pytest.approx(
            mount.boss_z1, abs=1e-3
        )


def test_every_boss_column_runs_up_to_the_deck_ceiling(data, deck, mounts):
    """Printed face down, every boss is a column standing on the top slab.

    The Deck prints with its closed face on the bed, so a boss that stopped at
    its insert would be an unsupported horizontal overhang. Both the plate's
    M2 bosses and the chassis band's M3 bosses must be solid from their base
    all the way up to the ceiling under the closed face -- probed off the
    insert bore, which is a blind hole.
    """
    _, _, _, frame = data
    ceiling = frame.chassis_top - frame.wall
    joint = frame.chassis_joint
    columns = [
        (m.name, m.x, m.y, m.boss_z0, m.boss_diameter / 2.0)
        for m in mounts.mounts
    ] + [
        (
            f"band:{s.kind}@{s.x:.2f},{s.y:.2f}",
            s.x,
            s.y,
            frame.parting_z,
            s.boss / 2.0,
        )
        for s in joint.stations
    ]
    for name, x, y, base, radius in columns:
        # Between the insert bore (Ø3.0 -> r 1.5) and the boss surface.
        probe = radius * 0.75
        for z in (base + 0.4, (base + ceiling) / 2.0, ceiling - 0.3):
            assert _material_at(deck, x + probe, y, z) > 0, (
                f"{name}: hollow {probe:.2f} mm off the axis at z {z:.2f} "
                f"(base {base:.2f}, ceiling {ceiling:.2f})"
            )


def test_no_insert_boss_or_ledge_enters_the_well_cutout(data, deck, mounts):
    """The Cutout column is clear from below the plate to the Deck top."""
    _, _, _, frame = data
    cut = mounts.cutout_rect
    column = ch.box_centered(cut.width, cut.depth, frame.chassis_top - frame.parting_z + 2.0)
    column = ch.translate(
        column, cut.cx, cut.cy,
        (frame.chassis_top + frame.parting_z) / 2.0,
    )
    assert ch.volume_mm3(ch.intersect(deck, column)) == pytest.approx(0, abs=1e-6)


def test_ring_is_interrupted_where_the_plate_is_notched(data, deck, mounts):
    """A band column may not share volume with the ring (the plate's notch).

    The notch removes the ring's outer reach only: the inner sliver of the
    ring stays, so the Well remains sealed end to end. Above the plate the
    notch itself is filled by the band column, which now runs the Deck's full
    height, so the probe keeps clear of that column's disc.
    """
    assert mounts.notches, "the plate is not notched under the band columns"
    for notch in mounts.notches:
        plan = mounts.frame.to_plan_rect(notch.rect)
        # Above the plate's top (17.8) and below the Deck's top slab (30.3) the
        # only Deck material here may be the band column: the notch cut the
        # ring's outer reach away. Probe the notch's inboard corner -- outboard
        # of the column's disc and of the ring's remaining sliver.
        probe = ch.box_centered(0.2, 0.2, 6.0)
        probe = ch.translate(probe, plan.x0 + 0.25, plan.y1 - 0.25, 25.5)
        assert ch.volume_mm3(ch.intersect(deck, probe)) == pytest.approx(
            0, abs=1e-6
        ), f"the ring fills the plate notch at {notch.source}"

        # ... but the ring's inner sliver keeps the Well continuous.
        sealed = _material_bounds(
            deck,
            plan.x0 + 0.65, plan.y1 + 0.1, plan.x1 - 0.65, plan.y1 + 0.7,
            22.5, 28.5,
        )
        assert sealed is not None, f"the notch severed the ring at {notch.source}"


def test_the_band_does_not_breach_the_plate_border_or_a_boss(data, deck, mounts):
    """Nothing cut into the band reaches the plate's border or a Well boss."""
    _, _, _, frame = data
    z = frame.parting_z + 1.85
    cut = mounts.cutout_rect
    for station in frame.chassis_joint.stations:
        if station.y < 0.0:
            assert _material_at(deck, station.x, cut.y0 - 0.45, z) > 0
        else:
            assert _material_at(deck, station.x, cut.y1 + 0.45, z) > 0
    for mount in mounts.mounts:
        # The boss itself still stands proud of the ring, off the insert bore.
        off = 1.5 if mount.is_front else -1.5
        assert _material_at(deck, mount.x, mount.y + off, z + 0.5) > 0


def test_deck_sections_rejoin_and_print_closed_face_down(data, deck):
    """The ring is part of the Deck: it splits at the Seam and prints flat."""
    config, _, _, frame = data
    from geometry.split import split_part

    left, right = split_part(
        deck,
        config.slide.split["chassis_deck"],
        frame.depth,
        config.wall.thickness,
    )
    assert ch.volume_mm3(left) + ch.volume_mm3(right) == pytest.approx(
        ch.volume_mm3(deck), rel=1e-3
    )
    # Nothing new crosses the Parting plane: the Well stands on the Deck.
    assert ch.bounding_box(deck).zmin == pytest.approx(frame.parting_z, abs=1e-3)

    report = ValidationReport()
    for name, section in (("chassis_deck_left", left), ("chassis_deck_right", right)):
        x, y, z = ch.bounding_box_mm(section)
        assert x <= BUILD_VOLUME[0] + 1e-6
        assert y <= BUILD_VOLUME[1] + 1e-6
        assert z <= BUILD_VOLUME[2] + 1e-6
        check_bed_face(
            name,
            section,
            PrintOrientation((0.0, 0.0, 1.0)),
            config.material.min_bed_face_area,
            report,
        )
    assert report.passed, report.summary()


def test_the_placed_plate_does_not_share_volume_with_the_deck(data, deck, mounts):
    """The plate sits under the Well ring and clears every band boss (#19).

    The plate is placed by the keyboard's own frame, exactly as the assembly
    places it, then intersected with the Deck. The notches were on the wrong
    lip before the frame fix: the plate's front-lip material would sit inside
    the band columns.
    """
    config, components, budget, frame = data
    keyboard = components["keyboard"]
    keyboard.set_well_mounts(mounts)
    plate = keyboard._plate.build()
    placed = ch.rotate_z(plate, frame.plate_frame.rotation)
    placed = ch.translate(
        placed,
        frame.plate_frame.cx,
        frame.plate_frame.cy,
        budget.well.plate_bottom,
    )
    assert ch.volume_mm3(ch.intersect(deck, placed)) == pytest.approx(
        0.0, abs=1e-6
    )
    # And the plate really is under the ring: every station's ear is plate
    # material at the plate's own Z (the screw has something to clamp).
    for mount in mounts.mounts:
        assert _material_at(
            placed,
            mount.world_xy[0] + 1.75,
            mount.world_xy[1],
            budget.well.plate_bottom + 0.75,
        ) > 0.0, f"{mount.name}: no plate material under the boss"
