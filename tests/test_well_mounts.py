"""Plate boss stations and ear outlines (ADR-0014, issues #11 and #18).

Pure-data tests: the eight M2 insert bosses under the Deck's Well, the ears the
plate grows to reach them, and the notches the existing chassis band joint
forces into the plate border. The Deck (T3) cuts the bosses onto the Well
ring's outer face; the plate (T4) cuts the clearance holes, the ears and the
notches. The at-Seam pair straddles the plate's real Seam at each end, so each
Section keeps four stations. Nothing here needs a CAD library.

Every expected value is derived from the configuration, the fastener library,
the slide budget and the keyboard's Seam. The few literal numbers stated
(Ø6.0 boss, Ø3.0 bore, 4.6 mm ear, the -50.584 spacebar-row Seam end) are the
arithmetic on those sources spelled out, so a parameter change moves the model
and the test together.
"""

import dataclasses
import math

import pytest

from components.slide import compute_slide_budget
from geometry.well_mounts import (
    Ear,
    Obstacle,
    PlanRect,
    PlateFrame,
    PlateNotch,
    SeamPath,
    bearing_seat_obstacles,
    plate_cutouts,
    well_mounts,
)
from keyboard.geometry.seam import RowSeam
from layouts import make_layout
from main import BuildPipeline
from utilities import fasteners
from utilities.config_loader import Wall


@pytest.fixture(scope="module")
def data():
    pipeline = BuildPipeline("config/default.yaml", layout_name="slider")
    config = pipeline.load_config()
    components = pipeline.load_components()
    placements = make_layout("slider", components, config=config).placements()
    budget = compute_slide_budget(config, components)
    return config, components, budget, placements


@pytest.fixture(scope="module")
def seam(data):
    """The plate's real split Seam -- the row-jogging path of #15."""
    _, components, _, _ = data
    return components["keyboard"].plate_model().seam


@pytest.fixture(scope="module")
def keyboard_placement(data):
    """The keyboard's placement: the plate's frame in the chassis (issue #19)."""
    _, components, _, placements = data
    keyboard = components["keyboard"]
    return next(p for p in placements if p.component is keyboard)


@pytest.fixture(scope="module")
def frame(data, keyboard_placement):
    """The one plate frame: the Well's plate, placed by the layout."""
    _, _, budget, _ = data
    return PlateFrame.from_placement(
        keyboard_placement,
        width=budget.well.plate_width,
        depth=budget.well.plate_depth,
    )


@pytest.fixture(scope="module")
def mounts(data, seam, frame):
    config, _, budget, _ = data
    return well_mounts(config, budget, seam=seam, frame=frame)


def _screw(config) -> str:
    return str((config.keyboard.mounting or {}).get("screw", "M2"))


def _plate_rect(budget) -> PlanRect:
    """The plate's plan rectangle, derived exactly as the module derives it."""
    well = budget.well
    front = -budget.chassis_height / 2.0 + well.ring + well.front_lip
    return PlanRect(
        -well.plate_width / 2.0,
        front,
        well.plate_width / 2.0,
        front + well.plate_depth,
    )


def _switch_cutouts(components) -> tuple[PlanRect, ...]:
    """The real switch cutouts, as plate-local rectangles.

    Read through the same production helper the pipeline passes to
    ``well_mounts``, so the test cannot disagree with the build about which
    openings the pattern must clear.
    """
    return plate_cutouts(components["keyboard"].plate_model())


# -- the pattern ---------------------------------------------------------


def test_eight_stations_four_per_plate_section(mounts):
    assert len(mounts.mounts) == 8
    for section in ("left", "right"):
        per_section = [m for m in mounts.mounts if m.section == section]
        assert len(per_section) == 4
        assert sorted(m.station for m in per_section) == [
            "front-outer",
            "front-seam",
            "rear-outer",
            "rear-seam",
        ]
    assert len({(round(m.x, 6), round(m.y, 6)) for m in mounts.mounts}) == 8


def test_mount_names_are_unique_and_say_which_section(mounts):
    names = [m.name for m in mounts.mounts]
    assert len(set(names)) == 8
    for mount in mounts.mounts:
        assert mount.station in mount.name
        assert mount.name.endswith(mount.section)


def test_outer_stations_mirror_and_seam_pairs_straddle_the_seam(mounts):
    """Only the outer pair mirrors about the centreplane.

    The at-Seam stations straddle the plate Seam where it *ends*, and the real
    Seam is not centred (its spacebar-row end is the jog), so those pairs sit on
    either side of their own Seam end, not symmetrically about x = 0. A station
    that the chassis forces inboard (issue #19) is walked toward the Seam, so a
    pair need not be equidistant either -- it still clamps both Sections.
    """
    for station in ("front-outer", "rear-outer"):
        left = mounts.mount(f"{station}-left")
        right = mounts.mount(f"{station}-right")
        assert left.world_xy[1] == pytest.approx(right.world_xy[1])
        assert left.world_xy[0] == pytest.approx(-right.world_xy[0])
        # The plate frame is a point reflection, so the local pattern mirrors too.
        assert left.plate_xy[0] == pytest.approx(-right.plate_xy[0])
        assert left.plate_xy[1] == pytest.approx(right.plate_xy[1])
        assert left.ear is not None and right.ear is not None
        assert right.ear.rect.x0 == pytest.approx(-left.ear.rect.x1)
        assert right.ear.rect.x1 == pytest.approx(-left.ear.rect.x0)
        assert right.ear.rect.y0 == pytest.approx(left.ear.rect.y0)

    for station, seam_x in (
        ("front-seam", mounts.seam_front),
        ("rear-seam", mounts.seam_rear),
    ):
        left = mounts.mount(f"{station}-left")
        right = mounts.mount(f"{station}-right")
        assert left.world_xy[1] == pytest.approx(right.world_xy[1])
        # One station on each side of that end's world Seam segment ...
        assert min(left.x, right.x) < seam_x < max(left.x, right.x)
        # ... each on its own Section ...
        assert left.section != right.section
        # ... and the two ears do not meet across it.
        left_ear, right_ear = left.ear.rect, right.ear.rect
        assert (
            left_ear.x1 <= right_ear.x0 + 1e-9
            or right_ear.x1 <= left_ear.x0 + 1e-9
        )
        # Same tab, just translated: an ear never changes size with the Seam.
        assert left.ear.rect.width == pytest.approx(right.ear.rect.width)
        assert left.ear.rect.depth == pytest.approx(right.ear.rect.depth)


