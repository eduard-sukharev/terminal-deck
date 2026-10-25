"""Display-only color palette for glTF rendering.

Every component gets its own opaque color so parts are easy to tell apart in
a viewer; only the case shell (``"case"``) is translucent, so the components
inside stay visible. Give any new component its own entry here — a test
fails if one is missing or shares a color.

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
    "controller": (0.10, 0.62, 0.62, 1.0),   # teal
    "sbc_plug": (0.95, 0.85, 0.20, 1.0),     # yellow
    "hdmi_plug_sbc": (0.90, 0.35, 0.65, 1.0),     # pink
    "hdmi_plug_driver": (0.45, 0.85, 0.90, 1.0),  # light cyan
    "hinge": (0.55, 0.55, 0.58, 1.0),        # steel grey
    "base_knuckle": (0.95, 0.55, 0.20, 1.0), # orange: the separate Base knuckle
    "end_cheek": (0.85, 0.35, 0.15, 1.0),    # darker orange: the end cheeks (fused to the Deck)
    "lid_knuckle": (0.30, 0.55, 0.85, 1.0),  # blue: Lid knuckles fused to the Lid shell
    "hinge_hardware": (0.80, 0.80, 0.82, 1.0),  # bolts, nuts, washers, service caps
    "section_left": (0.62, 0.78, 0.92, 1.0),    # printed Sections, one color each so
    "section_center": (0.95, 0.80, 0.55, 1.0),  # the Seams read in a review render
    "section_right": (0.70, 0.88, 0.66, 1.0),
    "case": (0.72, 0.73, 0.76, 0.55),        # translucent shell grey
}

DEFAULT_COLOR: Color = (0.6, 0.6, 0.6, 1.0)


def color_for(role: str) -> Color:
    """RGBA color for a component role or sub-assembly name."""
    return COMPONENT_COLORS.get(role, DEFAULT_COLOR)


__all__ = ["Color", "COMPONENT_COLORS", "DEFAULT_COLOR", "color_for"]
