"""The chassis Tray <-> Deck band joint (ADR-0012).

Data-level assertions (stations, band, screw, stations clear of components)
plus shape-level checks that the Tray and the Deck really meet at the Parting
plane, carry the screw holes, keep a plain outer band (ADR-0016) and rejoin into
the whole.
"""

import math

import pytest

from case.chassis import Chassis
from utilities import fasteners
from case.slider_frame import SliderFrame
from components.slide import compute_slide_budget
from layouts import make_layout
from main import BuildPipeline
from utilities import cad_helpers as ch
from utilities.slider_validation import BUILD_VOLUME


@pytest.fixture(scope="module")
def data():
    pipeline = BuildPipeline("config/default.yaml", layout_name="slider")
    config = pipeline.load_config()
    components = pipeline.load_components()
    placements = make_layout("slider", components, config=config).placements()
    budget = compute_slide_budget(config, components)
    frame = SliderFrame.from_data(config, budget, components, placements)
    return config, budget, frame, placements


@pytest.fixture(scope="module")
def solids(data):
    config, _, frame, _ = data
    chassis = Chassis(config, frame)
    return chassis.build_tray(), chassis.build_deck()


def _material_at(shape, x, y, z):
    probe = ch.translate(ch.box_centered(0.4, 0.4, 0.4), x, y, z)
    return ch.volume_mm3(ch.intersect(shape, probe))


def _width_at(shape, z):
    slab = ch.translate(ch.box_centered(1000.0, 1000.0, 0.01), 0.0, 0.0, z)
    return ch.bounding_box_mm(ch.intersect(shape, slab))[0]


# -- data ----------------------------------------------------------------
def test_twelve_stations_four_corners_six_sides_two_ends(data):
    """ADR-0015 adds one long-wall station per side, on the centreline."""
    _, budget, _, _ = data
    joint = budget.chassis_joint
    assert joint.station_count == 12
    assert len(joint.corner_stations) == 4
    assert len(joint.side_stations) == 6
    assert len(joint.end_stations) == 2
    centres = {(round(s.x, 6), round(s.y, 6)) for s in joint.stations}
    assert len(centres) == 12
    centreline = [s for s in joint.stations if abs(s.x) < 1e-9]
    assert len(centreline) == 2
    assert {round(s.y, 6) for s in centreline} == {
        round(-joint.depth / 2.0 + joint.side_inset, 6),
        round(joint.depth / 2.0 - joint.side_inset, 6),
    }


def test_stations_mirror_about_both_centreplanes(data):
    """The long walls and the corners mirror both ways.

    The two short-side stations cannot: the narrow case leaves no band beside
    the keyboard, so they sit in the free band *behind* it, which only exists
    at one end. They mirror about the X centreplane alone.
    """
    _, budget, _, _ = data
    joint = budget.chassis_joint
    wall_points = {
        (round(s.x, 6), round(s.y, 6))
        for s in joint.stations
        if not s.is_end
    }
    for x, y in wall_points:
        assert (-x, y) in wall_points
        assert (x, -y) in wall_points
        assert (-x, -y) in wall_points
    end_points = {(round(s.x, 6), round(s.y, 6)) for s in joint.end_stations}
    assert len(end_points) == 2
    for x, y in end_points:
        assert (-x, y) in end_points
        assert y > 0.0


def test_parting_plane_and_band_are_derived(data):
    config, budget, frame, _ = data
    joint = budget.chassis_joint
    assert joint.parting_z == pytest.approx(frame.parting_z)
    assert joint.parting_z == pytest.approx(
        min(
            config.parting.max,
            max(config.parting.min, config.parting.front_wall_fraction * budget.chassis_top),
        )
    )
    # The band is split evenly around the Parting plane.
    assert joint.band_z0 == pytest.approx(joint.parting_z - joint.band / 2.0)
    assert joint.band_z1 == pytest.approx(joint.parting_z + joint.band / 2.0)
    assert joint.band_z1 < budget.chassis_top - config.wall_thickness
    # Both halves are prismatic (ADR-0019): the Tray no longer drafts inward,
    # so the base and the band are the closed-face width.
    assert joint.band_width == pytest.approx(budget.width)
    assert joint.base_width == pytest.approx(budget.width)
    assert frame.chassis_base_width == pytest.approx(joint.base_width)
    assert frame.chassis_band_width == pytest.approx(joint.band_width)