# -- one source for the boss ---------------------------------------------


def test_boss_diameter_is_the_insert_hole_plus_two_margins(data, mounts):
    config, _, _, _ = data
    insert = fasteners.heat_insert(_screw(config))
    margin = config.chassis_joint.boss_margin
    assert mounts.insert_hole_diameter == pytest.approx(insert.printed_hole_diameter)
    assert mounts.insert_depth == pytest.approx(insert.depth)
    assert mounts.boss_diameter == pytest.approx(
        insert.printed_hole_diameter + 2.0 * margin
    )
    # One source: every mount reports the module's single diameter.
    assert {m.boss_diameter for m in mounts.mounts} == {mounts.boss_diameter}
    # Today: a Ø6.0 boss around the Ø3.0 M2 insert bore.
    assert mounts.boss_diameter == pytest.approx(6.0)


def test_boss_runs_from_the_plate_top_up_to_the_deck_ceiling(data, mounts):
    """The boss is a full column: face down it stands on the Deck's top slab."""
    config, _, budget, _ = data
    ceiling = budget.chassis_top - config.wall_thickness
    for mount in mounts.mounts:
        assert mount.boss_z0 == pytest.approx(mounts.plate_top)
        assert mount.boss_z1 == pytest.approx(ceiling)
        assert mount.boss_z1 - mount.boss_z0 == pytest.approx(mounts.boss_height)
        # The insert bottomed in the boss still has printable material above it.
        assert mount.boss_z1 - mount.boss_z0 >= mounts.insert_depth


def test_a_ceiling_that_cannot_hold_the_insert_fails(data, seam, frame):
    """A column is only printable to the ceiling if the ceiling is high enough."""
    config, _, budget, _ = data
    shallow = dataclasses.replace(budget, chassis_top=budget.well.plate_top + 2.0)
    result = well_mounts(config, shallow, seam=seam, frame=frame)
    assert not result.ok
    assert any("insert" in reason for reason in result.failures)


def test_the_screw_is_a_derived_stock_length(data, mounts):
    """The plate screw comes from the grip and the insert, like every joint."""
    config, _, budget, _ = data
    screw = fasteners.screw(_screw(config))
    insert = fasteners.heat_insert(_screw(config))
    # The head seats on the plate's underside, so the grip is the plate.
    assert mounts.screw_grip == pytest.approx(budget.well.plate_thickness)
    assert mounts.screw_name == f"{mounts.screw}x{mounts.screw_length}"
    assert mounts.screw_engagement == pytest.approx(
        mounts.screw_length - mounts.screw_grip
    )
    assert mounts.screw_engagement >= float(mounts.screw.lstrip("M"))
    assert mounts.screw_engagement <= mounts.insert_depth
    # Today: a 1.5 mm plate over a 3.0 mm insert leaves the stock M2x4.
    assert mounts.screw_name == "M2x4"
    assert mounts.screw_length == 4
    assert mounts.screw_engagement == pytest.approx(2.5)
    # The head is the library's, and a 1.5 mm plate cannot recess it.
    assert mounts.head_diameter == pytest.approx(screw.head_diameter)
    assert mounts.head_depth == pytest.approx(screw.head_depth)
    assert (
        mounts.plate_bottom - mounts.head_depth
        < budget.chassis_joint.parting_z
    )


# -- the lips ------------------------------------------------------------


def test_front_and_rear_stations_sit_in_the_lips_at_the_ring(data, mounts):
    config, _, budget, _ = data
    well = budget.well
    bore_margin = config.merged_boss.bore_margin
    plan = _plate_rect(budget)
    for mount in mounts.mounts:
        front = mount.station.startswith("front")
        # Work in "outboard of the ring's outer face" distances (mm).
        ring_face = plan.y0 if front else plan.y1
        lip = well.front_lip if front else well.rear_lip
        out = -1.0 if front else 1.0
        station_out = out * (mount.y - ring_face)
        # The bore's edge keeps `bore_margin` from the ring: the boss may merge
        # into the ring's outer face, its bore may not.
        assert station_out == pytest.approx(
            bore_margin + mounts.insert_hole_diameter / 2.0
        )
        # The boss overlaps the ring's outer face (it is merged into the wall)
        # but never reaches the ring's inner face, i.e. the Cutout ...
        assert -well.ring < station_out - mount.boss_diameter / 2.0 < 0.0
        # ... and the whole boss stays inside the lip.
        assert 0.0 < station_out + mount.boss_diameter / 2.0 <= lip + 1e-9


