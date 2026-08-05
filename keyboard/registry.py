"""Switch and stabilizer type registry — plugin system for cutout shapes.

A third party adds a new type by::

    1. Writing a class that satisfies the Switch or Stabilizer protocol.
    2. Decorating it with ``@register_switch("name")`` or
       ``@register_stabilizer("name")``.
    3. Importing their module before calling ``keyboard.generate()``.

No core library files need to be modified.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from collections.abc import Sequence


class SwitchProtocol(Protocol):
    """A switch family providing cutout geometry and metadata."""

    def cutout_vertices(self) -> Sequence[tuple[float, float]]:
        """Polygon vertices of the plate cutout, centered on origin."""

    def plate_tolerance(self) -> float:
        """Recommended plate cutout tolerance (mm)."""

    def plate_thickness(self) -> float:
        """Nominal plate thickness for this switch (mm)."""

    def switch_center(self) -> tuple[float, float]:
        """(x, y) offset of the switch electrical center from the cutout center."""

    def metadata(self) -> dict[str, Any]:
        """Arbitrary metadata dict."""


class KeycapProtocol(Protocol):
    """A keycap profile providing dimensions and metadata."""

    def base_size(self) -> float:
        """Bottom square side for a 1u key (mm)."""

    def top_diameter(self) -> float:
        """Top circle diameter for a 1u key (mm); corner_radius = top_diameter / 2."""

    def height(self) -> float:
        """Cap height from base to top (mm)."""

    def segments(self) -> int:
        """Number of sample points per wire for lofting."""

    def metadata(self) -> dict[str, Any]:
        """Arbitrary metadata dict."""


class StabilizerProtocol(Protocol):
    """A stabilizer family providing cutout polygon(s) for a key width."""

    def cutout_polygons(
        self,
        key_units: float,
        kerf: float = 0.0,
    ) -> Sequence[Sequence[tuple[float, float]]]:
        """Cutout polygon(s) for a key of *key_units*, centred on the switch centre.

        Returns one polygon for combined types (cherry, costar_compat) or two
        for costar (twin slots).  *kerf* is the per-edge outward offset
        (``_k/2`` in kb_builder terms).
        """

    def metadata(self) -> dict[str, Any]:
        """Arbitrary metadata dict."""


_SWITCH: dict[str, type] = {}
_STABILIZER: dict[str, type] = {}
_KEYCAP: dict[str, type] = {}


def register_switch(name: str):
    """Decorator: register a switch class under *name*."""
    def decorator(cls):
        _SWITCH[name] = cls
        cls._registry_name = name
        return cls
    return decorator


def register_stabilizer(name: str):
    """Decorator: register a stabilizer class under *name*."""
    def decorator(cls):
        _STABILIZER[name] = cls
        cls._registry_name = name
        return cls
    return decorator


def get_switch(name: str) -> type:
    """Return the switch class for *name*.

    Raises ``ValueError`` with registered types if not found.
    """
    try:
        return _SWITCH[name]
    except KeyError:
        registered = ", ".join(sorted(_SWITCH))
        raise ValueError(
            f"Unknown switch type {name!r}. Registered: {registered}"
        ) from None


def get_stabilizer(name: str) -> type:
    """Return the stabilizer class for *name*."""
    try:
        return _STABILIZER[name]
    except KeyError:
        registered = ", ".join(sorted(_STABILIZER))
        raise ValueError(
            f"Unknown stabilizer type {name!r}. Registered: {registered}"
        ) from None


def registered_switches() -> frozenset[str]:
    return frozenset(_SWITCH)


def registered_stabilizers() -> frozenset[str]:
    return frozenset(_STABILIZER)


def register_keycap(name: str):
    """Decorator: register a keycap profile class under *name*."""
    def decorator(cls):
        _KEYCAP[name] = cls
        cls._registry_name = name
        return cls
    return decorator


def get_keycap(name: str) -> type:
    """Return the keycap profile class for *name*.

    Raises ``ValueError`` with registered profiles if not found.
    """
    try:
        return _KEYCAP[name]
    except KeyError:
        registered = ", ".join(sorted(_KEYCAP))
        raise ValueError(
            f"Unknown keycap profile {name!r}. Registered: {registered}"
        ) from None


def registered_keycaps() -> frozenset[str]:
    return frozenset(_KEYCAP)
