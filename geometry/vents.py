"""Vent pattern generator.

Produces vent slot layouts (cooling for the SBC / display). Slot size,
spacing, and pattern are calculated parameters — never hardcoded.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class VentSpec:
    """Calculated vent layout.

    Attributes
    ----------
    slot_length : float
        Slot length along the vent axis (mm).
    slot_width : float
        Slot width (mm).
    gap : float
        Material gap between slots (mm).
    margin : float
        Distance from the panel edge to the first slot (mm).
    positions : tuple[float, ...]
        Slot center offsets along the vent axis (mm).
    """

    slot_length: float
    slot_width: float
    gap: float
    margin: float
    positions: tuple[float, ...] = field(default_factory=tuple)


def vent_slots(
    vent_axis_extent: float,
    perpendicular_extent: float,
    slot_width: float | None = None,
    gap: float | None = None,
    margin: float = 3.0,
) -> VentSpec:
    """Compute a row of vent slots.

    Parameters
    ----------
    vent_axis_extent : float
        Panel extent along the slot axis (mm).
    perpendicular_extent : float
        Panel extent perpendicular to the slot axis (mm).
    slot_width : float or None
        Slot short dimension (mm); defaults to the printable minimum 0.8.
    gap : float or None
        Material between slots (mm); defaults to ``slot_width``.
    margin : float
        Edge margin (mm).

    Returns
    -------
    VentSpec
        The calculated vent layout.
    """
    slot_width = slot_width if slot_width is not None else 0.8
    gap = gap if gap is not None else slot_width
    slot_length = perpendicular_extent - 2 * margin
    usable = vent_axis_extent - 2 * margin
    step = slot_width + gap
    count = max(0, int(usable // step))
    positions = tuple(
        -vent_axis_extent / 2 + margin + step / 2 + i * step for i in range(count)
    )
    return VentSpec(
        slot_length=slot_length,
        slot_width=slot_width,
        gap=gap,
        margin=margin,
        positions=positions,
    )


def build(spec: VentSpec, wall_thickness: float):
    """Generate vent slot cut solids for a shell face.

    Slots run along Y at the calculated X positions and are tall enough to
    cross the shell wall (depth = ``wall_thickness`` plus the slot width on
    each side). All slots are produced as a single compound so the caller can
    remove them with one boolean cut.

    Parameters
    ----------
    spec : VentSpec
        Calculated vent layout.
    wall_thickness : float
        Shell wall thickness the slots cross (mm).

    Returns
    -------
    cadquery.Workplane
        Compound of all slot solids (centered on the wall midplane at z=0),
        to subtract from the shell as a single cut.
    """
    from utilities import cq_helpers

    cq = cq_helpers.require_cq()
    # Slot cut boxes are centered on the wall midplane (z=0); each spans the
    # wall plus the slot width top and bottom so it always crosses through.
    depth = wall_thickness + 2 * spec.slot_width
    points = [(pos, 0.0) for pos in spec.positions]
    if not points:
        return cq.Workplane("XY")
    return (
        cq.Workplane("XY")
        .pushPoints(points)
        .rect(spec.slot_width, spec.slot_length)
        .extrude(depth)
    )