def test_the_front_lip_hosts_the_boss(data, mounts):
    """ADR-0014's open measurement: the front lip is the tightest host.

    A merged boss needs only the bore margin towards the ring (the ring *is*
    the merged wall), so the lip must be `bore_margin + hole + boss_margin`.
    """
    config, _, budget, _ = data
    required = (
        config.merged_boss.bore_margin
        + mounts.insert_hole_diameter
        + config.chassis_joint.boss_margin
    )
    assert mounts.lip_required == pytest.approx(required)
    assert budget.well.front_lip >= required - 1e-9
    assert mounts.front_lip_slack == pytest.approx(budget.well.front_lip - required)
    # Today: 5.65 mm of front lip for a 5.00 mm boss, 0.65 mm to spare.
    assert mounts.front_lip_slack == pytest.approx(0.65, abs=1e-6)


# -- ears ----------------------------------------------------------------


def test_every_station_has_an_ear_that_holds_the_clearance_hole(data, mounts):
    config, _, budget, _ = data
    screw = fasteners.screw(_screw(config))
    edge = config.chassis_joint.boss_margin
    for mount in mounts.mounts:
        ear = mount.ear
        assert isinstance(ear, Ear)
        hole = PlanRect.from_centre(*mount.plate_xy, screw.clearance, screw.clearance)
        assert ear.rect.contains_inner(hole, edge)
        assert ear.thickness == pytest.approx(budget.well.plate_thickness)
        # The ear is an extension outboard of the ring under the station: the
        # hole's centre sits one (bore margin + hole radius) into the lip, and
        # the ear reaches one (hole radius + edge margin) past it.
        protrusion = (
            mounts.insert_hole_diameter / 2.0 + mounts.bore_margin
            + ear.rect.width / 2.0
        )
        assert protrusion == pytest.approx(
            (mounts.insert_hole_diameter / 2.0 + mounts.bore_margin)
            + (screw.clearance / 2.0 + edge)
        )
        assert ear.fillet is not None and ear.fillet > 0.0
        assert ear.overlap >= config.material.minimum_feature
        # Today: a 4.6 mm ear around the Ø2.2 hole, r2.0 ends.
        assert protrusion == pytest.approx(4.6)
        assert ear.fillet == pytest.approx(2.0)


def test_ears_exist_because_the_border_cannot_hold_the_hole(data, mounts):
    """The ring-width border is too narrow for the hole plus its margins."""
    config, _, budget, _ = data
    screw = fasteners.screw(_screw(config))
    edge = config.chassis_joint.boss_margin
    assert budget.well.ring < screw.clearance + 2.0 * edge
    frame = mounts.frame
    for mount in mounts.mounts:
        front = mount.station.startswith("front")
        # The plain plate border under the ring, at this station's X. The plate
        # is placed rotated, so the world front lip is the local +Y edge.
        if front:
            border = PlanRect(
                mount.ear.rect.x0, frame.depth / 2.0 - budget.well.ring,
                mount.ear.rect.x1, frame.depth / 2.0,
            )
        else:
            border = PlanRect(
                mount.ear.rect.x0, -frame.depth / 2.0,
                mount.ear.rect.x1, -frame.depth / 2.0 + budget.well.ring,
            )
        hole = PlanRect.from_centre(*mount.plate_xy, screw.clearance, screw.clearance)
        assert not border.contains_inner(hole, edge)


def test_ears_stay_inside_their_lip_and_off_the_wall(data, mounts):
    config, _, budget, _ = data
    well = budget.well
    plate = _plate_rect(budget)
    for mount in mounts.mounts:
        ear = mounts.frame.to_plan_rect(mount.ear.rect)
        if mount.station.startswith("front"):
            gap = ear.y0 - (plate.y0 - well.front_lip)
        else:
            gap = (plate.y1 + well.rear_lip) - ear.y1
        # The ear ends inside the lip, clear of the Deck's end wall.
        assert gap >= config.clearance.shell - 1e-9
        # And inside the plate's X envelope.
        assert ear.x0 >= plate.x0 - 1e-9
        assert ear.x1 <= plate.x1 + 1e-9


# -- the Seam ------------------------------------------------------------


def _seam_x_at(model, y: float) -> float:
    """The plate Seam's X at plate-local ``y`` (the test's own reading)."""
    bands = model.seam.segments(model.metadata.height)
    for y0, y1, x in bands:
        if y0 <= y <= y1:
            return x
    return bands[0][2] if y < bands[0][0] else bands[-1][2]


def _jog_rear(seam, x: float) -> RowSeam:
    """The real Seam with its rear (spacebar) segment moved to ``x``."""
    bands = [list(band) for band in seam.bands]
    bands[-1][2] = x
    return RowSeam(tuple(tuple(band) for band in bands))


