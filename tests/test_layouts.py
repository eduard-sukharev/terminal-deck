"""Tests for layout placement."""

import pytest

from layouts import make_layout
from utilities.config_loader import load_config
from main import BuildPipeline


def _components():
    p = BuildPipeline("config/default.yaml")
    p.load_config()
    return p.load_components()


def _placement(placements, name):
    return next(p for p in placements if p.component.name == name)


def _layout(comps=None, cfg=None):
    """The one layout: the compact clamshell recipe."""
    if comps is None:
        p = BuildPipeline("config/default.yaml")
        cfg = p.load_config()
        comps = p.load_components()
    return make_layout("compact", comps, config=cfg)


def test_unknown_layout_rejected():
    import pytest
    with pytest.raises(ValueError):
        make_layout("default")


def test_compact_placements():
    p = BuildPipeline("config/default.yaml")
    cfg = p.load_config()
    placements = _layout(p.load_components(), cfg).placements()
    # keyboard, sbc, sbc_plug, hdmi_plug_sbc, controller, battery, hub,
    # display, driver, hdmi_plug_driver
    assert len(placements) == 10


def test_compact_no_collisions():
    from utilities.validation import ValidationReport, check_collisions
    r = ValidationReport()
    check_collisions(_layout().placements(), r)
    assert r.passed, r.checks[0].message


def test_driver_flipped_behind_panel():
    placements = _layout().placements()
    driver = _placement(placements, "HDMI Driver Board")
    display = _placement(placements, "Display 8.8\" 1920x480")
    assert driver.rotation == 180.0
    assert driver.flip_x is True
    assert driver.x == -9.5
    assert driver.y == 5.0
    # Flipped board hangs below its origin: top face 0.5 mm below the
    # display's Z so the PCB backside clears the panel.
    assert driver.z == display.z - 0.5
    assert driver.z_bounds() == (
        display.z - 0.5 - driver.component.size().height, display.z - 0.5
    )


def test_world_offset_rotation_and_flip():
    from pytest import approx
    from layouts.base import Placement
    comps = _components()
    driver = comps["driver"]
    # 180° about Z then flip about X: local (x, y, z) -> (-x, y, -z).
    p = Placement(driver, -9.5, 5.0, 180.0, 60.0, flip_x=True)
    assert p.world_offset(24.5, -5.0, 1.8) == approx((-9.5 - 24.5, 0.0, 58.2))
    assert p.world_offset(0.0, 0.0, 0.0) == (-9.5, 5.0, 60.0)
    # Local +X maps to world -X; local +Y stays +Y.
    assert p.world_direction(1.0, 0.0, 0.0) == approx((-1.0, 0.0, 0.0))
    assert p.world_direction(0.0, 1.0, 0.0) == approx((0.0, 1.0, 0.0))
    # The FPC slot (local -X) therefore faces east (+X) in the world.
    assert p.world_direction(-1.0, 0.0, 0.0) == approx((1.0, 0.0, 0.0))


def test_world_offset_no_transform():
    from layouts.base import Placement
    comps = _components()
    driver = comps["driver"]
    p = Placement(driver, 1.0, 2.0, 0.0, 3.0)
    assert p.world_offset(4.0, 5.0, 6.0) == (5.0, 7.0, 9.0)
    assert p.z_bounds() == (3.0, 3.0 + driver.size().height)


def test_bosses_rotation_and_flip():
    from pytest import approx
    from assemblies.assembly import Assembly
    comps = _components()
    cfg = load_config("config/default.yaml")
    layout = make_layout("compact", comps, config=cfg)
    assembly = Assembly(layout.placements(), cfg)
    driver = _placement(layout.placements(), "HDMI Driver Board")
    # Driver mounting holes: NW/NE/SE at local (+/-24.5, +/-19.75) (3.0 inset).
    # Under 180° rot + X flip, local (x, y) -> (-x, y).
    boss_points = [(x, y) for x, y, _ in assembly.bosses([driver])]
    cx, cy = driver.x, driver.y
    expected = {
        (cx - 24.5, cy + 19.75),
        (cx + 24.5, cy + 19.75),
        (cx - 24.5, cy - 19.75),
    }
    assert len(boss_points) == len(expected)
    for bx, by in boss_points:
        assert any(
            bx == approx(ex) and by == approx(ey) for ex, ey in expected
        )


