"""Tests for component config plumbing."""

import pytest

from components.display_88 import Display88
from components.hdmi_driver import HdmiDriver
from components.battery import Battery


def test_display_flex_config():
    d = Display88({
        "width": 231.0,
        "height": 64.5,
        "thickness": 6.5,
        "flex": {"width": 38.5, "thickness": 1.0, "stack": 0.6, "edge_protrusion": 1.0},
    })
    assert d._flex_width == 38.5
    assert d._flex_thickness == 1.0
    assert d._flex_stack == 0.6
    assert d._flex_edge_protrusion == 1.0


def test_display_flex_defaults():
    d = Display88({"width": 231.0, "height": 64.5, "thickness": 6.5})
    assert d._flex_width == 38.5
    assert d._flex_thickness == 1.0
    assert d._flex_stack == 0.6
    assert d._flex_edge_protrusion == 0.75


def test_hdmi_driver_fpc_slot():
    h = HdmiDriver({"driver_board": {"fpc_slot_height": 1.5}})
    assert h._fpc_slot_height == 1.5


def test_hdmi_driver_fpc_slot_default():
    h = HdmiDriver({"driver_board": {}})
    assert h._fpc_slot_height == 1.0


def test_battery_side_by_side():
    """Two cells barrel-to-barrel: 2 diameters wide, one length deep."""
    b = Battery({"battery": {
        "cell_diameter": 18.6, "cell_length": 65.2,
        "count": 2, "arrangement": "side_by_side", "clearance": 2.0,
    }})
    assert b.size().width == pytest.approx(37.2)
    assert b.size().depth == pytest.approx(65.2)
    assert b.size().height == pytest.approx(18.6)
    assert b.clearance == 2.0


def test_battery_end_to_end():
    """Two cells cap-to-cap: one diameter wide, 2 lengths deep."""
    b = Battery({"battery": {
        "cell_diameter": 18.6, "cell_length": 65.2,
        "count": 2, "arrangement": "end_to_end",
    }})
    assert b.size().width == pytest.approx(18.6)
    assert b.size().depth == pytest.approx(130.4)
    assert b.size().height == pytest.approx(18.6)


def test_battery_defaults_to_two_18650_side_by_side():
    b = Battery({})
    assert b.count == 2
    assert b.size().width == pytest.approx(37.2)
    assert b.size().depth == pytest.approx(65.2)
    assert b.size().height == pytest.approx(18.6)


def test_battery_cell_centers_are_spaced_by_geometry():
    """Cell centers come from diameter/length, not hardcoded offsets."""
    b = Battery({"battery": {"count": 3, "arrangement": "side_by_side"}})
    xs = sorted(x for x, _ in b._cell_centers())
    assert xs == pytest.approx([-18.6, 0.0, 18.6])
    assert b.size().width == pytest.approx(3 * 18.6)


def test_battery_rejects_unknown_arrangement():
    with pytest.raises(ValueError, match="arrangement"):
        Battery({"battery": {"arrangement": "stacked"}})


def test_battery_rejects_zero_count():
    with pytest.raises(ValueError, match="count"):
        Battery({"battery": {"count": 0}})


# -- keyboard plate on the Well (ADR-0014) --------------------------------


def _slider_data():
    from components.slide import compute_slide_budget
    from main import BuildPipeline

    pipeline = BuildPipeline()
    config = pipeline.load_config()
    components = pipeline.load_components()
    budget = compute_slide_budget(config, components)
    return config, components, budget


def test_keyboard_plate_matches_the_well_budget():
    """One sizing chain: the plate the component builds equals the budget's."""
    _, components, budget = _slider_data()
    plate = components["keyboard"]._plate.size()
    assert plate.width == pytest.approx(budget.well.plate_width)
    assert plate.depth == pytest.approx(budget.well.plate_depth)
    assert plate.height == pytest.approx(budget.well.plate_thickness)


def test_keyboard_cutout_matches_the_well_cutout():
    _, components, budget = _slider_data()
    cutout = components["keyboard"]._plate.cutout
    assert cutout[2] - cutout[0] == pytest.approx(budget.well.cutout_width)
    assert cutout[3] - cutout[1] == pytest.approx(budget.well.cutout_depth)


