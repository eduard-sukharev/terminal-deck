"""Keyboard geometry generator.

Public API
----------
* :func:`generate` — produce a :class:`KeyboardGeometryModel` from a KLE layout
* :func:`generate_from_file` — load KLE JSON from a file and generate
* :func:`validate` — run validation checks on the generated model
* :func:`parse_layout` — parse KLE JSON into a :class:`KeyboardLayout`
* Registry functions: :func:`register_switch`, :func:`register_stabilizer`,
  :func:`get_switch`, :func:`get_stabilizer`, :func:`registered_switches`,
  :func:`registered_stabilizers`
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from keyboard.geometry.plate import generate as _generate
from keyboard.layout.kle_parser import load_kle, parse_kle
from keyboard.layout.layout import KeyboardLayout
from keyboard.metadata import KeyboardGeometryModel, KeyboardMetadata
from keyboard.registry import (
    get_keycap,
    get_stabilizer,
    get_switch,
    register_keycap,
    register_stabilizer,
    register_switch,
    registered_keycaps,
    registered_stabilizers,
    registered_switches,
)
from keyboard.validation import validate as _validate

# Import built-in switch/stabilizer/keycap modules so their registrations populate.
import keyboard.switches.kb_builder  # noqa: F401
import keyboard.stabilizers.kb_builder  # noqa: F401
import keyboard.keycaps.xda  # noqa: F401


def parse_layout(data: list[list[Any]], pitch: float = 19.05) -> KeyboardLayout:
    """Parse KLE JSON data into a KeyboardLayout.

    Parameters
    ----------
    data : list[list]
        The top-level array from a KLE JSON file.
    pitch : float
        Switch pitch in mm (default 19.05).

    Returns
    -------
    KeyboardLayout
    """
    rows = parse_kle(data)
    keys = [key for row in rows for key in row]
    return KeyboardLayout(keys=keys, pitch=pitch)


def generate(
    layout: KeyboardLayout,
    switch_family: str = "mx_alps",
    stabilizer_family: str = "cherry",
    plate_thickness: float = 1.5,
    edge_margin: float = 8.0,
    corner_radius: float = 8.0,
    screw_diameter: float = 2.0,
    screw_edge_offset: float = 5.0,
) -> KeyboardGeometryModel:
    """Generate the complete keyboard geometry model.

    Parameters
    ----------
    layout : KeyboardLayout
        Parsed keyboard layout.
    switch_family : str
        Default switch family name (default ``"mx_alps"``).
    stabilizer_family : str
        Registered stabilizer family name (default ``"cherry"``).
    plate_thickness : float
        Plate thickness in mm.
    edge_margin : float
        Margin beyond outermost switch centers (mm).
    corner_radius : float
        Plate corner radius (mm).
    screw_diameter : float
        Mounting screw hole diameter (mm).
    screw_edge_offset : float
        Mounting hole inset from plate edge (mm).

    Returns
    -------
    KeyboardGeometryModel
    """
    return _generate(
        layout,
        switch_family=switch_family,
        stabilizer_family=stabilizer_family,
        plate_thickness=plate_thickness,
        edge_margin=edge_margin,
        corner_radius=corner_radius,
        screw_diameter=screw_diameter,
        screw_edge_offset=screw_edge_offset,
    )


def generate_from_file(
    path: str | Path,
    switch_family: str = "mx_alps",
    stabilizer_family: str = "cherry",
    plate_thickness: float = 1.5,
    edge_margin: float = 8.0,
    corner_radius: float = 8.0,
    screw_diameter: float = 2.0,
    screw_edge_offset: float = 5.0,
    pitch: float = 19.05,
) -> KeyboardGeometryModel:
    """Load a KLE JSON file and generate the geometry model.

    Convenience wrapper around :func:`parse_layout` + :func:`generate`.
    """
    rows = load_kle(path)
    keys = [key for row in rows for key in row]
    layout = KeyboardLayout(keys=keys, pitch=pitch)
    return generate(
        layout,
        switch_family=switch_family,
        stabilizer_family=stabilizer_family,
        plate_thickness=plate_thickness,
        edge_margin=edge_margin,
        corner_radius=corner_radius,
        screw_diameter=screw_diameter,
        screw_edge_offset=screw_edge_offset,
    )


def validate(
    layout: KeyboardLayout,
    model: KeyboardGeometryModel,
    switch_family: str = "mx_alps",
    stabilizer_family: str = "cherry",
) -> list[str]:
    """Validate the keyboard geometry model.

    Returns a list of error messages (empty = valid).
    """
    return _validate(layout, model, switch_family, stabilizer_family)


__all__ = [
    "parse_layout",
    "generate",
    "generate_from_file",
    "validate",
    "KeyboardLayout",
    "KeyboardGeometryModel",
    "KeyboardMetadata",
    "register_switch",
    "register_stabilizer",
    "register_keycap",
    "get_switch",
    "get_stabilizer",
    "get_keycap",
    "registered_switches",
    "registered_stabilizers",
    "registered_keycaps",
]