# ── Sloped deck / tilt ────────────────────────────────────────────────────


def _base():
    from assemblies.assembly import Assembly
    from case.base import Base
    p = BuildPipeline("config/default.yaml")
    cfg = p.load_config()
    comps = p.load_components()
    placements = p.place_layout(comps).placements()
    return Base(Assembly(placements, cfg), cfg, keyboard=comps.get("keyboard")), cfg


def test_deck_rises_toward_the_rear_then_flattens():
    """The wedge is flat at the front, rises to the keyboard's rear edge
    (the knee), then holds flat the rest of the way to the actual rear
    wall — not a full-depth plane; see Base._deck_knee_y."""
    import math
    base, cfg = _base()
    depth = base.size().depth
    front_y = depth / 2
    knee_y = base._deck_knee_y()
    assert knee_y is not None
    front, knee, rear = (
        base.deck_level_at(front_y), base.deck_level_at(knee_y),
        base.deck_level_at(-front_y),
    )
    assert front < knee
    assert knee == pytest.approx(rear)  # flat behind the knee
    assert knee - front == pytest.approx(
        (front_y - knee_y) * math.tan(math.radians(cfg.deck.slope))
    )
    assert base.deck_rear_level() == pytest.approx(rear)


def test_deck_level_at_is_linear_in_front_of_the_knee():
    """deck_level_at is a plane in front of the knee, not a fudge — and
    constant (not still rising) behind it."""
    base, _ = _base()
    knee_y = base._deck_knee_y()
    assert knee_y is not None
    # Three points strictly in front of the knee: linear.
    front_y = base.size().depth / 2
    step = (front_y - knee_y) / 3.0
    a, b, c = (
        base.deck_level_at(y)
        for y in (knee_y + 2 * step, knee_y + step, knee_y)
    )
    assert (a - b) == pytest.approx(b - c)
    # Behind the knee: flat, not still rising.
    assert base.deck_level_at(knee_y - 5.0) == pytest.approx(base.deck_level_at(knee_y))
    assert base.deck_level_at(-front_y) == pytest.approx(base.deck_level_at(knee_y))


def test_keyboard_is_tilted_onto_the_deck():
    """The keyboard rides the wedge, pivoting about its front-bottom edge."""
    base, cfg = _base()
    kb = base._keyboard_placement()
    assert kb.tilt_x == pytest.approx(-cfg.deck.slope)
    # Front-bottom edge stays on the floor; the rise all goes to the rear.
    assert kb.z_bounds()[0] == pytest.approx(0.0, abs=1e-6)


def test_keyboard_plate_top_meets_the_deck_plane():
    """The deck and the keyboard it covers stay coincident under tilt."""
    import math
    base, _ = _base()
    kb = base._keyboard_placement()
    stack = base.keyboard._plate_raise + base.keyboard._plate_thickness
    plate_top = kb.z + stack * math.cos(math.radians(kb.tilt_x))
    assert base.deck_level_at(kb.y) == pytest.approx(plate_top)


def test_flat_deck_reproduces_untilted_geometry():
    """slope 0 is a real no-op, so the wedge is opt-in."""
    from dataclasses import replace
    from assemblies.assembly import Assembly
    from case.base import Base
    p = BuildPipeline("config/default.yaml")
    loaded = p.load_config()
    cfg = replace(loaded, deck=replace(loaded.deck, slope=0.0))
    comps = p.load_components()
    # Layout is built from the same recipe against the flat config.
    layout = make_layout("compact", comps, config=cfg)
    base = Base(Assembly(layout.placements(), cfg), cfg, keyboard=comps.get("keyboard"))
    kb = base._keyboard_placement()
    assert kb.tilt_x == 0.0
    assert base.deck_level_at(-50.0) == pytest.approx(base.deck_level_at(50.0))


def test_tilt_widens_z_bounds_and_footprint():
    """A tilt swings depth into height, so both bounds grow."""
    from layouts.base import Placement
    base, _ = _base()
    kb = base._keyboard_placement()
    flat = Placement(kb.component, kb.x, kb.y, kb.rotation, kb.z, kb.flip_x, 0.0)
    assert kb.z_bounds()[1] - kb.z_bounds()[0] > flat.z_bounds()[1] - flat.z_bounds()[0]
    _, ky0, _, ky1 = kb.box
    _, fy0, _, fy1 = flat.box
    assert (ky1 - ky0) > (fy1 - fy0)


