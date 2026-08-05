"""YAML recipe loader: loads constraint recipes from YAML files.

Each recipe file contains a list of constraints under a ``constraints`` key.
Values are pre-computed (no expression evaluation). Component size references
like ``{keyboard.depth}`` are resolved at load time from the component specs.

Example ``config/layouts/default.yaml``::

    constraints:
      - kind: fixed_position
        subject: keyboard
        y: 35.0
      - kind: centered_on
        subject: keyboard
        axes: ["x"]
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from layouts.constraints import (
    CablePath,
    CenteredGroup,
    CenteredOn,
    Clearance,
    Constraint,
    ConstraintPriority,
    EdgeAlignment,
    FixedPosition,
    FootprintMatch,
    RegionConstraint,
    RelativePlacement,
    SharePlane,
    TargetEnvelope,
    ZStack,
)

# Map YAML kind strings to Constraint dataclasses.
_CONSTRAINT_KINDS: dict[str, type[Constraint]] = {
    "cable_path": CablePath,
    "centered_group": CenteredGroup,
    "centered_on": CenteredOn,
    "clearance": Clearance,
    "edge_alignment": EdgeAlignment,
    "fixed_position": FixedPosition,
    "footprint_match": FootprintMatch,
    "region": RegionConstraint,
    "relative_placement": RelativePlacement,
    "share_plane": SharePlane,
    "target_envelope": TargetEnvelope,
    "z_stack": ZStack,
}

# Fields that should be converted from list to tuple.
_TUPLE_FIELDS: frozenset[str] = frozenset({
    "axes",
    "subjects",
    "via_point",
})

# Fields that should be converted from string to ConstraintPriority.
_PRIORITY_FIELDS: frozenset[str] = frozenset({"priority"})

_REF_PATTERN = re.compile(r"\{([^}]+)\}")


def _resolve_refs(value: Any, components: dict[str, Any], config: Any) -> Any:
    """Resolve ``{component.field}`` and ``{config.path}`` references in a value.

    Supports:
    * ``{keyboard.depth}`` → ``components["keyboard"].size().depth``
    * ``{sbc.width}`` → ``components["sbc"].size().width``
    * ``{config.wall_thickness}`` → ``config.wall_thickness``
    * ``{config.clearance.shell}`` → ``config.clearance.shell``
    """
    if not isinstance(value, str):
        return value

    def _resolve_one(match: re.Match) -> str:
        path = match.group(1)
        parts = path.split(".")
        if parts[0] == "config":
            obj: Any = config
            for attr in parts[1:]:
                obj = getattr(obj, attr, None)
                if obj is None:
                    raise ValueError(f"Unknown config path: {path}")
            return str(obj)
        else:
            comp_name = parts[0]
            comp = components.get(comp_name)
            if comp is None:
                raise ValueError(f"Unknown component: {comp_name}")
            if len(parts) == 2 and parts[1] in ("width", "depth", "height"):
                box = comp.size()
                return str(getattr(box, parts[1]))
            raise ValueError(f"Unknown component reference: {path}")

    resolved = _REF_PATTERN.sub(_resolve_one, value)
    # Coerce numeric strings back to float/int.
    try:
        return int(resolved)
    except ValueError:
        try:
            return float(resolved)
        except ValueError:
            return resolved


def _coerce_value(value: Any, field_name: str) -> Any:
    """Coerce a YAML value to the type expected by the constraint dataclass."""
    if field_name in _TUPLE_FIELDS and isinstance(value, list):
        return tuple(value)
    if field_name in _PRIORITY_FIELDS and isinstance(value, str):
        return ConstraintPriority[value.upper()]
    return value


def load_recipe(
    path: str | Path,
    components: dict[str, Any] | None = None,
    config: Any = None,
) -> list[Constraint]:
    """Load a YAML recipe file and return a list of Constraint objects.

    Parameters
    ----------
    path : str or Path
        Path to the YAML recipe file.
    components : dict or None
        Components keyed by name (needed for ``{component.field}`` refs).
    config : Config or None
        Resolved build configuration (needed for ``{config.path}`` refs).

    Returns
    -------
    list[Constraint]
        The resolved constraint objects.
    """
    path = Path(path)
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    components = components or {}
    raw_list = data.get("constraints", [])
    if not isinstance(raw_list, list):
        raise ValueError(f"Expected a list under 'constraints' key in {path}")

    constraints: list[Constraint] = []
    for item in raw_list:
        if not isinstance(item, dict):
            raise ValueError(f"Each constraint must be a dict, got {type(item).__name__}")

        kind = item.get("kind")
        if not kind:
            raise ValueError(f"Constraint missing 'kind' field: {item}")

        cls = _CONSTRAINT_KINDS.get(kind)
        if cls is None:
            raise ValueError(f"Unknown constraint kind: {kind!r}")

        params = dict(item)
        del params["kind"]

        # Resolve component/config references.
        for key, value in params.items():
            params[key] = _resolve_refs(value, components, config)

        # Coerce types (list → tuple, string → enum).
        for key, value in params.items():
            params[key] = _coerce_value(value, key)

        constraints.append(cls(**params))

    return constraints


__all__ = ["load_recipe"]
