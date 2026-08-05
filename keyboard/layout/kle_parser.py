"""KLE (Keyboard Layout Editor) JSON parser.

Parses the KLE JSON format into a list of :class:`Key` objects with absolute
positions. Supports the standard KLE metadata keys (w, h, x, y, r, rx, ry, a)
and the kb_builder per-key overrides (_t, _s, _r, _rs, _k).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from keyboard.layout.key import Key


def parse_kle(data: list[list[Any]]) -> list[list[Key]]:
    """Parse KLE JSON rows into a list of rows, each a list of Key objects.

    Parameters
    ----------
    data : list[list]
        The top-level array from a KLE JSON file. Each element is either a
        row (list) or a global metadata dict (ignored here).

    Returns
    -------
    list[list[Key]]
        Keys grouped by row, with absolute (x, y) positions in key units.
    """
    rows: list[list[Key]] = []
    row_y: float = 0.0
    for row_data in data:
        if not isinstance(row_data, list):
            continue
        row = _parse_row(row_data, row_y)
        if row:
            rows.append(row)
            # Next row sits below the tallest key in this row.
            max_h = max(k.height for k in row)
            row_y += max_h
    return rows


def _parse_row(row_data: list[Any], row_y: float = 0.0) -> list[Key]:
    """Parse one KLE row into Key objects with absolute positions."""
    keys: list[Key] = []
    x: float = 0.0
    y: float = row_y
    pending: dict[str, Any] = {}

    for item in row_data:
        if isinstance(item, dict):
            # Metadata dict — applies to the next key only (KLE one-shot
            # semantics), then reverts to the defaults below.
            pending.update(item)
            if "x" in item:
                x += float(item["x"])
            if "y" in item:
                y += float(item["y"])
            if "a" in item:
                pass  # alignment — not stored per-key
            continue

        if isinstance(item, (int, float)):
            # Gap — shift x by this many units
            x += float(item)
            continue

        if isinstance(item, str):
            # Key legend
            w = float(pending.pop("w", 1.0))
            h = float(pending.pop("h", 1.0))
            rx = float(pending.pop("rx", 0.0))
            ry = float(pending.pop("ry", 0.0))
            r = float(pending.pop("r", 0.0))
            _t = pending.pop("_t", None)
            _s = pending.pop("_s", None)
            _r = pending.pop("_r", None)
            _rs = pending.pop("_rs", None)
            _k = pending.pop("_k", None)

            key_x = x + w / 2.0
            key_y = y + h / 2.0

            keys.append(Key(
                x=key_x,
                y=key_y,
                width=w,
                height=h,
                rotation=r,
                rotation_x=rx,
                rotation_y=ry,
                legend=item,
                switch_type=str(_t) if _t is not None else None,
                stabilizer_type=str(_s) if _s is not None else None,
                switch_rotation=float(_r) if _r is not None else None,
                stab_rotation=float(_rs) if _rs is not None else None,
                kerf=float(_k) if _k is not None else None,
            ))

            x += w

    return keys


def load_kle(path: str | Path) -> list[list[Key]]:
    """Load a KLE JSON file and parse it into rows of Key objects."""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return parse_kle(data)
