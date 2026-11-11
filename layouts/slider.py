"""The slider layout: the clamshell's successor (ADR-0009).

The placement recipe itself works in the chassis-centred frame (the keyboard's
Y includes the chassis half-height), so this class only binds the recipe. X is
symmetric because the enclosure hint is symmetric and the rear-band pair is
centred on the keyboard.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from layouts.layout_recipe import RecipeLayout

#: The built-in slider recipe.
SLIDER_RECIPE = (
    Path(__file__).resolve().parent.parent / "config" / "layouts" / "slider.yaml"
)


class SliderLayout(RecipeLayout):
    """Recipe layout for the slider."""

    name = "slider"

    def __init__(
        self,
        components: dict[str, Any] | None = None,
        config: Any = None,
        recipe_path: str | Path | None = None,
    ) -> None:
        # The recipe's envelope is the budget's, not a restatement of the
        # mechanism formulas: the chassis depth is whatever the closed face
        # requires (the lid is the larger half), so the recipe asks the
        # budget for it instead of duplicating the derivation in YAML.
        from components.slide import compute_slide_budget

        budget = (
            compute_slide_budget(config, components)
            if config is not None and components
            else None
        )
        super().__init__(
            components or {},
            config=config,
            recipe_path=recipe_path or SLIDER_RECIPE,
            budget=budget,
        )


__all__ = ["SLIDER_RECIPE", "SliderLayout"]
