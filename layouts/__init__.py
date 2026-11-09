"""Layout definitions. Layouts contain no CAD — only placements.

``compact`` is the retired clamshell arrangement (kept while the slider's CAD
path is being built); ``slider`` is the target form (ADR-0009), declared as
constraints in ``config/layouts/slider.yaml``. Pass ``--layout-recipe <path>``
to run a different recipe file through the same machinery.
"""

from pathlib import Path

from layouts.base import Layout, Placement
from layouts.layout_constrained import ConstraintLayout
from layouts.layout_recipe import RecipeLayout
from layouts.slider import SLIDER_RECIPE, SliderLayout

#: The built-in clamshell recipe (retired with the clamshell, ADR-0009).
RECIPE = Path(__file__).resolve().parent.parent / "config" / "layouts" / "clamshell.yaml"

#: Accepted ``--layout`` values.
LAYOUTS = ("compact", "slider")


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
        Layout name: ``"compact"`` (clamshell, retired) or ``"slider"``.
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
    if name == "slider":
        return SliderLayout(
            components or {},
            config=config,
            recipe_path=recipe_path or SLIDER_RECIPE,
        )
    return RecipeLayout(
        components or {}, config=config, recipe_path=recipe_path or RECIPE
    )


__all__ = [
    "Layout",
    "Placement",
    "ConstraintLayout",
    "RecipeLayout",
    "SliderLayout",
    "LAYOUTS",
    "RECIPE",
    "SLIDER_RECIPE",
    "make_layout",
]
