"""kb_builder stabilizer types — 3 cutout families transcribed from swill/kb_builder.

Each type is registered as a separate :class:`StabilizerProtocol` family.
Per-key ``_s`` codes 0-1 are accepted (mirroring kb_builder's ``range(2)``
check); code 2 and unknown values fall back to the config default.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from keyboard.registry import register_stabilizer

_REFERENCE = Path(__file__).resolve().parent.parent / "reference" / "stabilizer_cutouts.yaml"

with open(_REFERENCE, "r") as _f:
    _DATA = yaml.safe_load(_f)

_CODE_TO_FAMILY: dict[int, str] = {}
_FAMILY_TO_ENTRY: dict[str, dict[str, Any]] = {}
for entry in _DATA["types"]:
    name: str = entry["name"]
    code: int = entry["code"]
    _CODE_TO_FAMILY[code] = name
    _FAMILY_TO_ENTRY[name] = entry

_CENTER_OFFSETS: dict[str, float] = _DATA["center_offsets"]
_DEFAULT_OFFSET: float = _DATA["default_offset"]

# Regex for symbolic vertex tokens: [±](x)?(±num)(±k)
_VERTEX_RE = re.compile(
    r"^([+-]?)"       # optional sign
    r"(x)?"           # optional x
    r"([+-]?(?:\d+(?:\.\d+)?))?"  # optional number
    r"([+-]k)?$"      # optional ±k
)


def _resolve_vertex(token: str, x: float, k: float) -> float:
    """Resolve a symbolic vertex coordinate to a float.

    Token format: ``[±](x)?(±num)(±k)``, e.g. ``"7-k"``, ``"x+4.2-k"``,
    ``"-x-1.65+k"``.
    """
    m = _VERTEX_RE.match(token)
    if not m:
        raise ValueError(f"Unrecognised vertex token: {token!r}")
    sign, has_x, num_str, k_str = m.groups()

    value = 0.0
    if has_x:
        x_sign = -1.0 if sign == "-" else 1.0
        value += x_sign * x
        if num_str:
            value += float(num_str)
    else:
        num = float(num_str) if num_str else 0.0
        if sign == "-":
            num = -num
        value += num

    if k_str:
        if k_str == "+k":
            value += k
        elif k_str == "-k":
            value -= k

    return value


def _stab_offset(key_units: float) -> float:
    """Return the stabiliser centre offset for *key_units*.

    Replicates kb_builder's ``stab_size`` string formatting and ``stabs``
    lookup (``lib/builder.py:500-504``).
    """
    s = str(key_units).replace(".", "")
    if key_units < 10:
        s = s.ljust(3, "0")
    else:
        s = s.ljust(4, "0")
    return _CENTER_OFFSETS.get(s, _DEFAULT_OFFSET)


def resolve_stabilizer_family(
    type_ref: str | None,
    default: str = "cherry",
) -> str:
    """Resolve a per-key stabiliser type reference to a registered family name.

    *type_ref* can be a family name (``"cherry"``) or an integer-code string
    (``"0"``, ``"1"``).  Per-key codes are restricted to ``{0, 1}`` mirroring
    kb_builder's ``range(2)`` check (``lib/builder.py:362``); code ``"2"`` and
    unrecognised values fall back to *default*.
    """
    if type_ref is None:
        return default
    if type_ref in _FAMILY_TO_ENTRY:
        return type_ref
    try:
        code = int(type_ref)
    except (ValueError, TypeError):
        return default
    if code not in (0, 1):
        return default
    return _CODE_TO_FAMILY.get(code, default)


class _KbBuilderStabilizer:
    """Base for all kb_builder stabiliser types."""

    def __init__(self, family: str) -> None:
        self._entry = _FAMILY_TO_ENTRY[family]

    def cutout_polygons(
        self,
        key_units: float,
        kerf: float = 0.0,
    ) -> list[list[tuple[float, float]]]:
        """Return cutout polygon(s) for a key of *key_units*.

        Returns one polygon for combined types (cherry, costar_compat) or two
        for costar (twin slots).  Each polygon is centred on the switch centre.
        """
        if 2.0 <= key_units < 3.0:
            template = self._entry["polygons_2u"]
        else:
            x = _stab_offset(key_units)
            template = self._entry["polygons_spacebar"]

        result: list[list[tuple[float, float]]] = []
        for poly in template:
            resolved = [
                (_resolve_vertex(t[0], x if "x" in str(t) else 0.0, kerf),
                 _resolve_vertex(t[1], x if "x" in str(t) else 0.0, kerf))
                for t in poly
            ]
            result.append(resolved)
        return result

    def metadata(self) -> dict[str, Any]:
        return {
            "family": self._entry["name"],
            "kb_builder_type": self._entry["code"],
        }


@register_stabilizer("cherry")
class CherryStabilizer(_KbBuilderStabilizer):
    def __init__(self) -> None:
        super().__init__("cherry")


@register_stabilizer("costar_compat")
class CostarCompatStabilizer(_KbBuilderStabilizer):
    def __init__(self) -> None:
        super().__init__("costar_compat")


@register_stabilizer("costar")
class CostarStabilizer(_KbBuilderStabilizer):
    def __init__(self) -> None:
        super().__init__("costar")