def test_lid_clears_the_tilted_keyboard():
    """The lid is derived from the keyboard's real top, not its nominal height."""
    base, cfg = _base()
    kb = base._keyboard_placement()
    _placement(base.assembly.placements, 'Display 8.8" 1920x480')
    driver = _placement(base.assembly.placements, "HDMI Driver Board")
    # The rear keycaps rise above the nominal component height...
    assert kb.z_bounds()[1] > kb.component.size().height
    # ...and the driver above them still clears.
    assert driver.z_bounds()[0] > kb.z_bounds()[1]


# ── Buried parts under the sloped plate ───────────────────────────────────


def test_switch_band_is_reported_as_occupied():
    """The switch bodies hang below the plate and must be collision-visible.

    Reporting only the plate (as this once did) hid a 7 mm band, letting a
    board be placed straight through the switch pins with every check green.
    """
    p = BuildPipeline("config/default.yaml")
    p.load_config()
    kb = p.load_components()["keyboard"]
    lowest = min(z for _, _, z, _ in kb.occupied_volumes())
    assert lowest == pytest.approx(kb._plate_raise - kb.switch_bottom_protrusion)
    assert lowest < kb._plate_raise


def test_switch_band_is_narrower_than_the_plate():
    """The plate's switch-free edge margin must stay genuinely free."""
    p = BuildPipeline("config/default.yaml")
    p.load_config()
    kb = p.load_components()["keyboard"]
    gx0, gy0, gx1, gy1 = kb.switch_grid_extent()
    plate = kb._plate.size()
    assert gx1 - gx0 < plate.width
    assert gy1 - gy0 < plate.depth


def test_plate_raise_clears_the_buried_sbc():
    """The plate stands tall enough that the SBC clears the switch bodies."""
    base, _ = _base()
    kb = base._keyboard_placement()
    sbc = _placement(base.assembly.placements, "Orange Pi Zero 2W")
    assert kb.z_bounds()[0] == pytest.approx(0.0, abs=1e-6)
    # Sized by plate_raise_for_buried, so it must exceed the bare-floor value.
    assert base.keyboard._plate_raise > (
        base.keyboard.switch_bottom_protrusion + base.keyboard._floor_gap
    )
    # And the SBC really is underneath it, not beside it.
    kx0, ky0, kx1, ky1 = kb.box
    sx0, sy0, sx1, sy1 = sbc.box
    assert sy0 >= ky0 - 1e-6 and sy1 <= ky1 + 1e-6


def test_plug_is_centred_on_its_port_not_offset_from_it():
    """The plug body must be centered on its origin in XY.

    ``Placement.box`` assumes that; a body modelled as extending *from* the
    origin gets collision-checked half a plug-length from where it is drawn.
    """
    p = BuildPipeline("config/default.yaml")
    p.load_config()
    comps = p.load_components()
    plug, _sbc = comps["sbc_plug"], comps["sbc"]
    conn = plug.host_connector()
    ox, oy, oz = plug.reference_origin()
    # Origin sits a full half-length beyond the port face, i.e. at the centre.
    face_y = conn.y + conn.direction[1] * conn.depth / 2.0
    assert oy == pytest.approx(face_y + conn.direction[1] * plug.protrusion / 2.0)
    # Z biased down half the height so the body straddles the opening.
    assert oz + plug.height / 2.0 == pytest.approx(conn.z)


def test_plug_port_index_selects_the_other_usb_c():
    """port_index is the assembly-time choice of which port carries the cable."""
    from components.usb_c_plug import UsbCPlug
    p = BuildPipeline("config/default.yaml")
    p.load_config()
    sbc = p.load_components()["sbc"]
    a = UsbCPlug({"port_index": 0}, host=sbc).reference_origin()
    b = UsbCPlug({"port_index": 1}, host=sbc).reference_origin()
    assert a[0] != b[0]


