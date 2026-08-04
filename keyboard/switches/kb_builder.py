"""kb_builder switch types — 5 cutout shapes transcribed from swill/kb_builder.

Each type is registered as a separate :class:`SwitchProtocol` family so the
registry can look it up by name.  A per-key ``_t`` integer code (0-4) in the
KLE JSON selects the cutout shape, falling back to the config default family.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from keyboard.registry import register_switch

_REFERENCE = Path(__file__).resolve().parent.parent / "reference" / "switch_cutouts.yaml"

with open(_REFERENCE, "r") as _f:
    _DATA = yaml.safe_load(_f)

# Build lookup tables from the reference data.
_CODE_TO_FAMILY: dict[int, str] = {}
_FAMILY_TO_ENTRY: dict[str, dict[str, Any]] = {}
for entry in _DATA["types"]:
    name: str = entry["name"]
    code: int = entry["code"]
    _CODE_TO_FAMILY[code] = name
    _FAMILY_TO_ENTRY[name] = entry


def resolve_switch_family(
    type_ref: str | None,
    default: str = "mx_alps",
) -> str:
    """Resolve a per-key switch type reference to a registered family name.

    *type_ref* can be a family name (``"mx_alps"``) or an integer-code string
    (``"1"``).  If *type_ref* is ``None`` or unrecognised, *default* is
    returned (matching kb_builder's silent fallback when ``_t`` is absent or
    out of range).
    """
    if type_ref is None:
        return default
    if type_ref in _FAMILY_TO_ENTRY:
        return type_ref
    try:
        code = int(type_ref)
    except (ValueError, TypeError):
        return default
    return _CODE_TO_FAMILY.get(code, default)


class _KbBuilderSwitch:
    """Base for all kb_builder switch types — loads geometry from the reference YAML."""

    def __init__(self, family: str) -> None:
        entry = _FAMILY_TO_ENTRY[family]
        self._entry = entry
        self._vertices = [tuple(v) for v in entry["vertices"]]

    def cutout_vertices(self) -> list[tuple[float, float]]:
        return list(self._vertices)

    def plate_tolerance(self) -> float:
        return self._entry.get("recommended_clearance", 0.05)

    def plate_thickness(self) -> float:
        return self._entry.get("nominal_thickness", 1.6)

    def switch_center(self) -> tuple[float, float]:
        return (0.0, 0.0)

    def metadata(self) -> dict[str, Any]:
        return {
            "family": self._entry["name"],
            "kb_builder_type": self._entry["code"],
            "width": self._entry["width"],
            "height": self._entry["height"],
        }


@register_switch("square")
class SquareSwitch(_KbBuilderSwitch):
    def __init__(self) -> None:
        super().__init__("square")


@register_switch("mx_alps")
class MxAlpsSwitch(_KbBuilderSwitch):
    def __init__(self) -> None:
        super().__init__("mx_alps")


@register_switch("mx_wings")
class MxWingsSwitch(_KbBuilderSwitch):
    def __init__(self) -> None:
        super().__init__("mx_wings")


@register_switch("mx_rotatable")
class MxRotatableSwitch(_KbBuilderSwitch):
    def __init__(self) -> None:
        super().__init__("mx_rotatable")


@register_switch("alps_only")
class AlpsOnlySwitch(_KbBuilderSwitch):
    def __init__(self) -> None:
        super().__init__("alps_only")
