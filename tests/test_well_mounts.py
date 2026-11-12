"""Plate boss stations and ear outlines (ADR-0014, issue #11).

Pure-data tests: the eight M2 insert bosses under the Deck's Well, the ears the
plate grows to reach them, and the notches the existing chassis band joint
forces into the plate border. The Deck (T3) cuts the bosses onto the Well
ring's outer face; the plate (T4) cuts the clearance holes, the ears and the
notches. Nothing here needs a CAD library.

Every expected value is derived from the configuration, the fastener library
and the slide budget. The few literal numbers stated (Ø6.0 boss, Ø3.0 bore,
4.6 mm ear) are the arithmetic on those sources spelled out, so a parameter
change moves the model and the test together.
"""

import dataclasses

import pytest

from components.slide import compute_slide_budget
from geometry.well_mounts import (
    Ear,
    Obstacle,
    PlanRect,
    PlateNotch,
    bearing_seat_obstacles,
    well_mounts,
)
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
def mounts(data):
    config, _, budget, _ = data
    return well_mounts(config, budget)


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

    The keyboard geometry model is pure data (no CAD), so the clash check runs
    against the actual switches rather than a placeholder.
    """
    model = components["keyboard"].plate_model()
    rects = []
    for cut in model.switch_cutouts:
        xs = [v[0] for v in cut.vertices]
        ys = [v[1] for v in cut.vertices]
        rects.append(
            PlanRect(
                cut.x + min(xs),
                cut.y + min(ys),
                cut.x + max(xs),
                cut.y + max(ys),
            )
        )
    return tuple(rects)


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


def test_stations_mirror_about_the_centreplane(mounts):
    for mount in mounts.mounts:
        (mirror,) = [
            m for m in mounts.mounts
            if m.station == mount.station and m.side == -mount.side
        ]
        assert mirror.y == pytest.approx(mount.y)
        assert mirror.x == pytest.approx(-mount.x)
        assert mirror.ear is not None and mount.ear is not None
        assert mirror.ear.rect.x0 == pytest.approx(-mount.ear.rect.x1)
        assert mirror.ear.rect.x1 == pytest.approx(-mount.ear.rect.x0)


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


def test_boss_stands_on_the_plate_top_and_holds_the_insert(mounts):
    for mount in mounts.mounts:
        assert mount.boss_z0 == pytest.approx(mounts.plate_top)
        assert mount.boss_z1 - mount.boss_z0 == pytest.approx(mounts.boss_height)
        # The insert bottomed in the boss still has printable material above it.
        assert mount.boss_z1 - mount.boss_z0 >= mounts.insert_depth


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
        assert ear.protrusion == pytest.approx(
            (mounts.insert_hole_diameter / 2.0 + mounts.bore_margin)
            + (screw.clearance / 2.0 + edge)
        )
        assert ear.fillet is not None and ear.fillet > 0.0
        assert ear.overlap >= config.material.minimum_feature
        # Today: a 4.6 mm ear around the Ø2.2 hole, r2.0 ends.
        assert ear.protrusion == pytest.approx(4.6)
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
        # The plain plate border under the ring, at this station's X.
        if front:
            border = PlanRect(
                mount.ear.rect.x0, -frame.depth / 2.0,
                mount.ear.rect.x1, -frame.depth / 2.0 + budget.well.ring,
            )
        else:
            border = PlanRect(
                mount.ear.rect.x0, frame.depth / 2.0 - budget.well.ring,
                mount.ear.rect.x1, frame.depth / 2.0,
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


def test_stations_and_ears_clear_the_stepped_seam(data, mounts):
    config, _, _, _ = data
    split = config.slide.split
    # The plate has no config Split any more: it splits between keys along its
    # own derived Seam (#15), so the stiffest *configured* step is the chassis's.
    far = max(abs(v) for v in split["chassis"].seams()[0].x_range)
    assert mounts.seam_far == pytest.approx(far)
    assert mounts.seam_clearance == pytest.approx(
        far + mounts.ear_half_width + config.material.minimum_feature
    )
    for mount in mounts.mounts:
        assert abs(mount.x) - mount.ear_half_width >= (
            far + config.material.minimum_feature - 1e-9
        )
    # The Seam stations are the tightest pair, one per Section.
    seam = [abs(m.x) for m in mounts.mounts if m.station.endswith("seam")]
    assert max(seam) == pytest.approx(mounts.seam_clearance)


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
        ear = mount.ear.rect
        for y0, y1, sx in bands:
            if ear.y1 <= y0 or ear.y0 >= y1:
                continue
            assert ear.x1 <= sx - margin or ear.x0 >= sx + margin, (
                f"{mount.station} ear {ear} straddles the plate Seam at x={sx:.2f}"
            )



# -- the existing chassis features ---------------------------------------


def test_stations_clear_the_band_stations_and_the_seats(data, mounts):
    config, _, budget, _ = data
    clearance = config.clearance.shell
    seats = bearing_seat_obstacles(config, budget)
    assert len(seats) == 2
    for mount in mounts.mounts:
        for station in budget.chassis_joint.stations:
            disc = PlanRect.from_centre(station.x, station.y, station.boss, station.boss)
            assert not mount.plan_rect.overlaps(disc, clearance), (mount.name, station)
        for seat in seats:
            assert not mount.plan_rect.overlaps(seat.rect, clearance), (mount.name, seat)
    assert mounts.ok, mounts.summary()
    assert mounts.failures == ()


def test_plate_notches_are_cut_where_the_band_bosses_reach_the_border(data, mounts):
    config, _, budget, _ = data
    plate = _plate_rect(budget)
    front_stations = [s for s in budget.chassis_joint.stations if s.y < 0.0]
    assert len(front_stations) == 4  # long-wall corners + long-wall stations
    assert len(mounts.notches) == len(front_stations)
    assert len({n.source for n in mounts.notches}) == len(front_stations)
    for notch in mounts.notches:
        assert isinstance(notch, PlateNotch)
        # The notch is a plate-local rectangle the plate builder can cut.
        assert notch.rect.overlaps(mounts.frame.local_rect)
        assert notch.rect.x0 < notch.rect.x1
        assert notch.rect.x0 >= mounts.frame.local_rect.x0 - notch.clearance - 1e-9
        assert notch.rect.x1 <= mounts.frame.local_rect.x1 + notch.clearance + 1e-9
        # It cuts the front border only: the sheet survives across it.
        assert notch.depth < (plate.y1 - plate.y0) / 2.0
        assert notch.clearance == pytest.approx(config.clearance.shell)
        # It really is driven by a band station.
        assert notch.source.startswith("chassis-joint:")
        # The boss may poke into the ring's plan, but never through it.
        assert budget.well.ring - notch.intrusion >= (
            config.material.minimum_feature - 1e-9
        )
    # Today: each band boss bites 0.75 mm into the 2.00 mm border; with the
    # shell air gap around it the notch is ~5.3 x 1.1 mm.
    for notch in mounts.notches:
        assert notch.depth == pytest.approx(1.1, abs=0.02)
        assert notch.rect.width == pytest.approx(5.3, abs=0.03)


def test_seats_clear_the_plate_in_z(data, mounts):
    """The bearing-clamp seats sit above the plate: no notch, a stated gap."""
    config, _, budget, _ = data
    for seat in bearing_seat_obstacles(config, budget):
        assert seat.z0 >= mounts.plate_top - 1e-9
        assert seat.z0 - mounts.plate_top >= config.slide.component_gap - 1e-9


def test_notches_keep_the_plate_one_connected_sheet(mounts):
    assert mounts.sheet_connected
    assert mounts.ok


def test_the_notches_come_from_the_band_joint_not_a_list(data, mounts):
    config, _, budget, _ = data
    bare = dataclasses.replace(
        budget,
        chassis_joint=dataclasses.replace(budget.chassis_joint, stations=()),
    )
    result = well_mounts(config, bare)
    assert result.notches == ()
    # Without the corner column the outer stations can sit at the plate's edge.
    for name in ("front-outer-left", "rear-outer-right"):
        assert abs(result.mount(name).x) > abs(mounts.mount(name).x)


def test_a_feature_that_breaches_the_ring_fails(data, mounts):
    config, _, budget, _ = data
    plate = _plate_rect(budget)
    reach = budget.well.ring - config.material.minimum_feature / 2.0
    blocker = Obstacle(
        name="test-ring-breach",
        rect=PlanRect(-20.0, plate.y0 - 5.0, -19.0, plate.y0 + reach),
        z0=mounts.plate_bottom,
        z1=mounts.plate_top,
    )
    result = well_mounts(config, budget, obstacles=(blocker,))
    assert not result.ok
    assert any("Well ring" in reason for reason in result.failures)
    # The mount pattern is still complete.
    assert len(result.mounts) == 8


def test_a_severing_notch_is_a_structural_failure(data, mounts):
    """A notch that cuts the sheet in two must fail, never silently vanish."""
    config, _, budget, _ = data
    x = 50.0
    cut = Obstacle(
        name="test-through-cut",
        rect=PlanRect(x - 1.0, -1000.0, x + 1.0, 1000.0),
        z0=mounts.plate_bottom,
        z1=mounts.plate_top,
    )
    result = well_mounts(config, budget, obstacles=(cut,))
    assert not result.sheet_connected
    assert not result.ok
    assert any("sever" in reason for reason in result.failures)
    # No station was dropped: the pattern is still eight.
    assert len(result.mounts) == 8


# -- switches ------------------------------------------------------------


def test_ears_and_bosses_clear_the_real_switch_cutouts(data, mounts):
    config, components, budget, _ = data
    cutouts = _switch_cutouts(components)
    assert len(cutouts) > 30  # the real 40% keyboard
    result = well_mounts(config, budget, cutouts=cutouts)
    assert result.ok, result.summary()
    for mount in result.mounts:
        for cut in cutouts:
            assert not mount.ear.rect.overlaps(cut), mount.name


def test_a_cutout_under_an_ear_is_reported(data, mounts):
    config, _, budget, _ = data
    mount = mounts.mounts[0]
    x, y = mount.plate_xy
    cut = PlanRect(x - 8.0, y - 8.0, x + 8.0, y + 8.0)
    result = well_mounts(config, budget, cutouts=(cut,))
    assert not result.ok
    assert len(result.mounts) == 8
    assert any("cutout" in reason for reason in result.failures)


# -- parameterisation ----------------------------------------------------


def test_stations_follow_the_well_sizing_chain(data, mounts):
    """The stations are derived, not pinned: a different plate moves them."""
    config, components, _, _ = data
    wobblier = dataclasses.replace(
        config, keyboard=dataclasses.replace(config.keyboard, plate_wobble=1.2)
    )
    other = well_mounts(wobblier, compute_slide_budget(wobblier, components))
    assert other.frame.depth > mounts.frame.depth
    assert other.mounts[0].y != pytest.approx(mounts.mounts[0].y)
    assert other.boss_diameter == pytest.approx(mounts.boss_diameter)

    thinner = dataclasses.replace(
        config, wall=Wall(thickness=config.wall.thickness - 0.2)
    )
    thin = well_mounts(thinner, compute_slide_budget(thinner, components))
    # The plate is Cutout + one wall per side, so a thinner ring makes it
    # shallower -- and moves every station with it.
    assert thin.frame.depth < mounts.frame.depth
    assert thin.mounts[0].y != pytest.approx(mounts.mounts[0].y)


def test_an_obstacle_over_a_boss_invalidates_that_station_only(data, mounts):
    config, _, budget, _ = data
    target = next(m for m in mounts.mounts if m.station == "front-outer")
    blocker = Obstacle(
        name="test-blocker",
        rect=PlanRect.from_centre(target.x, target.y, 8.0, 8.0),
        z0=mounts.plate_top,
        z1=mounts.plate_top + mounts.boss_height,
    )
    result = well_mounts(config, budget, obstacles=(blocker,))
    assert len(result.mounts) == 8
    hit = next(m for m in result.mounts if m.name == target.name)
    assert not hit.valid
    assert any("test-blocker" in reason for reason in hit.reasons)
    assert hit in result.invalid
    assert not result.ok
    # Every other station is untouched.
    assert all(m.valid for m in result.mounts if m.name != target.name)


# -- the frame and the report -------------------------------------------


def test_the_frame_is_the_plate_in_the_chassis(data, mounts):
    _, components, budget, _ = data
    frame = mounts.frame
    assert frame.width == pytest.approx(mounts.plate_width)
    assert frame.depth == pytest.approx(mounts.plate_depth)
    assert frame.to_local(frame.cx, frame.cy) == pytest.approx((0.0, 0.0))
    assert frame.to_plan(0.0, 0.0) == pytest.approx((frame.cx, frame.cy))
    for mount in mounts.mounts:
        assert frame.to_plan(*mount.plate_xy) == pytest.approx((mount.x, mount.y))
    # Plate-local rectangles are centred on the plate, like the keyboard's own
    # geometry model, so the plate builder can use them directly.
    assert frame.local_rect.x0 == pytest.approx(-mounts.plate_width / 2.0)
    # Today: the plate spans x +/-116.625, y -62.35..18.50.
    assert frame.local_rect.x1 == pytest.approx(116.625)
    assert frame.to_plan(0.0, 0.0) == pytest.approx((0.0, -21.925))
    # The Well Cutout is the plate inset by the ring, matching the budget.
    assert mounts.cutout_rect.width == pytest.approx(budget.well.cutout_width)
    assert mounts.cutout_rect.depth == pytest.approx(budget.well.cutout_depth)


def test_summary_reports_stations_bosses_ears_and_notches(mounts):
    text = mounts.summary()
    assert "6.00" in text  # the boss diameter
    assert "front-outer" in text
    assert "notch" in text


def test_module_is_pure_data():
    import geometry.well_mounts as module

    with open(module.__file__, "r", encoding="utf-8") as handle:
        source = handle.read()
    assert "build123d" not in source
    for package in ("case", "components"):
        assert f"from {package}" not in source
        assert f"import {package}" not in source
