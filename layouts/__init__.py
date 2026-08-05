"""Layout definitions. Layouts contain no CAD — only placements."""

from layouts.base import Layout, Placement
from pathlib import Path

from layouts.layout_compact import LayoutCompact
from layouts.layout_compact_v2 import LayoutCompactV2
from layouts.layout_constrained import ConstraintLayout
from layouts.layout_default import LayoutDefault
from layouts.layout_default_v2 import LayoutDefaultV2
from layouts.layout_recipe import RecipeLayout

LAYOUTS = {
    "default": LayoutDefault,
    "default_v2": LayoutDefaultV2,
    "compact": LayoutCompact,
    "compact_v2": LayoutCompactV2,
    "constrained": ConstraintLayout,
}

# Built-in recipe paths (relative to config/layouts/).
_RECIPE_DIR = Path(__file__).resolve().parent.parent / "config" / "layouts"
_RECIPE_LAYOUTS: dict[str, Path] = {
    "recipe_default": _RECIPE_DIR / "default.yaml",
    "recipe_compact": _RECIPE_DIR / "compact.yaml",
}


def make_layout(
    name: str,
    components: dict | None = None,
    config=None,
    recipe_path: str | Path | None = None,
) -> Layout:
    """Instantiate a layout by name.

    Parameters
    ----------
    name : str
        Layout name (``"default"``, ``"compact"``, ``"constrained"``, or
        ``"recipe_default"`` / ``"recipe_compact"``).
    components : dict or None
        Components keyed by role.
    config : Config or None
        Resolved build configuration (needed by constraint-based layouts).
    recipe_path : str or Path or None
        Override recipe path for ``RecipeLayout`` (overrides built-in).
    """
    # Check built-in recipe layouts first.
    if name in _RECIPE_LAYOUTS:
        rp = recipe_path or _RECIPE_LAYOUTS[name]
        return RecipeLayout(components or {}, config=config, recipe_path=rp)

    try:
        layout_cls = LAYOUTS[name]
    except KeyError as exc:
        raise ValueError(f"Unknown layout: {name!r}") from exc
    if config is not None and issubclass(layout_cls, ConstraintLayout):
        return layout_cls(components or {}, config=config)
    return layout_cls(components or {})


__all__ = [
    "Layout",
    "Placement",
    "LayoutCompact",
    "ConstraintLayout",
    "LayoutDefault",
    "LAYOUTS",
    "make_layout",
]
