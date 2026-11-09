"""Layout definitions. Layouts contain no CAD — only placements.

``slider`` is the only layout (ADR-0009), declared as constraints in
``config/layouts/slider.yaml`` and resolved by ``LayoutComposer``. Pass
``--layout-recipe <path>`` to run a different recipe file through the same
machinery.
"""

from pathlib import Path

from layouts.base import Layout, Placement
from layouts.layout_constrained import ConstraintLayout
from layouts.layout_recipe import RecipeLayout
from layouts.slider import SLIDER_RECIPE, SliderLayout

#: Accepted ``--layout`` values.
LAYOUTS = ("slider",)


def make_layout(
    name: str = "slider",
    components: dict | None = None,
    config=None,
    recipe_path: str | Path | None = None,
) -> Layout:
    """Instantiate the layout by name.

    Parameters
    ----------
    name : str
        Layout name: only ``"slider"``.
    components : dict or None
        Components keyed by role.
    config : Config or None
        Resolved build configuration (the composer evaluates recipe
        expressions against it).
    recipe_path : str or Path or None
        Recipe file to use instead of the built-in one.
    """
    if name not in LAYOUTS:
        raise ValueError(f"Unknown layout: {name!r} (expected one of {LAYOUTS})")
    return SliderLayout(
        components or {},
        config=config,
        recipe_path=recipe_path or SLIDER_RECIPE,
    )


__all__ = [
    "Layout",
    "Placement",
    "ConstraintLayout",
    "RecipeLayout",
    "SliderLayout",
    "LAYOUTS",
    "SLIDER_RECIPE",
    "make_layout",
]
