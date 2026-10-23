"""Rib layout clears the Seam bands (ADR 0003)."""

from geometry.ribs import rib_layout

PANEL_W, PANEL_D, WALL = 232.0, 114.0, 2.0
BAND = ((-42.0, -34.0), (34.0, 42.0))


def _clear(positions, thickness, bands):
    return all(
        pos + thickness / 2 <= lo or pos - thickness / 2 >= hi
        for pos in positions for lo, hi in bands
    )


def test_default_layout_is_unchanged_without_bands():
    spec = rib_layout(PANEL_W, PANEL_D, WALL)
    assert spec.positions == tuple(-104 + 12 + i * 24 for i in range(8))


def test_ribs_move_off_a_seam_band():
    plain = rib_layout(PANEL_W, PANEL_D, WALL)
    # The nominal rib at x=-44 sits at the left band's edge; at x=28/52 around the right.
    clear = rib_layout(PANEL_W, PANEL_D, WALL, avoid=((-46.0, -34.0), (34.0, 46.0)))
    assert not _clear(plain.positions, plain.thickness, ((-46.0, -34.0),))
    assert _clear(clear.positions, clear.thickness, ((-46.0, -34.0), (34.0, 46.0)))


def test_rib_count_is_preserved_when_a_clear_spot_exists():
    plain = rib_layout(PANEL_W, PANEL_D, WALL)
    clear = rib_layout(PANEL_W, PANEL_D, WALL, avoid=BAND)
    assert len(clear.positions) == len(plain.positions)
    assert _clear(clear.positions, clear.thickness, BAND)


def test_moved_ribs_stay_inside_the_panel_and_apart():
    clear = rib_layout(PANEL_W, PANEL_D, WALL, avoid=BAND)
    half = PANEL_W / 2
    assert all(abs(p) + clear.thickness / 2 < half for p in clear.positions)
    gaps = [b - a for a, b in zip(clear.positions, clear.positions[1:])]
    assert all(g >= clear.thickness * 2 for g in gaps)


def test_symmetric_bands_keep_a_symmetric_layout_symmetric_enough():
    clear = rib_layout(PANEL_W, PANEL_D, WALL, avoid=BAND)
    assert _clear(clear.positions, clear.thickness, BAND)
