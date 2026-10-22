"""Well: the rim stays below the switch tops."""

import math

from geometry.well import rim_height


def test_rim_top_stays_margin_below_switch_top():
    h = rim_height(switch_top=5.5, deck_thickness=2.0, margin=1.0)
    assert math.isclose(h, 2.5)
    assert 2.0 + h < 5.5


def test_rim_never_negative():
    assert rim_height(switch_top=2.0, deck_thickness=2.0, margin=1.0) == 0.0


def test_config_loads_well_margin():
    from utilities.config_loader import load_config
    assert load_config("config/default.yaml").well.switch_margin == 1.0