def test_keyboard_plate_sits_on_the_well():
    """The keyboard's local plate raise is the Well's plate bottom (mm)."""
    _, components, budget = _slider_data()
    assert components["keyboard"]._plate_raise == pytest.approx(budget.well.plate_bottom)


def test_keyboard_reports_no_floor_standoffs():
    """ADR-0014 retires the Tray-floor standoffs: the Deck bears the plate."""
    _, components, _ = _slider_data()
    keyboard = components["keyboard"]
    assert keyboard.mounting_holes() == []
    assert keyboard._plate.mounting_holes() == []


def test_keyboard_plate_takes_injected_mounting_holes():
    _, components, _ = _slider_data()
    keyboard = components["keyboard"]
    keyboard._plate.set_mounting_holes([(10.0, 5.0, 2.2)])
    holes = keyboard._plate.mounting_holes()
    assert [(h.x, h.y, h.diameter) for h in holes] == [(10.0, 5.0, 2.2)]
    assert holes[0].height == pytest.approx(keyboard._plate.size().height)


def test_a_pattern_for_another_plate_is_rejected():
    """The injected pattern is plate-local: its frame must be this plate."""
    import dataclasses

    from components.slide import compute_slide_budget
    from geometry.well_mounts import PlateFrame, well_mounts
    from main import BuildPipeline

    pipeline = BuildPipeline()
    config = pipeline.load_config()
    components = pipeline.load_components()
    placements = pipeline.place_layout(components).placements()
    budget = compute_slide_budget(config, components)
    keyboard = components["keyboard"]
    placement = next(p for p in placements if p.component is keyboard)
    mounts = well_mounts(config, budget, placement=placement)
    wrong = dataclasses.replace(
        mounts,
        frame=dataclasses.replace(
            mounts.frame, width=mounts.frame.width + 2.0
        ),
    )
    keyboard.set_well_mounts(wrong)
    with pytest.raises(ValueError, match="pattern is 235.25"):
        components["keyboard"]._plate.size()


# -- the plate's Well-mount pattern (ADR-0014, issue #14) -----------------

@pytest.fixture(scope="module")
def well_plate():
    """The slider's plate with the Well-mount pattern injected (#11/#18/#19)."""
    from components.slide import compute_slide_budget
    from geometry.well_mounts import PlateFrame, well_mounts
    from main import BuildPipeline

    pipeline = BuildPipeline()
    config = pipeline.load_config()
    components = pipeline.load_components()
    placements = pipeline.place_layout(components).placements()
    budget = compute_slide_budget(config, components)
    keyboard = components["keyboard"]
    placement = next(p for p in placements if p.component is keyboard)
    frame = PlateFrame.from_placement(
        placement,
        width=budget.well.plate_width,
        depth=budget.well.plate_depth,
    )
    mounts = well_mounts(config, budget, placement=placement)
    keyboard.set_well_mounts(mounts)
    return config, components, budget, placements, mounts, keyboard


def _rect_of(plan_rect):
    return (plan_rect.x0, plan_rect.y0, plan_rect.x1, plan_rect.y1)


def _circle_in_rect(x, y, r, rect, margin=0.0):
    eps = 1e-9
    return (
        x - r - margin >= rect[0] - eps
        and x + r + margin <= rect[2] + eps
        and y - r - margin >= rect[1] - eps
        and y + r + margin <= rect[3] + eps
    )


def _circle_hits_rect(x, y, r, rect):
    dx = max(rect[0] - x, 0.0, x - rect[2])
    dy = max(rect[1] - y, 0.0, y - rect[3])
    return dx * dx + dy * dy < r * r