def test_screw_reaches_the_insert(data):
    """ADR-0021: the head is buried one wall below the Parting plane.

    The grip is therefore exactly one wall -- not the whole floor depth -- so
    the shortest M3 stock length that still fills the insert is the M3x6.
    """
    config, budget, _, _ = data
    joint = budget.chassis_joint
    assert joint.grip == pytest.approx(config.wall_thickness)
    assert joint.recess.z_seat == pytest.approx(
        joint.parting_z - config.wall_thickness
    )
    assert joint.screw.name == "M3x6"
    assert joint.screw.engagement <= joint.insert_depth + 1e-9
    assert joint.screw.engagement >= float(joint.screw.size.lstrip("M")) - 1e-9


def test_column_stays_inside_the_floor_skin(data):
    config, budget, _, _ = data
    joint = budget.chassis_joint
    minimum = config.material.minimum_feature
    # The countersink lives in the 2 mm floor, *below* the column's base, so it
    # does not bound the column: the screw shank does, and the floor's skin
    # bounds the countersink itself.
    shank = fasteners.screw(joint.screw.size).clearance
    for station in joint.stations:
        assert 0.0 < station.base_boss <= station.boss
        assert station.base_boss >= shank + 2.0 * minimum - 1e-6
        # The column's outer surface stays inside the Tray's floor skin.
        assert station.base_distance >= station.base_boss / 2.0 + minimum - 1e-6
        # The recess keeps a printable skin to the outer face.
        assert (
            station.edge_margin
            >= minimum - 1e-6
        )


# -- geometry ------------------------------------------------------------
def test_tray_and_deck_meet_at_the_parting_plane(data, solids):
    _, _, frame, _ = data
    tray, deck = solids
    tray_box = ch.bounding_box(tray)
    deck_box = ch.bounding_box(deck)
    assert tray_box.zmin == pytest.approx(0.0, abs=0.01)
    assert tray_box.zmax == pytest.approx(frame.parting_z, abs=0.01)
    assert deck_box.zmin == pytest.approx(frame.parting_z, abs=0.01)
    assert deck_box.zmax == pytest.approx(frame.chassis_top, abs=0.01)
    # The silhouette is continuous across the joint: the prismatic band is the
    # closed-face width on both sides of the plane.
    assert _width_at(tray, frame.parting_z - 0.005) == pytest.approx(
        frame.chassis_band_width, abs=0.01
    )
    assert _width_at(deck, frame.parting_z + 0.005) == pytest.approx(
        frame.chassis_band_width, abs=0.01
    )


def test_the_tray_and_the_deck_are_prismatic(data, solids):
    """ADR-0019: the Tray's X walls are vertical, so the silhouette is straight.

    The only taper left on the Tray is the base draft on its end walls, and
    that only leans the depth (the cavity follows, so the wall keeps its
    thickness); the X silhouette is one width from the table to the closed
    face.
    """
    config, budget, frame, _ = data
    tray, deck = solids
    taper = budget.base_taper
    assert taper.height == pytest.approx(frame.chassis_band_z0)
    assert taper.height < frame.parting_z
    for z in (0.5, frame.chassis_band_z0 + 0.5, frame.parting_z - 0.5):
        assert _width_at(tray, z) == pytest.approx(frame.width, abs=0.05)
    # Deck: one prismatic block, with no flare back out toward the face.
    for z in (frame.parting_z + 0.5, frame.chassis_top / 2.0 + 5.0, frame.chassis_top - 0.5):
        assert _width_at(deck, z) == pytest.approx(frame.width, abs=0.05)