def test_at_seam_stations_straddle_each_end_of_the_real_seam(data, mounts):
    config, components, _, _ = data
    model = components["keyboard"].plate_model()
    # The pinned, intended pattern: the at-Seam station sits 7.20 mm off its
    # Seam segment (ear 2.60 + printable minimum 0.60 + 4.00 Section slack).
    assert mounts.seam_clearance == pytest.approx(7.20, abs=0.01)
    assert mounts.seam_clearance == pytest.approx(
        mounts.seam_far + mounts.ear_half_width + config.material.minimum_feature
    )
    # The real Seam's two ends in the *plate-local* frame (the keyboard model's
    # own centred frame, where +Y is the spacebar/front edge).
    assert mounts.seam_path.x_low_y == pytest.approx(_seam_x_at(model, -1000.0))
    assert mounts.seam_path.x_high_y == pytest.approx(_seam_x_at(model, 1000.0))
    assert mounts.seam_local_rear == pytest.approx(0.0, abs=1e-6)
    assert mounts.seam_local_front == pytest.approx(-50.584375, abs=1e-6)

    # Placed on the chassis, the keyboard's 180 deg turn swaps the two ends:
    # the spacebar row's jog (local front) is the *world front* lip's Seam end.
    assert mounts.seam_front == pytest.approx(50.584375, abs=1e-6)
    assert mounts.seam_rear == pytest.approx(0.0, abs=1e-6)

    # Each pair straddles its own end of the *world* Seam, one station per
    # Section. A station the chassis forces inboard (the front lip's band
    # column) is walked toward the Seam and says so; the rest keep the nominal
    # clearance.
    for station, seam_x in (
        ("front-seam", mounts.seam_front),
        ("rear-seam", mounts.seam_rear),
    ):
        pair = [
            mounts.mount(f"{station}-left"),
            mounts.mount(f"{station}-right"),
        ]
        assert min(m.x for m in pair) < seam_x < max(m.x for m in pair)
        assert {m.section for m in pair} == {"left", "right"}
    for name in (
        "front-seam-left",
        "front-seam-right",
        "rear-seam-left",
        "rear-seam-right",
    ):
        mount = mounts.mount(name)
        seam_x = mounts.seam_front if name.startswith("front") else mounts.seam_rear
        nominal = seam_x + (1.0 if mount.x > seam_x else -1.0) * mounts.seam_clearance
        # Either the nominal clearance from its end, or a reported walk toward it.
        assert abs(mount.x - nominal) < 1e-9 or mount.adjustments, name

    # Today: the spacebar-row jog is 50.584 mm off the centreline.
    assert mounts.mount("front-seam-left").x == pytest.approx(
        50.584375 + mounts.seam_clearance, abs=1e-6
    )
    assert mounts.mount("rear-seam-left").x == pytest.approx(
        mounts.seam_clearance, abs=1e-6
    )
    assert mounts.mount("rear-seam-right").x == pytest.approx(
        -mounts.seam_clearance, abs=1e-6
    )


def test_a_front_at_seam_station_is_walked_inboard_of_the_band_column(
    data, mounts, frame
):
    """The front lip's band column cannot share the Seam end with a boss.

    The spacebar-row Seam end lands 10.39 mm from the front wall's side band
    station, and the nominal 7.20 mm at-Seam station would put its M2 boss
    (and bore) inside that column. The station is therefore walked toward the
    Seam until the plate's ear clears the column by the shell clearance, and
    the walk is reported -- never silent. The two Deck bosses may fuse in
    print; their insert bores keep printable material between them.
    """
    config, _, budget, _ = data
    column = next(
        s
        for s in budget.chassis_joint.stations
        if s.kind == "side" and s.x > 0.0 and s.y < 0.0
    )
    walked = mounts.mount("front-seam-right")  # the world +x member, local right
    assert walked.x > mounts.seam_front - mounts.seam_clearance
    assert walked.adjustments, "the walk must be reported, not silent"
    assert any("Seam" in note for note in walked.adjustments)
    # The plate's ear (the part that must clear the *column*) sits exactly the
    # shell clearance off the column's boss.
    ear = frame.local_rect_to_world(walked.ear.rect)
    assert ear.x0 - (column.x + column.boss / 2.0) == pytest.approx(
        config.clearance.shell, abs=1e-6
    )
    # The well boss may merge with the band boss (both are Deck material); the
    # two heat-set bores keep at least the printable minimum of material.
    distance = math.hypot(walked.x - column.x, walked.y - column.y)
    assert distance - (
        mounts.insert_hole_diameter + budget.chassis_joint.insert_hole
    ) / 2.0 >= config.material.minimum_feature - 1e-9
    # And it is still the closest at-Seam station: it clamps the Seam's end.
    assert mounts.seam_front - walked.x == pytest.approx(3.54, abs=0.01)
    assert mounts.seam_front - walked.x < mounts.seam_clearance


def test_each_section_gets_four_stations_on_its_side_of_the_seam(data, mounts):
    """The Section count comes from the Seam, in the plate's own frame."""
    config, components, _, _ = data
    model = components["keyboard"].plate_model()
    minimum = config.material.minimum_feature
    counts = {"left": 0, "right": 0}
    for mount in mounts.mounts:
        local_x, local_y = mount.plate_xy
        seam_x = _seam_x_at(model, local_y)
        if mount.section == "left":
            assert local_x < seam_x, mount.name
            counts["left"] += 1
        else:
            assert local_x > seam_x, mount.name
            counts["right"] += 1
        # The plate's own geometry -- the ear and the clearance bore (the boss
        # is Deck material above the plate, so the split does not cut it) --
        # stays clear of the segment by the printable minimum.
        for rect in (mount.ear.rect, mount.local_bore_rect):
            gap = seam_x - rect.x1 if mount.section == "left" else rect.x0 - seam_x
            assert gap >= minimum - 1e-9, (mount.name, gap)
    assert counts == {"left": 4, "right": 4}
    assert mounts.section_counts == {"left": 4, "right": 4}
    assert mounts.ok, mounts.summary()


def test_the_real_plate_seam_crosses_no_station_ear(data, mounts):
    """No boss ear straddles the plate Seam the keyboard model derives (#15).

    The Seam jogs between key rows, so its X differs per band; an ear is only
    in trouble where the two overlap in Y.
    """
    config, components, _, _ = data
    model = components["keyboard"].plate_model()
    margin = config.material.minimum_feature
    bands = model.seam.segments(model.metadata.height)
    assert len(bands) > 1  # the row-jogging path, not a straight cut
    for mount in mounts.mounts:
        for rect in (mount.ear.rect, mount.local_bore_rect):
            for y0, y1, sx in bands:
                if rect.y1 <= y0 or rect.y0 >= y1:
                    continue
                assert rect.x1 <= sx - margin or rect.x0 >= sx + margin, (
                    f"{mount.name} reaches across the plate Seam at x={sx:.2f}"
                )


