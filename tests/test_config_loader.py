"""Tests for config loading and dataclass mapping."""

from utilities.config_loader import load_config, build_config, Config, Display, Flex


def test_load_default():
    cfg = load_config("config/default.yaml")
    assert isinstance(cfg, Config)
    assert cfg.wall_thickness == 2.0


def test_display_flex():
    cfg = load_config("config/default.yaml")
    assert isinstance(cfg.display, Display)
    assert isinstance(cfg.display.flex, Flex)
    assert cfg.display.flex.width == 38.5
    assert cfg.display.flex.thickness == 1.0
    # The ribbon is taped flat in the FPC guard's channel, so the folded-loop
    # allowance is gone; the measured flat stack replaces it.
    assert cfg.display.flex.stack == 0.6
    assert not hasattr(cfg.display.flex, "fold")


def test_fpc_guard():
    cfg = load_config("config/default.yaml")
    guard = cfg.slide.fpc_guard
    assert guard.total == 1.6
    assert 0.0 < guard.recess < guard.total
    assert guard.margin > 0.0
    assert guard.sag_allowance >= 0.0
    assert guard.grille_slot > 0.0
    assert guard.fit >= 0.0
    # The channel has to swallow the measured ribbon stack.
    assert guard.recess >= cfg.display.flex.stack


def test_hardware_sections():
    cfg = load_config("config/default.yaml")
    assert "sbc" in cfg.hardware
    assert "battery" in cfg.hardware
    assert "driver_board" in cfg.hardware
    assert cfg.hardware["battery"]["present"] is True


def test_wall_alias():
    cfg = load_config("config/default.yaml")
    assert cfg.wall_thickness == cfg.wall.thickness


def test_merge_topics():
    cfg = load_config("config/default.yaml", topics=("display", "keyboard", "hardware"))
    assert cfg.display.width > 0
    assert cfg.keyboard.columns == 12
