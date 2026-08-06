"""Tests for layout placement."""

from layouts import make_layout
from utilities.config_loader import load_config
from main import BuildPipeline


def _components():
    p = BuildPipeline("config/default.yaml")
    cfg = p.load_config()
    return p.load_components()


def _placement(placements, name):
    return next(p for p in placements if p.component.name == name)


def test_default_placements():
    comps = _components()
    layout = make_layout("default", comps)
    placements = layout.placements()
    assert len(placements) == 5  # keyboard, sbc, battery, display, driver
    driver = _placement(placements, "HDMI Driver Board")
    assert driver.rotation == 180.0
    assert driver.flip_x is True
    assert driver.x == -9.5
    assert driver.y == 5.0
    assert driver.z == 59.5  # 0.5 mm below the display Z (backside clearance)


def test_compact_placements():
    comps = _components()
    layout = make_layout("compact", comps)
    placements = layout.placements()
    assert len(placements) == 6  # keyboard, sbc, battery, hub, display, driver
    driver = _placement(placements, "HDMI Driver Board")
    assert driver.rotation == 180.0
    assert driver.flip_x is True
    assert driver.x == -9.5
    assert driver.y == 5.0
    assert driver.z == 59.5  # 0.5 mm below the display Z (backside clearance)


def test_default_no_collisions():
    from utilities.validation import ValidationReport, check_collisions
    comps = _components()
    layout = make_layout("default", comps)
    r = ValidationReport()
    check_collisions(layout.placements(), r)
    assert r.passed, r.checks[0].message


def test_compact_no_collisions():
    from utilities.validation import ValidationReport, check_collisions
    comps = _components()
    layout = make_layout("compact", comps)
    r = ValidationReport()
    check_collisions(layout.placements(), r)
    assert r.passed, r.checks[0].message


def test_default_v2_driver_flipped():
    comps = _components()
    layout = make_layout("default_v2", comps)
    driver = _placement(layout.placements(), "HDMI Driver Board")
    display = _placement(layout.placements(), "Display 8.8\" 1920x480")
    assert driver.rotation == 180.0
    assert driver.flip_x is True
    assert driver.x == -9.5
    assert driver.y == 5.0
    # Flipped board hangs below its origin: top face 0.5 mm below the
    # display's Z so the PCB backside clears the panel.
    assert driver.z == display.z - 0.5
    assert driver.z_bounds() == (display.z - 0.5 - driver.component.size().height, display.z - 0.5)


def test_compact_v2_driver_flipped():
    comps = _components()
    layout = make_layout("compact_v2", comps)
    driver = _placement(layout.placements(), "HDMI Driver Board")
    assert driver.rotation == 180.0
    assert driver.flip_x is True
    assert driver.x == -9.5
    assert driver.y == 5.0


def test_recipe_default_driver_flipped():
    p = BuildPipeline("config/default.yaml")
    cfg = p.load_config()
    comps = p.load_components()
    layout = make_layout("recipe_default", comps, config=cfg)
    driver = _placement(layout.placements(), "HDMI Driver Board")
    assert driver.rotation == 180.0
    assert driver.flip_x is True
    assert driver.x == -9.5
    assert driver.y == 5.0


def test_recipe_compact_driver_flipped():
    p = BuildPipeline("config/default.yaml")
    cfg = p.load_config()
    comps = p.load_components()
    layout = make_layout("recipe_compact", comps, config=cfg)
    driver = _placement(layout.placements(), "HDMI Driver Board")
    assert driver.rotation == 180.0
    assert driver.flip_x is True
    assert driver.x == -9.5
    assert driver.y == 5.0


def test_flipped_driver_does_not_collide_with_display():
    from utilities.validation import ValidationReport, check_collisions
    comps = _components()
    layout = make_layout("default_v2", comps)
    r = ValidationReport()
    check_collisions(layout.placements(), r)
    assert r.passed, r.checks[0].message


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
    from utilities.config_loader import load_config
    comps = _components()
    cfg = load_config("config/default.yaml")
    layout = make_layout("default_v2", comps)
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