def test_stations_follow_a_moved_seam_jog(data, seam, frame):
    """The at-Seam stations are derived from the Seam, not pinned to numbers."""
    config, _, budget, _ = data
    moved = _jog_rear(seam, -70.0)
    result = well_mounts(config, budget, seam=moved, frame=frame)
    # The moved jog is the plate-local *front* (high-Y) end; placed, the
    # world's rear Seam end is 0 and the front end +70 (the 180 deg turn).
    assert result.seam_local_front == pytest.approx(-70.0)
    assert result.seam_front == pytest.approx(70.0)
    assert result.seam_rear == pytest.approx(0.0)
    # The rear pair straddles the (world) rear end at x = 0 ...
    assert result.mount("rear-seam-left").x == pytest.approx(
        result.seam_clearance
    )
    assert result.mount("rear-seam-right").x == pytest.approx(
        -result.seam_clearance
    )
    # ... and the front pair follows the moved Seam end at +70.
    assert result.mount("front-seam-left").x == pytest.approx(
        70.0 + result.seam_clearance
    )
    assert result.mount("front-seam-right").x == pytest.approx(
        70.0 - result.seam_clearance
    )
    assert result.ok, result.summary()
    assert result.section_counts == {"left": 4, "right": 4}


def test_a_seam_jog_that_swallows_an_outer_station_fails_loudly(data, seam, frame):
    """Never rebalance silently: a crossed station is a structured failure."""
    config, _, budget, _ = data
    result = well_mounts(config, budget, seam=_jog_rear(seam, -110.0), frame=frame)
    # Nothing is dropped or NX-shuffled: the eight stations are still reported.
    assert len(result.mounts) == 8
    assert result.section_counts != {"left": 4, "right": 4}
    assert not result.ok
    assert any("Section" in reason for reason in result.failures)
    # And the pair that ended up on one Section says so itself.
    crossed = [
        m for m in result.mounts if any("section" in r for r in m.reasons)
    ]
    assert crossed, "the crossed pair must say which station it is"


def test_seam_path_reads_the_ends_and_the_side_of_a_band(seam):
    path = SeamPath.from_seam(seam, 80.85)
    assert path.x_low_y == pytest.approx(0.0)
    assert path.x_high_y == pytest.approx(-50.584375)
    # Every band is addressed by plate-local Y ...
    for y0, y1, x in path.bands:
        assert path.x_at((y0 + y1) / 2.0) == pytest.approx(x)
    # ... and the ends are stretched to the plate's own front/back edges.
    assert path.bands[0][0] == pytest.approx(-80.85 / 2.0)
    assert path.bands[-1][1] == pytest.approx(80.85 / 2.0)
    # Section membership is the Seam's, not the centreplane's.
    assert path.section_at(-60.0, 30.0) == -1
    assert path.section_at(-40.0, 30.0) == 1
    assert path.section_at(-1.0, -30.0) == -1
    assert path.section_at(1.0, -30.0) == 1


def test_the_budget_carries_the_plate_seam(data, seam, frame):
    """The Deck's adapter calls well_mounts without the keyboard model.

    ``compute_slide_budget`` puts the plate's Seam on the Well, so the Deck's
    insert bosses and the plate's ears are one pattern from one source. The
    plate's *frame* (the placement's 180 deg turn) is the other half of that
    source: without it the pattern would be point-reflected in the chassis.
    """
    config, _, budget, _ = data
    assert budget.well.seam == seam
    implicit = well_mounts(config, budget, frame=frame)
    explicit = well_mounts(config, budget, seam=seam, frame=frame)
    assert implicit.ok, implicit.summary()
    assert [(m.name, m.world_xy) for m in implicit.mounts] == [
        (m.name, m.world_xy) for m in explicit.mounts
    ]
    # The Well can hand out the same frame and world Seam from the placement.
    assert budget.well.seam_in(frame).bands == implicit.seam_world.bands


def test_a_missing_frame_is_an_error_not_a_zero_rotation(data, seam):
    """The 180 deg placement is never assumed away: the frame is required."""
    config, _, budget, _ = data
    with pytest.raises(ValueError, match="plate frame"):
        well_mounts(config, budget, seam=seam)


def test_a_missing_seam_is_an_error_not_a_centreline_guess(data, frame):
    """Never fall back to the straight x = 0 cut the real Seam replaced."""
    config, _, budget, _ = data
    bare = dataclasses.replace(
        budget, well=dataclasses.replace(budget.well, seam=None)
    )
    with pytest.raises(ValueError, match="plate's Seam"):
        well_mounts(config, bare, frame=frame)


def test_seam_path_accepts_bare_bands_and_rejects_broken_ones():
    plain = SeamPath.from_seam(((-10.0, 0.0, 2.0), (0.0, 10.0, -3.0)), 40.0)
    assert plain.bands[0][0] == pytest.approx(-20.0)  # stretched to the edge
    assert plain.bands[-1][1] == pytest.approx(20.0)
    assert plain.x_low_y == pytest.approx(2.0)
    assert plain.x_high_y == pytest.approx(-3.0)
    with pytest.raises(ValueError):
        SeamPath.from_seam((), 40.0)
    with pytest.raises(ValueError):
        SeamPath.from_seam(((0.0, 5.0),), 40.0)  # not a (y0, y1, x) band
    with pytest.raises(ValueError):
        SeamPath.from_seam(((0.0, 5.0, 0.0), (10.0, 9.0, 0.0)), 40.0)  # inside out
    with pytest.raises(ValueError):
        SeamPath.from_seam(((0.0, 5.0, 0.0), (6.0, 9.0, 0.0)), 40.0)  # a gap



