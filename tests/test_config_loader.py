"""Tests for config loading and dataclass mapping."""

from utilities.config_loader import load_config, build_config, Config, Display, Flex


def test_load_default():
    cfg = load_config("config/default.yaml")
    assert isinstance(cfg, Config)
    assert cfg.wall_thickness == 2.5


def test_display_flex():
    cfg = load_config("config/default.yaml")
    assert isinstance(cfg.display, Display)
    assert isinstance(cfg.display.flex, Flex)
    assert cfg.display.flex.width == 38.5
    assert cfg.display.flex.thickness == 1.0
    assert cfg.display.flex.fold == 6.0


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