def test_the_plate_carries_eight_m2_clearance_holes(well_plate):
    config, _, _, _, mounts, keyboard = well_plate
    plate = keyboard._plate
    holes = plate.mounting_holes()
    assert len(holes) == len(mounts.mounts) == 8
    screw = __import__("utilities.fasteners", fromlist=["screw"]).screw(
        str((config.keyboard.mounting or {}).get("screw", "M2"))
    )
    for hole, mount in zip(holes, mounts.mounts):
        assert (hole.x, hole.y) == pytest.approx(mount.plate_xy)
        assert hole.x, hole.y  # placed facts, not the origin
        assert hole.diameter == pytest.approx(screw.clearance)
        assert hole.diameter == pytest.approx(2.20)
        assert hole.height == pytest.approx(plate.size().height) == pytest.approx(1.5)


def test_every_clearance_hole_sits_in_its_ear_with_an_edge_margin(well_plate):
    config, _, _, _, mounts, keyboard = well_plate
    plate = keyboard._plate
    for mount in mounts.mounts:
        assert mount.ear is not None
        rect = _rect_of(mount.ear.rect)
        x, y = mount.plate_xy
        r = mount.clearance_hole_diameter / 2.0
        assert _circle_in_rect(x, y, r, rect, margin=mounts.boss_margin), (
            f"{mount.name}: hole misses its ear"
        )
        # The ear still overlaps the plate ring (the union is a real ligature).
        assert mount.ear.overlap >= config.material.minimum_feature


def test_no_ear_or_hole_intersects_a_switch_or_stabilizer_cutout(well_plate):
    _, _, _, _, mounts, keyboard = well_plate
    model = keyboard.plate_model()
    cutouts = list(model.switch_cutouts) + list(model.stabilizer_cutouts)
    for cut in cutouts:
        xs = [cut.x + vx for vx, _ in cut.vertices]
        ys = [cut.y + vy for _, vy in cut.vertices]
        box = (min(xs), min(ys), max(xs), max(ys))
        for mount in mounts.mounts:
            assert not _circle_hits_rect(
                *mount.plate_xy, mount.clearance_hole_diameter / 2.0, box
            ), f"{mount.name}: hole overlaps a cutout"
            ear = _rect_of(mount.ear.rect)
            assert not (
                ear[0] < box[2] and box[0] < ear[2] and ear[1] < box[3] and box[1] < ear[3]
            ), f"{mount.name}: ear overlaps a cutout"


def test_ears_do_not_overlap_each_other_and_stay_inside_the_case(well_plate):
    from case.slider_frame import SliderFrame

    config, components, budget, placements, mounts, _ = well_plate
    frame = SliderFrame.from_data(config, budget, components, placements)
    ears = [_rect_of(m.ear.rect) for m in mounts.mounts]
    for i, first in enumerate(ears):
        for second in ears[i + 1 :]:
            assert not (
                first[0] < second[2]
                and second[0] < first[2]
                and first[1] < second[3]
                and second[1] < first[3]
            )
    # Plan-frame ears against the chassis cavity (vertical end walls, the
    # band's inner X faces at the plate's Z).
    inner_x = frame.chassis_band_width / 2.0 - frame.wall
    inner_y = frame.depth / 2.0 - frame.wall
    for mount in mounts.mounts:
        rect = mounts.frame.to_plan_rect(mount.ear.rect)
        assert -inner_x <= rect.x0 and rect.x1 <= inner_x
        assert -inner_y <= rect.y0 and rect.y1 <= inner_y


def test_plate_footprint_cutouts_are_the_four_band_notches(well_plate):
    from keyboard.validation import _point_in_polygon

    _, _, _, _, mounts, keyboard = well_plate
    rects = keyboard.footprint_cutouts()
    assert len(rects) == len(mounts.notches) == 4
    assert sorted(rects) == sorted(_rect_of(notch.rect) for notch in mounts.notches)
    outline = keyboard.footprint_outline()
    assert outline
    half_d = keyboard._plate.size().depth / 2.0
    # The keyboard is placed rotated 180 deg, so the chassis' front band
    # columns (world -Y) notch the plate's **+Y** (spacebar) lip.
    for rect in rects:
        cx = (rect[0] + rect[2]) / 2.0
        # The bite is a gap in the sheet, the material just inboard is not.
        assert not _point_in_polygon(cx, half_d - (half_d - rect[1]) / 2.0, outline)
        assert _point_in_polygon(cx, rect[1] - 0.2, outline)