# -- the existing chassis features ---------------------------------------


def test_stations_clear_the_band_stations_and_the_seats(data, mounts):
    """No plate material meets a chassis feature; Deck bosses may merge.

    The plate (its ear, at the plate's Z) must clear every band boss by the
    shell clearance. The *well boss* is Deck material above the plate, so it
    may fuse with a band boss -- what must stay printable is the material
    between the two heat-set bores (issue #19's walked station).
    """
    config, _, budget, _ = data
    clearance = config.clearance.shell
    minimum = config.material.minimum_feature
    seats = bearing_seat_obstacles(config, budget)
    assert len(seats) == 2
    for mount in mounts.mounts:
        ear = mounts.frame.local_rect_to_world(mount.ear.rect)
        for station in budget.chassis_joint.stations:
            reach = station.boss / 2.0
            dx = max(ear.x0 - station.x, 0.0, station.x - ear.x1)
            dy = max(ear.y0 - station.y, 0.0, station.y - ear.y1)
            assert math.hypot(dx, dy) >= reach + clearance - 1e-9, (
                mount.name,
                station,
            )
            # Two Deck insert bosses may fuse; their bores keep the minimum.
            bore_distance = math.hypot(mount.x - station.x, mount.y - station.y)
            assert bore_distance - (
                mounts.insert_hole_diameter + budget.chassis_joint.insert_hole
            ) / 2.0 >= minimum - 1e-9, (mount.name, station)
        for seat in seats:
            assert not mount.plan_rect.overlaps(seat.rect, clearance), (mount.name, seat)
    assert mounts.ok, mounts.summary()
    assert mounts.failures == ()


def test_plate_notches_are_cut_where_the_band_bosses_reach_the_border(data, mounts):
    config, _, budget, _ = data
    plate = _plate_rect(budget)
    front_stations = [s for s in budget.chassis_joint.stations if s.y < 0.0]
    assert len(front_stations) == 5  # two corners, two sides, one centreline
    assert len(mounts.notches) == len(front_stations)
    assert len({n.source for n in mounts.notches}) == len(front_stations)
    for notch in mounts.notches:
        assert isinstance(notch, PlateNotch)
        # The notch is a plate-local rectangle the plate builder can cut.
        assert notch.rect.overlaps(mounts.frame.local_rect)
        assert notch.rect.x0 < notch.rect.x1
        assert notch.rect.x0 >= mounts.frame.local_rect.x0 - config.clearance.shell - 1e-9
        assert notch.rect.x1 <= mounts.frame.local_rect.x1 + config.clearance.shell + 1e-9
        # It cuts the front border only: the sheet survives across it.
        assert notch.depth < (plate.y1 - plate.y0) / 2.0
        # It really is driven by a band station.
        assert notch.source.startswith("chassis-joint:")
        # The boss may poke into the ring's plan, but never through it.
        assert budget.well.ring - notch.intrusion >= (
            config.material.minimum_feature - 1e-9
        )
        # The same rectangle in the chassis plan: the world frame the Deck's
        # band bosses live in (issue #19 -- the notches were on the wrong lip).
        world = mounts.frame.local_rect_to_world(notch.rect)
        assert (world.x0, world.y0, world.x1, world.y1) == pytest.approx(
            (
                notch.world_rect.x0,
                notch.world_rect.y0,
                notch.world_rect.x1,
                notch.world_rect.y1,
            )
        )
    # Today: each band boss bites 0.75 mm into the 2.00 mm border; with the
    # shell air gap around it the notch is ~5.3 x 1.1 mm.
    for notch in mounts.notches:
        assert notch.depth == pytest.approx(1.1, abs=0.02)
        assert notch.rect.width == pytest.approx(5.3, abs=0.03)


def test_the_notches_land_on_the_world_front_lip(mounts):
    """The chassis' band columns are in the world front wall (-Y).

    The keyboard is placed rotated 180 deg, so the plate-local frame's **+Y**
    edge is the world's front lip. A notch emitted in the unrotated frame would
    sit on the world rear lip and clear nothing.
    """
    plate = mounts.frame.rect
    local = mounts.frame.local_rect
    for notch in mounts.notches:
        # World: the notch crosses the plate's front (-Y) edge.
        assert notch.world_rect.y0 < plate.y0 < notch.world_rect.y1
        assert notch.world_rect.y1 < plate.y1
        # Plate-local: the same notch crosses the **+Y** edge.
        assert notch.rect.y0 < local.y1 < notch.rect.y1
        assert notch.rect.y0 > local.y0
        # The band station that drives it is a front-wall one.
        source_x, source_y = notch.source.rsplit("@", 1)[1].split(",")
        assert float(source_y) < 0.0
        assert float(source_x) == pytest.approx(
            mounts.frame.local_rect_to_world(notch.rect).cx, abs=0.01
        )


def test_seats_clear_the_plate_in_z(data, mounts):
    """The bearing-clamp seats sit above the plate: no notch, a stated gap."""
    config, _, budget, _ = data
    for seat in bearing_seat_obstacles(config, budget):
        assert seat.z0 >= mounts.plate_top - 1e-9
        assert seat.z0 - mounts.plate_top >= config.slide.component_gap - 1e-9


def test_notches_keep_the_plate_one_connected_sheet(mounts):
    assert mounts.sheet_connected
    assert mounts.ok


def test_the_notches_come_from_the_band_joint_not_a_list(data, mounts, seam, frame):
    config, _, budget, _ = data
    bare = dataclasses.replace(
        budget,
        chassis_joint=dataclasses.replace(budget.chassis_joint, stations=()),
    )
    result = well_mounts(config, bare, seam=seam, frame=frame)
    assert result.notches == ()
    # Without the corner column the outer stations can sit at the plate's edge.
    for name in ("front-outer-left", "rear-outer-right"):
        assert abs(result.mount(name).x) > abs(mounts.mount(name).x)


