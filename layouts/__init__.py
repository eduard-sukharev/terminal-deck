"""Layout definitions. Layouts contain no CAD — only placements."""

from layouts.base import Layout, Placement
from layouts.layout_compact import LayoutCompact
from layouts.layout_default import LayoutDefault

LAYOUTS = {
    "default": LayoutDefault,
    "compact": LayoutCompact,
}


def make_layout(name: str, components: dict | None = None) -> Layout:
    """Instantiate a layout by name (``"default"`` or ``"compact"``)."""
    try:
        layout_cls = LAYOUTS[name]
    except KeyError as exc:
        raise ValueError(f"Unknown layout: {name!r}") from exc
    return layout_cls(components or {})


__all__ = [
    "Layout",
    "Placement",
    "LayoutCompact",
    "LayoutDefault",
    "LAYOUTS",
    "make_layout",
]
