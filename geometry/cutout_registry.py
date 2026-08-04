"""Cutout type registry — plugin system for switch and stabilizer cutout shapes.

A third party adds a new cutout type by::

    1. Writing a frozen dataclass with a ``vertices`` property.
    2. Decorating it with ``@register_switch_cutout("name")`` or
       ``@register_stabilizer_cutout("name")``.
    3. Importing their module before the pipeline runs.

No core library files need to be modified.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from geometry.cutout_protocol import (
        StabilizerCutoutProtocol,
        SwitchCutoutProtocol,
    )

#: Registered switch cutout spec classes, keyed by type name.
_SWITCH: dict[str, type[SwitchCutoutProtocol]] = {}

#: Registered stabilizer cutout spec classes, keyed by type name.
_STABILIZER: dict[str, type[StabilizerCutoutProtocol]] = {}


def register_switch_cutout(name: str):
    """Decorator: register a switch cutout spec class under ``name``.

    The decorated class must satisfy :class:`SwitchCutoutProtocol` (a frozen
    dataclass with a ``vertices`` property).

    Example::

        @register_switch_cutout("mx")
        @dataclass(frozen=True)
        class MxCutout:
            @property
            def vertices(self):
                ...
    """
    def decorator(cls):
        _SWITCH[name] = cls
        cls._cutout_name = name
        return cls
    return decorator


def register_stabilizer_cutout(name: str):
    """Decorator: register a stabilizer cutout spec class under ``name``."""
    def decorator(cls):
        _STABILIZER[name] = cls
        cls._cutout_name = name
        return cls
    return decorator


def get_switch_cutout(name: str) -> type[SwitchCutoutProtocol]:
    """Return the switch cutout spec class for *name*.

    Raises ``ValueError`` with a list of registered types if not found.
    """
    try:
        return _SWITCH[name]
    except KeyError:
        registered = ", ".join(sorted(_SWITCH))
        raise ValueError(
            f"Unknown switch cutout type {name!r}. "
            f"Registered types: {registered}"
        ) from None


def get_stabilizer_cutout(name: str) -> type[StabilizerCutoutProtocol]:
    """Return the stabilizer cutout spec class for *name*."""
    try:
        return _STABILIZER[name]
    except KeyError:
        registered = ", ".join(sorted(_STABILIZER))
        raise ValueError(
            f"Unknown stabilizer cutout type {name!r}. "
            f"Registered types: {registered}"
        ) from None


def registered_switch_cutouts() -> frozenset[str]:
    """Return the set of registered switch cutout type names."""
    return frozenset(_SWITCH)


def registered_stabilizer_cutouts() -> frozenset[str]:
    """Return the set of registered stabilizer cutout type names."""
    return frozenset(_STABILIZER)