def test_the_tray_end_walls_leave_the_table_with_a_base_taper(data, solids):
    """ADR-0019: the vertical end walls read as a taper up to the band.

    Between the station pads the outer face leans out over ``taper.height``;
    above it, and inside a pad, the face is the full depth again.
    """
    _, budget, frame, _ = data
    tray, _ = solids
    taper = budget.base_taper
    half = frame.depth / 2.0
    # A point on a taper run, clear of every stop circle.
    x = sum(taper.segments[0]) / 2.0
    z = taper.height / 2.0
    face = taper.face_y(z)
    assert face < half - 0.3
    assert _material_at(tray, x, face - 0.4, z) > 0
    assert _material_at(tray, x, face + 0.4, z) == pytest.approx(0)
    # Above the taper the full depth is back.
    assert _material_at(tray, x, half - 0.4, taper.height + 0.5) > 0
    # The pads keep the full face at the table.
    station = next(
        s for s in budget.chassis_joint.stations
        if abs(abs(s.y) - (half - budget.chassis_joint.side_inset)) < 1e-9
    )
    assert _material_at(tray, station.x, half - 0.4, taper.height / 2.0) > 0


def test_tray_and_deck_are_valid_and_rejoin(solids):
    tray, deck = solids
    assert tray.is_valid and deck.is_valid
    assert len(tray.solids()) == 1 and len(deck.solids()) == 1
    whole = ch.make_compound([tray, deck])
    assert ch.volume_mm3(whole) == pytest.approx(
        ch.volume_mm3(tray) + ch.volume_mm3(deck), rel=1e-6
    )


def test_every_station_has_a_screw_hole_through_the_tray(data, solids):
    _, budget, frame, _ = data
    joint = budget.chassis_joint
    tray, _ = solids
    z = frame.parting_z / 2.0
    for station in joint.stations:
        assert _material_at(tray, station.x, station.y, z) == pytest.approx(0)
    # The column around the hole stays solid just outside the cone mouth,
    # probed near the floor where the frustum is at its widest (an end
    # station's column can stand free of the X wall -- the probe must sit
    # inside the column, not in the wall).
    z_floor = 0.5
    for station in joint.stations:
        offset = station.mouth_radius + 0.3
        px = station.x + station.normal[0] * offset
        py = station.y + station.normal[1] * offset
        assert _material_at(tray, px, py, z_floor) > 0


def test_the_deep_cone_buries_the_head_and_widens_to_the_floor(data, solids):
    """ADR-0021: the head seats one wall below the Parting plane.

    The access cavity is one wall deep above the head (the skin), the head
    pocket is empty down to the seat, and the cone widens from the pocket's
    neck to the floor face, keeping one minimum feature inside the column's
    footprint so the pier's wall at the floor is thick (never a knife edge).
    """
    config, budget, _, _ = data
    joint = budget.chassis_joint
    tray, _ = solids
    recess = joint.recess
    station = joint.side_stations[0]
    assert station.mouth_radius == pytest.approx(
        station.base_boss / 2.0 - config.material.minimum_feature
    )
    # Radially outward from the screw axis, in unit X.
    def at(radius, z):
        return _material_at(tray, station.x + radius, station.y, z)

    # The seat ring between the clearance hole and the pocket wall carries the
    # head; the skin above it is exactly one wall and never cut through.
    ring = (fasteners.screw(joint.screw.size).clearance / 2.0 + recess.pocket_radius) / 2.0
    assert at(ring, recess.z_seat - 0.2) == pytest.approx(0)
    assert at(ring, recess.z_seat + config.wall_thickness / 2.0) > 0
    # The pocket is empty; below the neck the cone has widened past it, so a
    # narrow probe at one radius reads material at the neck and void at the
    # floor.
    def narrow(radius, z):
        probe = ch.translate(
            ch.box_centered(0.1, 0.1, 0.1), station.x + radius, station.y, z
        )
        return ch.volume_mm3(ch.intersect(tray, probe))

    between = (recess.pocket_radius + station.mouth_radius) / 2.0
    assert narrow(between, recess.z_neck - 0.4) > 0
    assert narrow(between, 0.3) == pytest.approx(0)
    # The pier's wall at the floor: material just outside the mouth, empty
    # well inside it.
    assert at(station.mouth_radius + 0.45, 0.3) > 0
    assert at(station.mouth_radius - 0.45, 0.3) == pytest.approx(0)


