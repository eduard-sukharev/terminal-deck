"""Cutout generation — translates switch and stabilizer polygons to key positions.

Produces the :class:`~keyboard.metadata.Cutout` instances that the plate
generator assembles into the final geometry model.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

from keyboard.metadata import Cutout
from keyboard.registry import get_stabilizer, get_switch
from keyboard.stabilizers.kb_builder import resolve_stabilizer_family
from keyboard.switches.kb_builder import resolve_switch_family

if TYPE_CHECKING:
    from keyboard.layout.key import Key


def switch_cutouts(
    keys: list[Key],
    default_family: str = "mx_alps",
    pitch: float = 19.05,
    layout_centroid: tuple[float, float] = (0.0, 0.0),
) -> list[Cutout]:
    """Generate switch cutout polygons for every key.

    Each key's ``_t`` field (parsed into :attr:`Key.switch_type`) selects the
    cutout shape, falling back to *default_family* when absent or unrecognised
    (kb_builder semantics).  Per-key kerf (``_k``) is applied as a per-edge
    outward offset matching ``kb_builder/lib/builder.py``.

    Parameters
    ----------
    keys : list[Key]
        All keys in the layout.
    default_family : str
        Default switch family name (default ``"mx_alps"``).
    pitch : float
        Switch pitch in mm.
    layout_centroid : tuple[float, float]
        Centroid of the layout in units (for centering).

    Returns
    -------
    list[Cutout]
        One cutout per key, positioned in mm.
    """
    cx, cy = layout_centroid
    result: list[Cutout] = []
    for key in keys:
        x = (key.x - cx) * pitch
        y = (key.y - cy) * pitch

        family = resolve_switch_family(key.switch_type, default_family)
        verts = list(get_switch(family)().cutout_vertices())

        k = (key.kerf or 0.0) / 2.0
        if k:
            verts = _apply_kerf(verts, k)

        rot = key.switch_rotation if key.switch_rotation is not None else 0.0
        if key.height > key.width and rot == 0.0:
            rot = 90.0
        if rot:
            verts = _rotate_polygon(verts, rot)

        result.append(Cutout(vertices=verts, x=x, y=y))
    return result


def stabilizer_cutouts(
    keys: list[Key],
    default_family: str = "cherry",
    pitch: float = 19.05,
    layout_centroid: tuple[float, float] = (0.0, 0.0),
) -> list[Cutout]:
    """Generate stabilizer cutout polygons for keys wide enough to need them.

    A key needs stabilizers when its effective width >= 2.0 units.  Each key's
    ``_s`` field (parsed into :attr:`Key.stabilizer_type`) selects the cutout
    shape, falling back to *default_family* when absent or unrecognised
    (kb_builder semantics).  Per-key kerf (``_k``) is applied via the
    stabilizer's symbolic vertex templates.

    Combined types (cherry, costar_compat) produce one polygon per key that
    includes the switch opening; costar produces two twin-slot polygons.

    Parameters
    ----------
    keys : list[Key]
        All keys in the layout.
    default_family : str
        Default stabilizer family name (default ``"cherry"``).
    pitch : float
        Switch pitch in mm.
    layout_centroid : tuple[float, float]
        Centroid of the layout in units.

    Returns
    -------
    list[Cutout]
        Stabilizer cutout polygons, one or two per stabilized key.
    """
    cx, cy = layout_centroid
    result: list[Cutout] = []
    for key in keys:
        eff = key.height if key.height > key.width else key.width
        if eff < 2.0:
            continue

        family = resolve_stabilizer_family(key.stabilizer_type, default_family)
        stab = get_stabilizer(family)()
        k = (key.kerf or 0.0) / 2.0
        polys = stab.cutout_polygons(eff, k)

        sw_x = (key.x - cx) * pitch
        sw_y = (key.y - cy) * pitch

        rot = key.stab_rotation if key.stab_rotation is not None else 0.0
        if key.height > key.width and rot == 0.0:
            rot = 90.0

        for poly in polys:
            if rot:
                poly = _rotate_polygon(poly, rot)
            result.append(Cutout(vertices=poly, x=sw_x, y=sw_y))
    return result


def _rotate_polygon(
    verts: list[tuple[float, float]],
    degrees: float,
) -> list[tuple[float, float]]:
    """Rotate polygon vertices around the origin."""
    rad = math.radians(degrees)
    c, s = math.cos(rad), math.sin(rad)
    return [(x * c - y * s, x * s + y * c) for x, y in verts]


def _apply_kerf(
    verts: list[tuple[float, float]],
    k: float,
) -> list[tuple[float, float]]:
    """Expand a symmetric axis-aligned polygon outward by *k* per edge.

    Matches kb_builder's per-vertex kerf formula
    (``lib/builder.py:373-417``): each coordinate moves away from the origin
    by *k*, enlarging the cutout.  No vertex has a zero coordinate in any
    kb_builder switch polygon, so ``copysign`` is well-defined.
    """
    return [(x - math.copysign(k, x), y - math.copysign(k, y)) for x, y in verts]