def test_a_feature_that_breaches_the_ring_fails(data, mounts, seam, frame):
    config, _, budget, _ = data
    plate = _plate_rect(budget)
    reach = budget.well.ring - config.material.minimum_feature / 2.0
    blocker = Obstacle(
        name="test-ring-breach",
        rect=PlanRect(-20.0, plate.y0 - 5.0, -19.0, plate.y0 + reach),
        z0=mounts.plate_bottom,
        z1=mounts.plate_top,
    )
    result = well_mounts(config, budget, seam=seam, frame=frame, obstacles=(blocker,))
    assert not result.ok
    assert any("Well ring" in reason for reason in result.failures)
    # The mount pattern is still complete.
    assert len(result.mounts) == 8


def test_a_severing_notch_is_a_structural_failure(data, mounts, seam, frame):
    """A notch that cuts the sheet in two must fail, never silently vanish."""
    config, _, budget, _ = data
    x = 50.0
    cut = Obstacle(
        name="test-through-cut",
        rect=PlanRect(x - 1.0, -1000.0, x + 1.0, 1000.0),
        z0=mounts.plate_bottom,
        z1=mounts.plate_top,
    )
    result = well_mounts(config, budget, seam=seam, frame=frame, obstacles=(cut,))
    assert not result.sheet_connected
    assert not result.ok
    assert any("sever" in reason for reason in result.failures)
    # No station was dropped: the pattern is still eight.
    assert len(result.mounts) == 8


# -- switches ------------------------------------------------------------


def test_ears_and_bosses_clear_the_real_switch_cutouts(data, mounts, seam, frame):
    config, components, budget, _ = data
    cutouts = _switch_cutouts(components)
    assert len(cutouts) > 30  # the real 40% keyboard
    result = well_mounts(config, budget, seam=seam, frame=frame, cutouts=cutouts)
    assert result.ok, result.summary()
    for mount in result.mounts:
        for cut in cutouts:
            assert not mount.ear.rect.overlaps(cut), mount.name


def test_a_cutout_under_an_ear_is_reported(data, mounts, seam, frame):
    config, _, budget, _ = data
    mount = mounts.mounts[0]
    x, y = mount.plate_xy
    cut = PlanRect(x - 8.0, y - 8.0, x + 8.0, y + 8.0)
    result = well_mounts(config, budget, seam=seam, frame=frame, cutouts=(cut,))
    assert not result.ok
    assert len(result.mounts) == 8
    assert any("cutout" in reason for reason in result.failures)


# -- parameterisation ----------------------------------------------------


def _frame_of(budget, placement=None, rotation=None) -> PlateFrame:
    """A plate frame on ``budget``'s Well, at the layout's keyboard position.

    The layout places the keyboard's plate centre at
    ``-chassis_height/2 + well_front_margin + plate_depth/2`` (the Well's own
    centre), turned so the spacebar faces the user.
    """
    cy = -budget.chassis_height / 2.0 + budget.well_front_margin + (
        budget.well.plate_depth / 2.0
    )
    return PlateFrame(
        cx=0.0,
        cy=cy,
        width=budget.well.plate_width,
        depth=budget.well.plate_depth,
        rotation=placement.rotation if rotation is None else rotation,
    )


def test_stations_follow_the_well_sizing_chain(data, mounts, seam, keyboard_placement):
    """The stations are derived, not pinned: a different plate moves them."""
    config, components, _, _ = data
    wobblier = dataclasses.replace(
        config, keyboard=dataclasses.replace(config.keyboard, plate_wobble=1.2)
    )
    other_budget = compute_slide_budget(wobblier, components)
    other = well_mounts(
        wobblier,
        other_budget,
        seam=seam,
        frame=_frame_of(other_budget, keyboard_placement),
    )
    assert other.frame.depth > mounts.frame.depth
    assert other.mounts[0].y != pytest.approx(mounts.mounts[0].y)
    assert other.boss_diameter == pytest.approx(mounts.boss_diameter)

    thinner = dataclasses.replace(
        config, wall=Wall(thickness=config.wall.thickness - 0.2)
    )
    thin_budget = compute_slide_budget(thinner, components)
    thin = well_mounts(
        thinner,
        thin_budget,
        seam=seam,
        frame=_frame_of(thin_budget, keyboard_placement),
    )
    # The plate is Cutout + one wall per side, so a thinner ring makes it
    # shallower -- and moves every station with it.
    assert thin.frame.depth < mounts.frame.depth
    assert thin.mounts[0].y != pytest.approx(mounts.mounts[0].y)


def test_an_obstacle_over_a_boss_invalidates_that_station_only(data, mounts, seam, frame):
    config, _, budget, _ = data
    target = next(m for m in mounts.mounts if m.station == "front-outer")
    blocker = Obstacle(
        name="test-blocker",
        rect=PlanRect.from_centre(target.x, target.y, 8.0, 8.0),
        z0=mounts.plate_top,
        z1=mounts.plate_top + mounts.boss_height,
    )
    result = well_mounts(config, budget, seam=seam, frame=frame, obstacles=(blocker,))
    assert len(result.mounts) == 8
    hit = next(m for m in result.mounts if m.name == target.name)
    assert not hit.valid
    assert any("test-blocker" in reason for reason in hit.reasons)
    assert hit in result.invalid
    assert not result.ok
    # Every other station is untouched.
    assert all(m.valid for m in result.mounts if m.name != target.name)


