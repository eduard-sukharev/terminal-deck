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
    "section_left": (0.62, 0.78, 0.92, 1.0),    # printed Sections, one color each so
    "section_center": (0.95, 0.80, 0.55, 1.0),  # the Seams read in a review render
    "section_right": (0.70, 0.88, 0.66, 1.0),
    "case": (0.72, 0.73, 0.76, 0.55),        # translucent shell grey
    "chassis": (0.55, 0.65, 0.78, 0.55),     # slider chassis (translucent)
    "chassis_tray": (0.50, 0.60, 0.74, 0.50),  # chassis Tray (translucent)
    "chassis_deck": (0.60, 0.71, 0.84, 0.55),  # chassis Deck (translucent)
    "screen_lid": (0.78, 0.72, 0.55, 0.60),  # slider lid (translucent)
    "screen_lid_bezel": (0.78, 0.72, 0.55, 0.55),  # lid display tray (translucent)
    "screen_lid_back": (0.62, 0.58, 0.45, 0.85),   # lid back plate, carries the rods
    "guide_rod": (0.85, 0.86, 0.88, 1.0),    # steel guide rods
    "rod_clamp": (0.18, 0.32, 0.62, 1.0),    # printed rod end clamps (blue)
    "linear_bearing": (0.45, 0.47, 0.50, 1.0),  # LM...LUU bushings
    "bearing_clamp": (0.16, 0.48, 0.24, 1.0),   # printed bearing clamps (green)
    "fpc_guard": (0.86, 0.42, 0.28, 1.0),    # printed FPC grille plate (rust)
    "accessory_rail": (0.38, 0.24, 0.58, 1.0),  # printed accessory rail (violet)
    "rail_washer": (0.92, 0.80, 0.32, 1.0),  # printed washer pucks under the rail
}

DEFAULT_COLOR: Color = (0.6, 0.6, 0.6, 1.0)


def color_for(role: str) -> Color:
    """RGBA color for a component role or sub-assembly name."""
    return COMPONENT_COLORS.get(role, DEFAULT_COLOR)


__all__ = ["Color", "COMPONENT_COLORS", "DEFAULT_COLOR", "color_for"]
