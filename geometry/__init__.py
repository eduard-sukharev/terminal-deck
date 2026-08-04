"""Generative geometry helpers (boss, fillet, shell, ribs, vents, cutouts)."""

from geometry.boss import BossSpec, boss_spec, build as build_boss
from geometry.cutouts import Cutout, from_connector, generate as generate_cutouts
from geometry.ribs import RibSpec, build as build_ribs, rib_layout
from geometry.vents import VentSpec, build as build_vents, vent_slots

__all__ = [
    "BossSpec",
    "boss_spec",
    "build_boss",
    "Cutout",
    "from_connector",
    "generate_cutouts",
    "RibSpec",
    "rib_layout",
    "build_ribs",
    "VentSpec",
    "vent_slots",
    "build_vents",
]