def test_the_column_is_strict_above_the_neck(data, solids):
    """ADR-0021: from the cone's neck to the plane the column is a plain
    cylinder with strict dimensions (pocket + one minimum feature a side),
    below the neck a frustum down to the floor footprint."""
    config, budget, _, _ = data
    joint = budget.chassis_joint
    tray, _ = solids
    minimum = config.material.minimum_feature
    for station in joint.stations:
        assert station.strict_boss == pytest.approx(
            2.0 * (joint.recess.pocket_radius + minimum)
        )
        assert station.base_boss >= station.strict_boss - 1e-9
    # The cone's cavity below the neck stays inside the frustum: at the floor
    # the wall between the cone and the column footprint is one minimum
    # feature, so the pier there is the skin lip plus that feature.
    station = joint.side_stations[0]
    assert station.edge_margin == pytest.approx(
        station.margin - station.base_boss / 2.0 + minimum
    )
    # The cavity is empty right down to the floor face along the axis.
    assert _material_at(
        tray, station.x, station.y, joint.recess.z_neck - 0.5
    ) == pytest.approx(0)


def test_every_station_has_an_insert_hole_in_the_deck(data, solids):
    _, budget, frame, _ = data
    joint = budget.chassis_joint
    _, deck = solids
    z = frame.parting_z + joint.insert_depth / 2.0
    for station in joint.stations:
        assert _material_at(deck, station.x, station.y, z) == pytest.approx(0)


def test_the_band_skin_is_plain_at_every_station(data, solids):
    """No relief is cut into the band: the outer face stays flush (ADR-0016)."""
    _, budget, frame, _ = data
    joint = budget.chassis_joint
    tray, deck = solids
    for part, z in (
        (tray, frame.parting_z - 1.5),
        (deck, frame.parting_z + 1.5),
    ):
        for station in joint.stations:
            if station.is_corner:
                # The corner's outer face is the 45 degree chop, tested below.
                continue
            nx, ny = station.normal
            # 0.2 mm inside the outer face: material, not a relief floor.
            x = station.x + nx * (station.surface - 0.2)
            y = station.y + ny * (station.surface - 0.2)
            assert _material_at(part, x, y, z) > 0, (
                f"the band is cut at {station.kind} ({station.x:.2f}, "
                f"{station.y:.2f})"
            )


def test_each_chamfered_corner_keeps_a_full_wall(data, solids):
    """The cavity follows the outer chop, so no corner pinches to nothing.

    Before ADR-0016 a square cavity corner met the 4 mm outer chamfer at a
    knife edge on the 2 mm wall: half way along the corner diagonal there was
    neither material nor a free face.
    """
    config, _, frame, _ = data
    tray, deck = solids
    chamfer = config.corners.chamfer
    hx = frame.chassis_band_width / 2.0
    hy = frame.depth / 2.0
    root = math.sqrt(0.5)
    # Apex -> outer chamfer face, and the wall behind it.
    outer_face = chamfer * root
    for part, z in (
        (tray, frame.parting_z - 1.5),
        (deck, frame.parting_z + 1.5),
    ):
        for sx in (-1, 1):
            for sy in (-1, 1):
                ax, ay = sx * hx, sy * hy
                nx, ny = sx * root, sy * root

                def at(d: float) -> float:
                    return _material_at(part, ax - nx * d, ay - ny * d, z)

                assert at(outer_face - 0.4) == pytest.approx(0), "the chop is gone"
                # The old pinch point and a point one wall behind it: solid.
                for d in (outer_face + 0.4, outer_face + 1.3):
                    assert at(d) > 0, (
                        f"the corner at ({ax:.1f}, {ay:.1f}) is open at {d:.2f} mm"
                    )


def test_tray_and_deck_sections_fit_and_rejoin(data, solids):
    config, _, frame, _ = data
    wall = config.wall.thickness
    from geometry.split import split_part

    for part, name in zip(solids, ("chassis_tray", "chassis_deck")):
        sections = split_part(part, config.slide.split[name], frame.depth, wall)
        assert sum(ch.volume_mm3(s) for s in sections) == pytest.approx(
            ch.volume_mm3(part), rel=1e-3
        )
        for section in sections:
            x, y, z = ch.bounding_box_mm(section)
            assert x <= BUILD_VOLUME[0] + 1e-6
            assert y <= BUILD_VOLUME[1] + 1e-6
            assert z <= BUILD_VOLUME[2] + 1e-6