def test_plug_rejects_out_of_range_port():
    from components.usb_c_plug import UsbCPlug
    p = BuildPipeline("config/default.yaml")
    p.load_config()
    sbc = p.load_components()["sbc"]
    with pytest.raises(ValueError, match="out of range"):
        UsbCPlug({"port_index": 9}, host=sbc).reference_origin()


# ── Round-profile battery clearance / clearance tilt consistency ──────────


def test_battery_occupied_volumes_narrow_at_the_tips():
    """A cell's round cross-section, sliced along its curve, must be
    narrowest at the ends and widest at the equator — not a flat box.
    """
    from components.battery import Battery
    b = Battery({"battery": {"count": 2, "arrangement": "side_by_side"}})
    vols = b.occupied_volumes()
    n = b._occupied_volume_slices
    one_cell = vols[:n]  # first cell's n consecutive slices, tip to tip
    heights = [v[3].height for v in one_cell]
    assert heights[0] < heights[n // 2]
    assert max(heights) == pytest.approx(b.cell_diameter, abs=1e-6)


def test_clearance_resolver_matches_collision_check_under_tilt():
    """The clearance resolver's Z-span must agree with the collision
    checker's for a tilted volume — they diverged once (clearance used a
    naive center+height, undercounting a tilted sub-volume's true reach),
    letting a clearance check pass a placement collision detection rejects.
    """
    from layouts.base import volume_z_span, Placement
    from components.battery import Battery
    base, _ = _base()
    kb = base._keyboard_placement()
    Placement(Battery({}), 0.0, kb.y, 0.0, kb.z, False, kb.tilt_x)
    for ax, ay, az, box in kb.component.occupied_volumes()[:4]:
        wx, wy, wz = kb.world_offset(ax, ay, az)
        z0, z1 = volume_z_span(kb, box, wz)
        # Sanity: the tilt must actually widen the span beyond the raw height
        # for this to be a meaningful check.
        assert (z1 - z0) >= box.height - 1e-9


def test_battery_clears_the_floor_ribs():
    """The pack must be raised clear of the floor's stiffening ribs (the
    same rib_height every other floor-mounted part uses), not left flush on
    the floor (z=0), which would drive it straight through them. Distinct
    from `Battery.cradle_height`, which only sizes the cradle block's own
    height (how far it wraps the cell), not this raise.
    """
    from geometry.ribs import rib_height
    base, cfg = _base()
    bat = _placement(base.assembly.placements, "Battery")
    assert bat.z == pytest.approx(rib_height(cfg.wall_thickness))


def test_battery_noses_forward_of_a_flush_rear_wall_position():
    """The keyboard's rear edge must sit measurably closer to the rear wall
    than a plain flush 2mm gap past the battery would place it — i.e. the
    battery's round-profile nose-in actually claws back case depth, not a
    zero-effect no-op.
    """
    base, cfg = _base()
    bat = _placement(base.assembly.placements, "Battery")
    kb = base._keyboard_placement()
    _, bat_y0, _, bat_y1 = bat.box
    flush_kb_rear = bat_y1 + 2.0  # the old (pre-nose-in) recipe's plain gap
    _, kb_y0, _, kb_y1 = kb.box
    assert kb_y0 < flush_kb_rear - 1e-6


# ── Boss/standoff collisions ───────────────────────────────────────────────


def test_controller_clears_the_keyboard_plates_own_mounting_bosses():
    """The RP2040 must not sit under one of the plate's own corner standoffs
    — those run floor to plate-underside, so an overlap is a real collision,
    not just a tight XY fit.
    """
    import math
    base, cfg = _base()
    kb = base._keyboard_placement()
    ctl = _placement(base.assembly.placements, "RP2040-Zero")
    cx0, cy0, cx1, cy1 = ctl.box
    r = base.assembly.bosses()  # all mounting bosses, world frame
    for bx, by, spec in r:
        # Only the keyboard's own plate-mount bosses run tall enough
        # (floor to plate underside) to matter here.
        if spec.height < kb.component._plate_raise - 1.0:
            continue
        nx = min(max(bx, cx0), cx1)
        ny = min(max(by, cy0), cy1)
        d = math.hypot(bx - nx, by - ny)
        assert d >= spec.outer_diameter / 2, (
            f"controller overlaps a plate-mount boss at ({bx:.1f},{by:.1f})"
        )


def test_deck_columns_clear_every_base_floor_component():
    """No Deck column may land on a base-floor component's solid volume: it
    runs from the floor to the Parting plane and would punch through the part.
    """
    base, cfg = _base()
    r = base.column_geometry()["outer"] / 2
    columns = base.columns()
    assert len(columns) >= 4, "fewer Deck columns than the flat-deck baseline"
    rects = base.assembly.keepout_rects(0.0, base.parting_height(), base._base_placements())
    for col in columns:
        for x0, x1, y0, y1 in rects:
            hit = col.x + r > x0 and col.x - r < x1 and col.y + r > y0 and col.y - r < y1
            assert not hit, f"column ({col.x:.1f},{col.y:.1f}) lands on a component"


def test_deck_columns_are_not_squeezed_together():
    """Two columns snapped into the same tight gap must still be far enough
    apart to exist as separate printed posts.
    """
    import math
    base, cfg = _base()
    od = base.column_geometry()["outer"]
    columns = base.columns()
    for i in range(len(columns)):
        for j in range(i + 1, len(columns)):
            d = math.hypot(columns[i].x - columns[j].x, columns[i].y - columns[j].y)
            assert d >= od, f"columns {i} and {j} nearly touch"


def test_deck_columns_spread_across_most_of_the_case_width():
    """Columns should support the Deck across a meaningful part of the width,
    not cluster on one side."""
    base, cfg = _base()
    xs = [c.x for c in base.columns()]
    size = base.size()
    assert max(xs) - min(xs) >= 0.5 * (size.width - 2 * cfg.wall_thickness)


def test_every_deck_section_has_a_column_near_its_seam():
    base, cfg = _base()
    reach = cfg.deck.seam_screw_reach
    seam_x = cfg.split["deck"].seams()[0].x
    xs = [c.x for c in base.columns()]
    assert any(seam_x - reach <= x < seam_x for x in xs)
    assert any(seam_x < x <= seam_x + reach for x in xs)


def test_plate_has_eight_standoffs_and_the_seam_ones_clear_the_sbc():
    """Four edge + four Seam standoffs; the Seam ones stand clear of the board
    buried under the plate (they run floor to plate)."""
    base, cfg = _base()
    kb = base._keyboard_placement().component
    holes = kb.mounting_holes()
    assert len(holes) == 8
    sbc = _placement(base.assembly.placements, "Orange Pi Zero 2W")
    sx0, sy0, sx1, sy1 = sbc.box
    kp = base._keyboard_placement()
    for h in holes:
        wx, wy, _ = kp.world_offset(h.x, h.y, 0.0)
        inside = sx0 < wx < sx1 and sy0 < wy < sy1
        assert not inside, f"plate standoff at ({wx:.1f}, {wy:.1f}) is inside the SBC"


def _hinged_base():
    from dataclasses import asdict
    from components.hinge import Hinge
    base, cfg = _base()
    base.hinge = Hinge(asdict(cfg.hinge), wall_thickness=cfg.wall_thickness)
    return base, cfg


def test_every_deck_section_has_a_knuckle_screw_above_the_hub():
    base, cfg = _hinged_base()
    sites = base.deck_knuckle_sites()
    assert set(sites) == {"left", "right"}
    r = base.knuckle_boss_spec().outer_diameter / 2
    zp = base.parting_height()
    seam_x = cfg.split["deck"].seams()[0].x
    for name, pts in sites.items():
        assert pts, f"no knuckle screw into the {name} Deck Section"
        for x, z in pts:
            assert z - r >= zp  # the boss stands on the Parting plane, over the hub
            assert (x < seam_x) == (name == "left")
            assert abs(x - seam_x) > r  # clear of the Seam


def test_deck_knuckle_screw_is_stock_and_engages_the_insert():
    base, _ = _hinged_base()
    screw = base.deck_knuckle_screw()
    assert screw.size == "M3" and screw.engagement >= 3.0


def test_deck_knuckle_bosses_clear_the_seam_check():
    base, _ = _hinged_base()
    names = [f.name for f in base.structural_features() if f.name.startswith("deck knuckle")]
    assert len(names) == sum(len(p) for p in base.deck_knuckle_sites().values())
