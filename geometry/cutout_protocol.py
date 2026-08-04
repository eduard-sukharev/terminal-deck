"""Structural protocols for switch and stabilizer cutout shape providers.

A cutout provider is any frozen dataclass with a ``vertices`` property that
returns the closed polygon centered on origin. No base class is required —
structural typing means "if it quacks like a cutout, it is one."

This lets third parties add new cutout types by writing a plain dataclass
and registering it, without importing any base class from the core library.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from collections.abc import Sequence


class SwitchCutoutProtocol(Protocol):
    """A switch cutout shape provider.

    A frozen dataclass whose ``vertices`` property returns the closed polygon
    centered on origin. The spec is structurally typed — anything with a
    ``vertices`` property works; no base class required.
    """

    @property
    def vertices(self) -> Sequence[tuple[float, float]]:
        """Polygon vertices in draw order (closed polyline), centered on (0,0)."""
        ...


class StabilizerCutoutProtocol(Protocol):
    """A stabilizer cutout shape provider.

    Same contract as :class:`SwitchCutoutProtocol`. The two protocols are
    separate so stabilizers can gain type-specific members (e.g. a
    ``build_override`` for non-polyline shapes) without affecting switches.
    """

    @property
    def vertices(self) -> Sequence[tuple[float, float]]:
        ...