# -- the frame and the report -------------------------------------------


def test_the_frame_is_the_placed_plate_in_the_chassis(
    data, mounts, keyboard_placement, frame
):
    """One frame, derived from the keyboard's placement (issue #19)."""
    _, components, budget, _ = data
    assert mounts.frame is frame or mounts.frame == frame
    assert frame.rotation == pytest.approx(180.0)
    assert frame.width == pytest.approx(mounts.plate_width)
    assert frame.depth == pytest.approx(mounts.plate_depth)
    assert (frame.cx, frame.cy) == pytest.approx(
        (keyboard_placement.x, keyboard_placement.y)
    )

    # World <-> local round-trips, and the frame is the placement's transform.
    for x, y in ((0.0, 0.0), (10.0, -5.0), (-116.625, 40.425), (37.5, 12.25)):
        wx, wy = frame.local_to_world(x, y)
        assert frame.world_to_local(wx, wy) == pytest.approx((x, y))
        assert keyboard_placement.world_offset(x, y, 0.0)[:2] == pytest.approx(
            (wx, wy)
        )
        rect = PlanRect.from_centre(x, y, 4.0, 2.0)
        world_rect = frame.local_rect_to_world(rect)
        assert frame.world_rect_to_local(world_rect) == PlanRect(
            rect.x0, rect.y0, rect.x1, rect.y1
        )
        # The aliases the rest of the code reads are the same two maps.
        assert frame.to_plan(x, y) == pytest.approx((wx, wy))
        assert frame.to_local(wx, wy) == pytest.approx((x, y))

    # Plate-local rectangles are centred on the plate, like the keyboard's own
    # geometry model, so the plate builder can use them directly.
    assert frame.local_rect.x0 == pytest.approx(-mounts.plate_width / 2.0)
    # Today: the plate spans x +/-116.625 and y -62.35..18.50 in the plan.
    assert frame.local_rect.x1 == pytest.approx(116.625)
    assert frame.rect.y0 == pytest.approx(-62.35)
    assert frame.rect.y1 == pytest.approx(18.5)
    # The 180 deg turn: the plate's local +Y edge is the world's front lip.
    assert frame.local_to_world(0.0, mounts.plate_depth / 2.0)[1] == pytest.approx(
        frame.y0
    )
    # The Well Cutout is the plate inset by the ring, matching the budget.
    assert mounts.cutout_rect.width == pytest.approx(budget.well.cutout_width)
    assert mounts.cutout_rect.depth == pytest.approx(budget.well.cutout_depth)


def test_a_frame_off_the_well_is_an_error(data, keyboard_placement, frame):
    """The keyboard's placement and the Well must agree, or nothing does."""
    config, _, budget, _ = data
    shifted = dataclasses.replace(
        frame, cy=frame.cy + 1.0, cx=frame.cx
    )
    with pytest.raises(ValueError, match="Well"):
        well_mounts(config, budget, seam=budget.well.seam, frame=shifted)


def test_the_frame_needs_an_axis_aligned_rotation(mounts):
    """The plate's outline/ears/notches are axis-aligned rectangles."""
    with pytest.raises(ValueError, match="multiple of 90"):
        PlateFrame(
            cx=0.0,
            cy=0.0,
            width=mounts.plate_width,
            depth=mounts.plate_depth,
            rotation=37.0,
        )


def test_a_different_placement_offset_moves_the_whole_pattern(data, frame, seam):
    """Offset the keyboard (and its Well) and the pattern follows rigidly.

    A placement offset is a translation of the plate in the chassis: the Well
    is re-derived for it (its lips follow), and every station moves with the
    plate in the plan while keeping its place in the plate's own frame. With no
    chassis features to dodge, nothing walks.
    """
    config, _, budget, _ = data
    bare = dataclasses.replace(
        budget,
        chassis_joint=dataclasses.replace(budget.chassis_joint, stations=()),
    )
    base = well_mounts(config, bare, seam=seam, frame=frame)
    dy = 3.0  # rearward: the front lip grows, the plate keeps clear of the wall
    shifted_well = dataclasses.replace(
        budget.well,
        front_lip=budget.well.front_lip + dy,
        rear_lip=budget.well.rear_lip - dy,
    )
    shifted = dataclasses.replace(bare, well=shifted_well)
    moved = well_mounts(
        config,
        shifted,
        seam=seam,
        frame=dataclasses.replace(frame, cy=frame.cy + dy),
    )
    assert moved.ok, moved.summary()
    for old, new in zip(base.mounts, moved.mounts):
        assert new.name == old.name
        assert new.plate_xy == pytest.approx(old.plate_xy)
        assert new.world_xy == pytest.approx(
            (old.world_xy[0], old.world_xy[1] + dy)
        )
    for old, new in zip(base.notches, moved.notches):
        assert new.rect == old.rect
        assert new.world_rect.y0 == pytest.approx(old.world_rect.y0 + dy)


def test_summary_reports_stations_bosses_ears_and_notches(mounts):
    text = mounts.summary()
    assert "6.00" in text  # the boss diameter
    assert "front-outer" in text
    assert "notch" in text
    # The report names the Seam's two ends and the per-Section counts, so a
    # reader can see the four-per-Section pattern without re-deriving it.
    assert "front x=" in text and "rear x=" in text
    assert "sections: left 4, right 4" in text
    assert mounts.section_counts == {"left": 4, "right": 4}


def test_module_is_pure_data():
    import geometry.well_mounts as module

    with open(module.__file__, "r", encoding="utf-8") as handle:
        source = handle.read()
    assert "build123d" not in source
    for package in ("case", "components"):
        assert f"from {package}" not in source
        assert f"import {package}" not in source
