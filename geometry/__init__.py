"""Generative geometry helpers (boss, fillet, shell, ribs, vents, cutouts, switch)."""

from geometry.boss import BossSpec, boss_spec, build as build_boss
from geometry.cutout_registry import (
    get_stabilizer_cutout,
    get_switch_cutout,
    registered_stabilizer_cutouts,
    registered_switch_cutouts,
    register_stabilizer_cutout,
    register_switch_cutout,
)
from geometry.cutouts import Cutout, from_connector, generate as generate_cutouts
from geometry.ribs import RibSpec, build as build_ribs, rib_layout
from geometry.stabilizer_cutout import (
    StabilizerCutoutSpec,
    StabilizerPlacement,
    build_stabilizer_cutout,
    stabilizer_offset,
    stabilizer_pair,
)
from geometry.switch_cutout import SwitchCutoutSpec, build_cutout
from geometry.vents import VentSpec, build as build_vents, vent_slots

__all__ = [
    "BossSpec",
    "boss_spec",
    "build_boss",
    "Cutout",
    "from_connector",
    "generate_cutouts",
    "get_stabilizer_cutout",
    "get_switch_cutout",
    "RibSpec",
    "rib_layout",
    "build_ribs",
    "registered_stabilizer_cutouts",
    "registered_switch_cutouts",
    "register_stabilizer_cutout",
    "register_switch_cutout",
    "StabilizerCutoutSpec",
    "StabilizerPlacement",
    "build_stabilizer_cutout",
    "stabilizer_offset",
    "stabilizer_pair",
    "SwitchCutoutSpec",
    "build_cutout",
    "VentSpec",
    "vent_slots",
    "build_vents",
]
