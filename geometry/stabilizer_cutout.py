"""Cherry MX plate-mount stabilizer cutout geometry.

Provides the standard 7×15 mm stabilizer slot as a configurable CadQuery solid,
along with placement helpers for calculating left/right offsets from key width.

Usage::

    from geometry.stabilizer_cutout import (
        StabilizerCutoutSpec,
        build_stabilizer_cutout,
        stabilizer_offset,
        stabilizer_pair,
    )

    # Cut stabilizer slots in a plate
    for switch_x, switch_y in switch_positions:
        offset = stabilizer_offset(key_units, pitch)
        left, right = stabilizer_pair(switch_x, switch_y, offset)
        plate = plate.cut(build_stabilizer_cutout(thickness + 1.0, left.x, left.y))
        plate = plate.cut(build_stabilizer_cutout(thickness + 1.0, right.x, right.y))
"""

from __future__ import annotations

from dataclasses import dataclass

from geometry.cutout_registry import register_stabilizer_cutout


@register_stabilizer_cutout("mx-basic")
@dataclass(frozen=True)
class StabilizerCutoutSpec:
    """Cherry MX plate-mount stabilizer cutout slot.

    The standard plate-mount stabilizer slot is 7 mm wide × 15 mm tall.
    These are Cherry MX standard values — they should not be changed for
    normal use, but are configurable to accommodate non-standard fit.
    """

    width: float = 7.0
    height: float = 15.0

    @property
    def vertices(self) -> list[tuple[float, float]]:
        """Four corners of the stabilizer slot, centered on origin."""
        hw = self.width / 2.0
        hh = self.height / 2.0
        return [(-hw, -hh), (hw, -hh), (hw, hh), (-hw, hh)]


def build_stabilizer_cutout(
    height: float,
    x: float = 0.0,
    y: float = 0.0,
    z: float = 0.0,
    cutout_type: str = "mx-basic",
    spec: StabilizerCutoutSpec | None = None,
) -> object:
    """Return the selected stabilizer slot solid at ``(x, y, z)``.

    The solid is centered at ``(x, y, z)``, spanning ``z - height/2`` to
    ``z + height/2``.

    Parameters
    ----------
    height : float
        Extrusion height along Z (mm). For plate cutting, use
        ``plate_thickness + 1.0`` to guarantee clean-through.
    x, y, z : float
        Center position in the plate frame (mm).
    cutout_type : str
        Registered stabilizer cutout type. Default ``"mx-basic"``.
        Ignored if ``spec`` is provided (backward compat path).
    spec : StabilizerCutoutSpec or None
        Direct spec instance. If provided, used directly regardless of
        ``cutout_type`` (legacy support).
    """
    from geometry.cutout_registry import get_stabilizer_cutout
    from utilities import cq_helpers

    cq = cq_helpers.require_cq()

    if spec is not None:
        actual_spec = spec
    else:
        cls = get_stabilizer_cutout(cutout_type)
        actual_spec = cls()

    try:
        verts = actual_spec.vertices
    except NotImplementedError:
        return None

    solid = cq.Workplane("XY").polyline(verts).close().extrude(height)
    return cq_helpers.translate(solid, x, y, z - height / 2.0)


def stabilizer_offset(key_units: float, pitch: float = 19.05) -> float:
    """X distance from switch center to stabilizer cutout center.

    Standard Cherry MX formula: ``(key_units - 1) * pitch / 2``.

    For a 6.25u spacebar at 19.05 mm pitch::

        (6.25 - 1) * 19.05 / 2 = 50.0 mm

    Parameters
    ----------
    key_units : float
        Key width in units (e.g. 6.25 for a spacebar).
    pitch : float
        Switch pitch in mm (default 19.05).

    Returns
    -------
    float
        Absolute offset in mm. Caller manages sign (left/right).
    """
    if key_units <= 1.0:
        return 0.0
    return (key_units - 1.0) * pitch / 2.0


@dataclass(frozen=True)
class StabilizerPlacement:
    """One stabilizer cutout position in the plate frame."""

    x: float
    y: float


def stabilizer_pair(
    switch_x: float,
    switch_y: float,
    offset: float,
    offset_y: float = -1.4,
) -> tuple[StabilizerPlacement, StabilizerPlacement]:
    """Return left and right stabilizer placements for a switch.

    Parameters
    ----------
    switch_x, switch_y : float
        Switch center in the plate frame (mm).
    offset : float
        X offset from switch center to each stabilizer (mm). Use
        :func:`stabilizer_offset` to calculate from key width.
    offset_y : float
        Y offset from switch center (mm). The standard MX stab slot
        center is 1.4 mm below the switch center (default -1.4).

    Returns
    -------
    tuple[StabilizerPlacement, StabilizerPlacement]
        (left, right) stabilizer positions.
    """
    return (
        StabilizerPlacement(switch_x - offset, switch_y + offset_y),
        StabilizerPlacement(switch_x + offset, switch_y + offset_y),
    )
