"""Display-only color palette for glTF rendering.

Not a build parameter: colors affect only how the exported ``.gltf`` looks
in a viewer, never geometry. Keyed by component role (the key used in
``BuildPipeline.load_components()``) or by a sub-assembly name (e.g.
``"case"`` for the base/lid shell). Unknown roles fall back to
``DEFAULT_COLOR`` rather than erroring, so a new component never breaks a
glTF export.
"""

from __future__ import annotations

#: RGBA, each channel 0.0-1.0.
Color = tuple[float, float, float, float]

COMPONENT_COLORS: dict[str, Color] = {
    "display": (0.16, 0.42, 0.75, 1.0),      # blue
    "driver": (0.93, 0.60, 0.13, 1.0),       # orange
    "keyboard": (0.18, 0.18, 0.20, 1.0),     # near-black plate
    "sbc": (0.16, 0.66, 0.33, 1.0),          # green
    "battery": (0.82, 0.20, 0.20, 1.0),      # red
    "usb_breakout": (0.58, 0.29, 0.78, 1.0), # purple
    "hinge": (0.55, 0.55, 0.58, 1.0),        # steel grey
    "case": (0.72, 0.73, 0.76, 0.55),        # translucent shell grey
}

DEFAULT_COLOR: Color = (0.6, 0.6, 0.6, 1.0)


def color_for(role: str) -> Color:
    """RGBA color for a component role or sub-assembly name."""
    return COMPONENT_COLORS.get(role, DEFAULT_COLOR)


__all__ = ["Color", "COMPONENT_COLORS", "DEFAULT_COLOR", "color_for"]
