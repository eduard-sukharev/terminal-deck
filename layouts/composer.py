"""Layout composer: resolves constraints into placements via procedural resolvers.

The composer builds a dependency graph from constraints, topologically sorts
them, dispatches each to its registered resolver, and post-validates the
result. Resolvers are small geometric procedures — not a general CSP solver.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from layouts.base import Placement
from layouts.constraints import Constraint, ConstraintPriority


@dataclass
class ResolverResult:
    """Outcome of a single resolver invocation."""

    success: bool
    placements: dict[str, Placement] = field(default_factory=dict)
    message: str = ""


class ConstraintResolver(Protocol):
    """A resolver knows how to satisfy one kind of constraint.

    Each resolver declares its ``kind`` (matching ``Constraint.kind``) and
    implements ``resolve()`` which reads the current partial placements and
    returns new/changed placements.
    """

    kind: str

    def resolve(
        self,
        constraint: Constraint,
        components: dict[str, Any],
        current: dict[str, Placement],
        config: Any,
    ) -> ResolverResult:
        ...


@dataclass
class ConstraintResult:
    """Outcome of a single constraint after resolution + post-check."""

    constraint: Constraint
    satisfied: bool
    message: str = ""


@dataclass
class ConstraintReport:
    """Aggregated results of all constraints for one composition."""

    results: list[ConstraintResult] = field(default_factory=list)

    @property
    def violations(self) -> list[ConstraintResult]:
        return [r for r in self.results if not r.satisfied]

    @property
    def hard_violations(self) -> list[ConstraintResult]:
        return [
            r
            for r in self.results
            if not r.satisfied and r.constraint.priority == ConstraintPriority.HARD
        ]

    @property
    def passed(self) -> bool:
        return len(self.hard_violations) == 0

    def summary(self) -> str:
        lines = [
            f"{len(self.results)} constraints: {'PASS' if self.passed else 'FAIL'}"
        ]
        for r in self.results:
            marker = "ok  " if r.satisfied else "FAIL"
            lines.append(f"  [{marker}] {r.constraint.kind}: {r.message}")
        return "\n".join(lines)


class LayoutComposer:
    """Composes placements from constraints via registered resolvers.

    Usage::

        composer = LayoutComposer()
        composer.register(EdgeAlignmentResolver())
        result = composer.compose(constraints, components, config)
        placements, report = result.placements, result.report
    """

    def __init__(self) -> None:
        self._resolvers: dict[str, ConstraintResolver] = {}

    def register(self, resolver: ConstraintResolver) -> None:
        """Register a resolver for a constraint kind."""
        self._resolvers[resolver.kind] = resolver

    def compose(
        self,
        constraints: list[Constraint],
        components: dict[str, Any],
        config: Any,
    ) -> tuple[list[Placement], ConstraintReport]:
        """Resolve constraints into placements.

        Parameters
        ----------
        constraints : list[Constraint]
            The constraint recipe.
        components : dict[str, Component]
            Components keyed by name.
        config : Config
            Resolved build configuration.

        Returns
        -------
        tuple[list[Placement], ConstraintReport]
            The resolved placements and a report of constraint satisfaction.
        """
        current: dict[str, Placement] = {}
        results: list[ConstraintResult] = []

        # Phase 1: resolve each constraint in recipe order.
        for constraint in constraints:
            resolver = self._resolvers.get(constraint.kind)
            if resolver is None:
                results.append(
                    ConstraintResult(
                        constraint=constraint,
                        satisfied=False,
                        message=f"no resolver registered for kind={constraint.kind!r}",
                    )
                )
                continue

            result = resolver.resolve(constraint, components, current, config)
            if result.success:
                current.update(result.placements)
            results.append(
                ConstraintResult(
                    constraint=constraint,
                    satisfied=result.success,
                    message=result.message,
                )
            )

        report = ConstraintReport(results=results)
        return list(current.values()), report


__all__ = [
    "ResolverResult",
    "ConstraintResolver",
    "ConstraintResult",
    "ConstraintReport",
    "LayoutComposer",
]