def test_the_plate_is_one_uniform_sheet_with_its_ears(well_plate):
    _, _, _, _, mounts, keyboard = well_plate
    plate = keyboard._plate
    assert plate.size().height == pytest.approx(1.5)
    # Every ear is plate thickness: an extension of the sheet, not a boss.
    for mount in mounts.mounts:
        assert mount.ear.thickness == pytest.approx(1.5)
    # The outline reaches into every ear, i.e. the sheet really grows, on both
    # lips (the ears are on the plate's own front and rear edges).
    outline = keyboard.footprint_outline()
    ys = [y for _, y in outline]
    assert min(ys) == pytest.approx(-(80.85 / 2.0) - 4.6)
    assert max(ys) == pytest.approx(80.85 / 2.0 + 4.6)


def test_the_m2_stack_is_bottom_up_below_the_deck_bosses(well_plate):
    """Plate clearance hole -> insert boss, in Z: nothing is below the Tray."""
    _, components, budget, _, mounts, keyboard = well_plate
    plate_top = keyboard._plate_raise + keyboard._plate.size().height
    for mount in mounts.mounts:
        assert mount.boss_z0 == pytest.approx(plate_top)
        assert mount.boss_z0 == pytest.approx(budget.well.plate_top)
        assert mount.boss_z1 > mount.boss_z0
    # No Tray-floor standoffs: the keyboard component still declares none.
    assert keyboard.mounting_holes() == []
    assert len(keyboard.plate_mounting_holes()) == 8


def test_plate_holes_align_with_the_deck_bosses_in_the_assembly(well_plate):
    """The plate's eight holes sit under the Deck's eight bosses (issue #19).

    The keyboard is placed rotated 180 deg, so the plate's own frame is the
    point reflection of the chassis plan. This asserts the two frames through
    the *layout's* transform, for all eight stations: a plate hole must land on
    its Deck boss, the plate must carry material under that boss (the ear), and
    no notch may eat it.
    """
    from keyboard.validation import _point_in_polygon

    _, _, _, placements, mounts, keyboard = well_plate
    placement = next(p for p in placements if p.component is keyboard)
    holes = keyboard.plate_mounting_holes()
    outline = keyboard.footprint_outline()
    cutouts = keyboard.footprint_cutouts()
    for mount in mounts.mounts:
        # One hole per station, at the station's *plate-local* point.
        hole = next(
            h
            for h in holes
            if (h.x, h.y) == pytest.approx(mount.plate_xy)
        )
        # Placed, that hole is exactly on its Deck boss (world frame).
        wx, wy, _ = placement.world_offset(hole.x, hole.y, 0.0)
        assert (wx, wy) == pytest.approx(mount.world_xy)

        # The plate is material under the boss: the boss's plan point, and a
        # ring just outside the clearance hole, are inside the eared outline.
        assert _point_in_polygon(hole.x, hole.y, outline), mount.name
        assert mount.ear is not None
        assert (
            mount.ear.rect.x0 <= hole.x <= mount.ear.rect.x1
            and mount.ear.rect.y0 <= hole.y <= mount.ear.rect.y1
        )
        r = hole.diameter / 2.0 + 0.3
        for dx, dy in ((r, 0.0), (-r, 0.0), (0.0, r), (0.0, -r)):
            assert _point_in_polygon(hole.x + dx, hole.y + dy, outline), (
                f"{mount.name}: no plate material under the boss at "
                f"({hole.x + dx:.2f}, {hole.y + dy:.2f})"
            )
        # And no band-notch removes that material.
        for rect in cutouts:
            assert not (
                rect[0] <= hole.x <= rect[2] and rect[1] <= hole.y <= rect[3]
            ), f"{mount.name}: its hole is inside a notch"
    # Eight stations, eight holes: nothing was dropped or duplicated.
    assert len(holes) == len(mounts.mounts) == 8
    assert len({(round(h.x, 6), round(h.y, 6)) for h in holes}) == 8
