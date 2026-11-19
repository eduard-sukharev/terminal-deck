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


def _vertex_zmin(shape):
    return min(v.Z for v in shape.vertices())


def _vertex_zmax(shape):
    return max(v.Z for v in shape.vertices())


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
    # The bed/top extremes are read at the vertices: a fillet face's
    # control-point hull can overshoot the actual surface (ADR-0023), so the
    # plain bounding box is conservative there.
    assert _vertex_zmin(tray) == pytest.approx(0.0, abs=0.01)
    assert _vertex_zmax(tray) == pytest.approx(frame.parting_z, abs=0.01)
    assert _vertex_zmin(deck) == pytest.approx(frame.parting_z, abs=0.01)
    assert _vertex_zmax(deck) == pytest.approx(frame.chassis_top, abs=0.01)
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

    Between the corner pads the outer face leans out over ``taper.height``;
    above it, and inside a pad, the face is the full depth again. The probe
    sits mid-run, clear of the side stations' cones (the taper passes through
    them now).
    """
    _, budget, frame, _ = data
    tray, _ = solids
    taper = budget.base_taper
    half = frame.depth / 2.0
    wall_y = taper.half_depth - budget.chassis_joint.side_inset
    side_xs = [
        abs(s.x)
        for s in budget.chassis_joint.stations
        if abs(abs(s.y) - wall_y) < 1e-9 and not s.is_corner
    ]
    x = (max(side_xs) + taper.segments[0][1]) / 2.0
    z = taper.height / 2.0
    face = taper.face_y(z)
    assert face < half - 0.3
    assert _material_at(tray, x, face - 0.4, z) > 0
    assert _material_at(tray, x, face + 0.4, z) == pytest.approx(0)
    # Above the taper the full depth is back.
    assert _material_at(tray, x, half - 0.4, taper.height + 0.5) > 0
    # The pads keep the full face at the table.
    station = next(
        s
        for s in budget.chassis_joint.stations
        if abs(abs(s.y) - wall_y) < 1e-9 and s.is_corner
    )
    sy = math.copysign(half - 0.4, station.y)
    assert _material_at(tray, station.x, sy, taper.height / 2.0) > 0


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
    taper = budget.base_taper
    tray, _ = solids
    z = frame.parting_z / 2.0
    for station in joint.stations:
        assert _material_at(tray, station.x, station.y, z) == pytest.approx(0)
    # A column at every station, probed where the slice leaves it. The taper
    # cuts through the long-wall bosses: below the lip crossing the sloped
    # face is inside the cone mouth, so nothing of the column is left at the
    # table; above it the pier ring is intact. The end and corner stations
    # keep their columns to the table.
    z_pier = taper.height - 0.15
    z_floor = 0.5
    wall_y = taper.half_depth - joint.side_inset
    for station in joint.stations:
        offset = station.mouth_radius + 0.3
        px = station.x + station.normal[0] * offset
        py = station.y + station.normal[1] * offset
        on_tapered_wall = abs(abs(station.y) - wall_y) <= 1e-9
        if on_tapered_wall and not station.is_corner:
            # ADR-0023: the taper's slice passes through the boss -- at the
            # table the sloped face sits inside the cone, the boss is cut away.
            assert _material_at(tray, px, py, z_floor) == pytest.approx(0)
            # ...and the pier ring around the pocket survives above the lip.
            assert _material_at(tray, px, py, z_pier) > 0
        else:
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


# -- ADR-0023: the cone edge fillets ---------------------------------------
@pytest.fixture(scope="module")
def unfilleted_tray(data):
    """The Tray before the cone edge fillets, for selector assertions."""
    from geometry import edge_treatment

    original = edge_treatment.round_cone_cut
    edge_treatment.round_cone_cut = lambda body, *args, **kwargs: body
    try:
        config, _, frame, _ = data
        yield Chassis(config, frame).build_tray()
    finally:
        edge_treatment.round_cone_cut = original


def test_the_taper_fillet_selects_only_the_cones_edges(data, unfilleted_tray):
    from geometry.edge_treatment import cone_cut_edges

    _, budget, _, _ = data
    taper = budget.base_taper
    recess = budget.chassis_joint.recess
    rims, lips = cone_cut_edges(unfilleted_tray, taper.angle, 0.0)
    assert rims and lips
    # every selected edge is an arc of a cone: the long straight edges where
    # the walls meet the floor are never picked
    assert all(i.curve_type in ("circle", "ellipse") for i in rims + lips)
    # rims are the mouth rings at the bed face -- nothing from the cavity
    # floor at one wall above it
    assert all(abs(i.key[2]) < 0.01 for i in rims)
    # lips sit on the taper's outer slope, below the pocket's neck
    assert all(1.0 < i.key[2] < recess.z_neck for i in lips)


def test_the_wall_floor_edges_stay_sharp_after_the_fillet(data, solids):
    _, budget, frame, _ = data
    tray, _ = solids
    # the taper's long floor edge on each wall is still a straight segment:
    # filleting it would have replaced it with a curved surface
    lines = 0
    for face in ch.faces(tray):
        for wire in face.wires():
            for edge in wire.edges():
                info = ch.edge_info(edge)
                if (
                    info.curve_type == "line"
                    and abs(info.key[2]) < 0.02
                    and info.length > 50.0
                    and abs(info.tangent[0]) > 0.9
                ):
                    lines += 1
    assert lines >= 2
    # ...and the fillet did not wander below the bed or into the parting plane
    assert _vertex_zmin(tray) == pytest.approx(0.0, abs=0.01)
    assert _vertex_zmax(tray) == pytest.approx(frame.parting_z, abs=0.01)


# -- ADR-0024: the columns merge into the cavity walls ---------------------
def _wall_chord_half(joint, frame, config, radius: float) -> tuple[float, float]:
    """``(half chord, wall face Y)`` for a column of ``radius`` on a long wall."""
    wall = config.wall.thickness
    face = frame.depth / 2.0 - wall
    axis = frame.depth / 2.0 - joint.side_inset
    return math.sqrt(radius**2 - (face - axis) ** 2), face


def test_columns_merge_into_the_cavity_walls(data, solids):
    """Both halves fillet the chords where a column crosses the front/rear wall.

    The reentrant corner beside each chord is a crack starter in the most
    handled part of the case; ``chassis_joint.column_fillet`` fills it, so the
    material reaches past the chord where the sharp corner would be air.
    """
    from geometry.edge_treatment import column_junction_edges

    config, budget, frame, _ = data
    tray, deck = solids
    joint = budget.chassis_joint
    merge = config.chassis_joint.column_fillet
    station = next(s for s in joint.side_stations if s.x > 1e-6 and s.y > 0.0)
    columns = [
        (
            s.x,
            s.y,
            min(s.strict_boss, s.base_boss) / 2.0,
            max(s.strict_boss, s.base_boss) / 2.0,
        )
        for s in joint.stations
    ]

    # The Tray's own column is strict above the access cone's neck; the Deck's
    # band boss is a plain cylinder of `station.boss`.
    for shape, radius, z in (
        (tray, station.strict_boss / 2.0, joint.band_z0 + 1.0),
        (deck, station.boss / 2.0, (joint.parting_z + frame.chassis_top) / 2.0),
    ):
        half, face = _wall_chord_half(joint, frame, config, radius)
        assert half > merge, "the fillet has to fit the chord (HARD check)"
        # ...and no chord is left untreated on either half.
        assert column_junction_edges(shape, columns, face) == []
        for dx in (merge * 0.4, merge * 0.7):
            for dy in (0.3, merge * 0.4):
                assert _material_at(
                    shape, station.x + half + dx, face - dy, z
                ) > 1e-6, (
                    f"the merge fillet is missing {dx:.2f} past the chord at "
                    f"z {z:.2f}"
                )


def _probe(shape, x, y, z, size=0.1):
    """Material in a tiny box centered at ``x, y, z`` (mm^3)."""
    box = ch.translate(ch.box_centered(size, size, size), x, y, z)
    return ch.volume_mm3(ch.intersect(shape, box))


def test_boss_bases_are_filleted_on_the_plane_they_spring_from(data, solids):
    """ADR-0025: every boss stands on its base and the ring is rounded.

    Both halves are judged in their own print orientation: the Tray as
    modelled (a column stands on the floor), the Deck face down (the inner
    ceiling is the bed face, so its bosses stand on it).
    """
    from geometry.edge_treatment import boss_base_edges
    from geometry.printability import BED_DOWN, FACE_DOWN

    config, budget, frame, _ = data
    tray, deck = solids
    joint = budget.chassis_joint
    base = config.chassis_joint.boss_base_fillet
    station = next(s for s in joint.side_stations if s.x > 1e-6 and s.y > 0.0)
    columns = [
        (
            s.x,
            s.y,
            min(s.strict_boss, s.base_boss) / 2.0,
            max(s.strict_boss, s.base_boss) / 2.0,
        )
        for s in joint.stations
    ]
    ceiling = frame.chassis_top - frame.wall

    # The Tray's columns: no base ring is left on the floor.
    assert boss_base_edges(tray, columns, frame.wall, 1.0, BED_DOWN) == []
    # The Deck's front/rear band bosses: no base ring is left on the ceiling.
    column = (
        station.x,
        station.y,
        min(station.strict_boss, station.base_boss) / 2.0,
        max(station.strict_boss, station.base_boss) / 2.0,
    )
    assert boss_base_edges(deck, [column], ceiling, -1.0, FACE_DOWN) == []

    # ...and the fillet is material where the sharp corner was air: just
    # outside the boss wall and just above (Tray) / below (Deck) the plane.
    radius = station.strict_boss / 2.0
    inward = station.y - (radius + base * 0.25)
    assert _probe(tray, station.x, inward, frame.wall + base * 0.1) > 0.0
    assert _probe(deck, station.x, inward, ceiling - base * 0.1) > 0.0
