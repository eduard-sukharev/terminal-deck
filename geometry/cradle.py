"""U-shaped cell cradles.

Printed floor saddles that key a resting cylindrical cell's lateral
position — not structural (nothing fastens the pack down), just
registration: a cell that is merely resting on the floor would roll or
slide in transit without one. The groove is cut with the *cell's own*
radius and centre height (``rest_height + diameter / 2``, matching the
pack's own floor placement — see the battery placement in
``config/layouts/clamshell.yaml``), not the block's own height: cutting a
full-radius groove into a block only as tall as the block itself, centred
on the block's own top edge, was tried first and produces knife-edge walls
that taper to nothing (verified against a real cutaway — see AGENTS.md) —
because a circle that large barely curves at all over a span as short as
the block's height, so nearly the whole block falls inside it. Centring the
cut on the cell's real geometry instead means only the (small) sliver of
that circle actually inside the block ever gets removed, leaving a shallow,
correctly-curved scallop with real wall material either side of it.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class CradleSpec:
    """Calculated dimensions of one cell cradle.

    Attributes
    ----------
    diameter : float
        Cell diameter the groove is cut to match (mm).
    rest_height : float
        Height of the cell's own bottom above this cradle's floor (mm) —
        the pack's placement raise. Together with ``diameter`` this fixes
        the cell's true centre height, so the groove conforms to where the
        cylinder actually is rather than an independent guess.
    height : float
        Cradle block height (mm) — how far up the saddle reaches to wrap
        the cell; independent of ``rest_height``; a taller block wraps more
        of the cell's curve.
    width : float
        Extent of the saddle block along the cell's own axis (mm).
    clearance : float
        Extra radius added to the groove so the cell is a loose, not a
        press, fit (mm).
    wall : float
        Minimum wall thickness left beyond the groove opening at the
        block's top edge (mm) — real material to actually print, not a
        feather edge.
    """

    diameter: float
    rest_height: float
    height: float
    width: float
    clearance: float = 0.3
    wall: float = 2.0

    @property
    def groove_radius(self) -> float:
        """Groove radius (mm): the cell's own radius plus fit clearance."""
        return self.diameter / 2.0 + self.clearance

    @property
    def cell_center_z(self) -> float:
        """The resting cell's true centre height above this cradle's floor."""
        return self.rest_height + self.diameter / 2.0

    @property
    def opening_half_width(self) -> float:
        """Half-width of the groove cut at the block's top edge (mm).

        Where the cell's own circle actually intersects ``z = height``; 0
        if the block doesn't reach that high.
        """
        dz = self.cell_center_z - self.height
        inside = self.groove_radius**2 - dz**2
        return math.sqrt(inside) if inside > 0.0 else 0.0

    @property
    def block_half_width(self) -> float:
        """Half-width of the saddle block (mm): the groove opening plus a
        real wall on each side, so the top edge is never a feather edge."""
        return self.opening_half_width + self.wall


def build(spec: CradleSpec):
    """One U-shaped saddle, its groove centred on local Y, resting at z=0.

    Local Y, not X: ``components.battery.Battery`` lays every cell's long
    axis along its own local +Y (see its module docstring), so building the
    groove on the same axis here means the caller can place a saddle with
    exactly the cell's own placement (rotation included) instead of
    re-deriving the cell's world-frame axis independently.

    The groove is a cylinder of :attr:`CradleSpec.groove_radius`, axis
    along local Y, centred at :attr:`CradleSpec.cell_center_z` — i.e. it is
    a close copy of the cell itself, not an independently-sized cutter — cut
    from a block :attr:`CradleSpec.block_half_width` wide (real wall margin
    beyond the cut) and ``height`` tall.

    Returns
    -------
    Shape
        The saddle solid.
    """
    from utilities import cad_helpers

    cad_helpers.require_cad()
    half = spec.block_half_width
    block = cad_helpers.box_centered(2 * half, spec.width, spec.height)
    block = cad_helpers.translate(block, 0.0, 0.0, spec.height / 2.0)
    groove = cad_helpers.cylinder_centered(2 * spec.groove_radius, spec.width + 2.0)
    groove = cad_helpers.rotate_x(groove, 90.0)
    groove = cad_helpers.translate(groove, 0.0, 0.0, spec.cell_center_z)
    return cad_helpers.cut(block, groove)
