"""Recipe-based layout: a ConstraintLayout driven by a YAML recipe file.

``RecipeLayout`` loads constraints from a YAML file instead of Python code.
This lets non-Python users define layouts without writing code.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from layouts.layout_constrained import ConstraintLayout
from layouts.recipe_loader import load_recipe


class RecipeLayout(ConstraintLayout):
    """A constraint-based layout loaded from a YAML recipe file.

    The recipe file contains a ``constraints`` list. Each entry has a
    ``kind`` field matching a constraint type and the relevant parameters.

    Example ``config/layouts/my_layout.yaml``::

        constraints:
          - kind: fixed_position
            subject: keyboard
            y: 35.0
          - kind: centered_on
            subject: keyboard
            axes: ["x"]
    """

    name: str = "recipe"

    def __init__(
        self,
        components: dict[str, Any] | None = None,
        config: Any = None,
        recipe_path: str | Path | None = None,
    ) -> None:
        super().__init__(components, config)
        self._recipe_path = Path(recipe_path) if recipe_path else None

    def _build_constraints(self):
        if self._recipe_path is None:
            return []
        return load_recipe(self._recipe_path, self.components, self._config)


__all__ = ["RecipeLayout"]
