"""Vent pattern generator.

Produces a row of vertical vent slots through a wall (cooling for the SBC).
Slot size, spacing, and pattern are calculated parameters — never hardcoded.
A slot may stand over a connector cutout as long as it starts a web above it;
it is dropped only where its X range must stay solid (Seam bands, features
fused into the wall).
"""

from __future__ import annotations

from dataclasses import dataclass, field

#: Default distance (mm) from the panel edges to the slots, along the row and
#: from the floor/roof.
MARGIN = 3.0


@dataclass(frozen=True)
class VentSpec:
    """Calculated vent layout.

    Attributes
    ----------
    slot_width : float
        Slot width along the wall (mm).
    gap : float
        Material gap between slots (mm).
    margin : float
        Distance from the panel edge to the first slot (mm).
    positions : tuple[float, ...]
        Slot center offsets along the wall (mm); an X repeats where a solid
        band splits its slot in two.
    spans : tuple[tuple[float, float], ...]
        ``(z0, z1)`` of each slot, matching ``positions`` (mm).
    """

    slot_width: float
    gap: float
    margin: float
    positions: tuple[float, ...] = field(default_factory=tuple)
    spans: tuple[tuple[float, float], ...] = field(default_factory=tuple)


def vent_slots(
    vent_axis_extent: float,
    z_range: tuple[float, float],
    slot_width: float | None = None,
    gap: float | None = None,
    margin: float = MARGIN,
    keepouts: tuple[tuple[float, float], ...] = (),
    raised: tuple[tuple[float, float, float], ...] = (),
    min_length: float | None = None,
    solid_bands: tuple[tuple[float, float], ...] = (),
) -> VentSpec:
    """Compute a row of vertical vent slots.

    Parameters
    ----------
    vent_axis_extent : float
        Wall extent along the row (mm); the row is centered on 0.
    z_range : tuple[float, float]
        Lowest and highest Z any slot may reach (mm).
    slot_width : float or None
        Slot short dimension (mm); defaults to the printable minimum 0.8.
    gap : float or None
        Material between slots (mm); defaults to ``slot_width``.
    margin : float
        Edge margin along the row (mm).
    keepouts : tuple[tuple[float, float], ...]
        ``(x0, x1)`` ranges left solid over the whole height: any slot whose
        width overlaps one is dropped (Seam bands, features fused into the
        wall).
    raised : tuple[tuple[float, float, float], ...]
        ``(x0, x1, z)``: a slot overlapping ``x0..x1`` starts no lower than
        ``z`` (a connector cutout below it, plus a web).
    min_length : float or None
        Shortest slot worth cutting (mm); defaults to three slot widths.
    solid_bands : tuple[tuple[float, float], ...]
        ``(z0, z1)`` bands left solid along the whole row (e.g. either side
        of a parting plane); a slot crossing one is split around it.

    Returns
    -------
    VentSpec
        The calculated vent layout.
    """
    slot_width = slot_width if slot_width is not None else 0.8
    gap = gap if gap is not None else slot_width
    min_length = min_length if min_length is not None else 3 * slot_width
    z0, z1 = z_range
    usable = vent_axis_extent - 2 * margin
    step = slot_width + gap
    count = max(0, int(usable // step))
    positions, spans = [], []
    for i in range(count):
        pos = -vent_axis_extent / 2 + margin + step / 2 + i * step
        lo, hi = pos - slot_width / 2, pos + slot_width / 2
        if not all(hi <= k0 or lo >= k1 for k0, k1 in keepouts):
            continue
        bottom = max([z0] + [z for k0, k1, z in raised if hi > k0 and lo < k1])
        pieces = [(bottom, z1)]
        for b0, b1 in solid_bands:
            pieces = [
                part for a, b in pieces
                for part in ((a, min(b, b0)), (max(a, b1), b)) if part[1] > part[0]
            ]
        for a, b in pieces:
            if b - a >= min_length:
                positions.append(pos)
                spans.append((a, b))
    return VentSpec(
        slot_width=slot_width, gap=gap, margin=margin,
        positions=tuple(positions), spans=tuple(spans),
    )


def build(spec: VentSpec, wall_thickness: float):
    """Generate the vent slot cutters, centered on the wall midplane at y=0.

    Each slot is ``slot_width`` along X, crosses the wall along Y (the wall
    plus a slot width either side, so it always cuts through) and runs over
    its own ``(z0, z1)`` span in Z. All slots come back as one compound, to
    subtract from the shell with a single cut.
    """
    from utilities import cad_helpers

    if not spec.positions:
        return cad_helpers.empty_solid()
    depth = wall_thickness + 2 * spec.slot_width
    slots = [
        cad_helpers.translate(
            cad_helpers.box_centered(spec.slot_width, depth, z1 - z0), x, 0.0, (z0 + z1) / 2.0
        )
        for x, (z0, z1) in zip(spec.positions, spec.spans)
    ]
    return cad_helpers.make_compound(slots)
