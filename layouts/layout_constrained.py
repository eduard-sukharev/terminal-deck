"""Constraint-based layout: a Layout subclass driven by declarative constraints.

``ConstraintLayout`` subclasses ``Layout`` and replaces ``_build_placements``
with a ``LayoutComposer`` invocation. Subclasses override ``_build_constraints``
to define the constraint recipe.
"""

from __future__ import annotations

from typing import Any

from layouts.base import Layout, Placement
from layouts.composer import ConstraintReport, LayoutComposer
from layouts.constraints import Constraint
from layouts.resolvers import default_resolver_registry


class ConstraintLayout(Layout):
    """A layout expressed as constraints + resolvers.

    Subclasses override :meth:`_build_constraints` to return the constraint
    recipe. The composer resolves them into placements.

    After :meth:`placements` is called, :meth:`constraint_report` returns the
    resolution report.

    Example::

        class MyLayout(ConstraintLayout):
            name = "my_layout"

            def _build_constraints(self) -> list[Constraint]:
                return [
                    EdgeAlignment("keyboard", "front", "enclosure", "front", offset=20.0),
                    CenteredOn("keyboard", axes=("x",)),
                ]
    """

    name: str = "constrained"

    def __init__(
        self,
        components: dict[str, Any] | None = None,
        config: Any = None,
    ) -> None:
        super().__init__(components)
        self._config = config
        self._composer = LayoutComposer()
        self._constraint_report: ConstraintReport | None = None
        for kind, resolver in default_resolver_registry().items():
            self._composer.register(resolver)

    def _build_constraints(self) -> list[Constraint]:
        """Return the constraint recipe for this layout.

        Override in subclasses. Default: empty (no placements).
        """
        return []

    def constraint_report(self) -> ConstraintReport | None:
        """Return the constraint resolution report, or None if not yet resolved."""
        return self._constraint_report

    def _build_placements(self, placements: list[Placement]) -> None:
        constraints = self._build_constraints()
        resolved, report = self._composer.compose(
            constraints, self.components, self._config
        )
        self._constraint_report = report
        placements.clear()
        placements.extend(resolved)


__all__ = ["ConstraintLayout"]
