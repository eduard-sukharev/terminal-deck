"""Layout definitions. Layouts contain no CAD — only placements.

There is exactly one layout: ``compact``, the clamshell arrangement declared
as constraints in ``config/layouts/clamshell.yaml`` and resolved by
``LayoutComposer``. Pass ``--layout-recipe <path>`` to run a different recipe
file through the same machinery.
"""

from pathlib import Path

from layouts.base import Layout, Placement
from layouts.layout_constrained import ConstraintLayout
from layouts.layout_recipe import RecipeLayout

#: The built-in recipe: the compact clamshell.
RECIPE = Path(__file__).resolve().parent.parent / "config" / "layouts" / "clamshell.yaml"

#: Accepted ``--layout`` values.
LAYOUTS = ("compact",)


def make_layout(
    name: str = "compact",
    components: dict | None = None,
    config=None,
    recipe_path: str | Path | None = None,
) -> Layout:
    """Instantiate the layout by name.

    Parameters
    ----------
    name : str
        Layout name. Only ``"compact"`` is defined.
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
    return RecipeLayout(
        components or {}, config=config, recipe_path=recipe_path or RECIPE
    )


__all__ = [
    "Layout",
    "Placement",
    "ConstraintLayout",
    "RecipeLayout",
    "LAYOUTS",
    "RECIPE",
    "make_layout",
]
