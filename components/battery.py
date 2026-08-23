"""Internal battery pack: cylindrical lithium cells.

The sealed deck carries its own power source; the only external connectivity
is the rear USB hub. Dimensions from ``config/hardware.yaml`` (``battery``
section): a cell diameter/length plus how many cells and how they are packed,
from which the pack outline is calculated — never a hand-written box.

Two packing arrangements are supported, both of which lay the cells flat
(a cell stood on end is longer than the case is tall):

``side_by_side``
    Cells parallel, touching along their barrels ("two barrels"). The pack is
    ``count`` diameters wide by one cell length deep.
``end_to_end``
    Cells collinear, positive terminal to negative cap ("snake-like"). The
    pack is one diameter wide by ``count`` lengths deep.

The pack's long axis runs along local +Y in both cases; the layout rotates it
into place, so the recipe picks the orientation rather than this module.
"""

from __future__ import annotations

import math
from typing import Any

from components.base import BoundingBox, Component, Keepout

#: Packing arrangements: (cells across, cells along the length axis).
_ARRANGEMENTS: dict[str, tuple[int, int]] = {
    "side_by_side": (1, 0),  # count across, 1 long
    "end_to_end": (0, 1),  # 1 across, count long
}


class Battery(Component):
    """Internal lithium cell pack (cylindrical cells, laid flat)."""

    name = "Battery"

    def __init__(self, hardware: dict[str, Any] | None = None) -> None:
        data = (hardware or {}).get("battery", {})
        # 18650: the name is the spec — 18 mm diameter, 65 mm long.
        self.cell_diameter = float(data.get("cell_diameter", 18.6))
        self.cell_length = float(data.get("cell_length", 65.2))
        self.count = int(data.get("count", 2))
        self.arrangement = str(data.get("arrangement", "side_by_side"))
        self.clearance = float(data.get("clearance", 2.0))
        #: Height of the floor cradles that key each cell's lateral position
        #: (mm) — see ``geometry/cradle.py``. Independent of the pack's own
        #: floor standoff (the recipe raises it by ``config.wall_thickness``,
        #: the same rib clearance every other floor-mounted part uses, see
        #: ``geometry.ribs.rib_height``): a taller cradle wraps more of the
        #: cell's curve, it does not lift the cell any higher.
        self.cradle_height = float(data.get("cradle_height", 5.0))

        if self.count < 1:
            raise ValueError(f"battery.count must be >= 1, got {self.count}")
        if self.arrangement not in _ARRANGEMENTS:
            raise ValueError(
                f"unknown battery.arrangement {self.arrangement!r}; "
                f"expected one of {sorted(_ARRANGEMENTS)}"
            )

    @property
    def cells_across(self) -> int:
        """Number of cells across the pack's short (X) axis."""
        across, _ = _ARRANGEMENTS[self.arrangement]
        return self.count if across else 1

    @property
    def cells_along(self) -> int:
        """Number of cells along the pack's long (Y) axis."""
        _, along = _ARRANGEMENTS[self.arrangement]
        return self.count if along else 1

    @property
    def width(self) -> float:
        """Pack width (mm): cells packed barrel-to-barrel across X."""
        return self.cells_across * self.cell_diameter

    @property
    def depth(self) -> float:
        """Pack depth (mm): cells laid end to end along Y."""
        return self.cells_along * self.cell_length

    @property
    def height(self) -> float:
        """Pack height (mm) — one cell diameter; the cells lie flat."""
        return self.cell_diameter

    def size(self) -> BoundingBox:
        return BoundingBox(self.width, self.depth, self.height)

    def keepout(self) -> Keepout:
        # The compartment reserves the pack outline plus a wiring margin.
        c = self.clearance
        return Keepout(self.width + 2 * c, self.depth + 2 * c, self.height + c)

    def _cell_centers(self) -> list[tuple[float, float]]:
        """Local ``(x, y)`` center of each cell (mm)."""
        d, length = self.cell_diameter, self.cell_length
        x0 = -(self.cells_across - 1) * d / 2.0
        y0 = -(self.cells_along - 1) * length / 2.0
        return [
            (x0 + i * d, y0 + j * length)
            for i in range(self.cells_across)
            for j in range(self.cells_along)
        ]

    #: Slices each cell's round cross-section is approximated in, along
    #: local X (the axis a placement rotation maps onto whatever world axis
    #: a ceiling's height actually varies along — Y here, once the recipe
    #: rotates the pack 90°). A single bounding box per cell would report
    #: the same 18.6 mm-wide footprint at every point along that axis, so a
    #: collision/clearance check comparing it against a ceiling that is only
    #: low over PART of that width — the common case, e.g. a plate whose
    #: switches start partway across — sees the whole footprint as blocked
    #: by the narrowest point, even where the true curved surface has long
    #: since cleared it. More slices resolve that varying clearance instead
    #: of collapsing it to one worst-case box. (Slicing by Z instead, i.e.
    #: local-X width per Z-band, only refines *how wide* the reported box
    #: is — every slice still spans the cylinder's full local-X extent, so
    #: it does nothing for exactly this case.)
    #: 64, not the original 16: raised while tracking down a clearance false
    #: positive against the keyboard's switch pins (see
    #: rp2040_keyboard.Rp2040Keyboard.occupied_volumes) — the worst-case
    #: gap the resolver reports keeps shrinking as this goes up to roughly
    #: 64, then plateaus (checked up to 512), so the remaining conservatism
    #: versus a true boolean check is the axis-aligned box model itself
    #: (see that method's docstring), not further slicing.
    _occupied_volume_slices = 64

    def occupied_volumes(self) -> list[tuple[float, float, float, BoundingBox]]:
        """Solid sub-volumes: each cell's round profile, sliced along local X.

        Each cylinder (axis along local Y, circular cross-section in local
        XZ — see :meth:`build`) is sliced into narrow local-X bands; slice
        *i*'s height is the circle's true height at whichever edge of the
        band is closer to the axis centre (x=0), so the slice's top face
        stays above the real surface everywhere within it rather than
        cutting into it. Reported as ``[0, height]`` boxes — full local-Y
        length, resting on the floor — since only the upper bound the
        ceiling sees is refined here, not the (unused) volume beneath it.
        """
        r = self.cell_diameter / 2.0
        n = self._occupied_volume_slices
        slice_w = self.cell_diameter / n
        volumes = []
        for cx, cy in self._cell_centers():
            for i in range(n):
                x0 = -r + i * slice_w
                x1 = x0 + slice_w
                # Tallest point in the slice is at whichever edge is closer
                # to the axis centre (x=0) — the circle is tallest there.
                x_edge = x0 if abs(x0) < abs(x1) else x1
                dx = min(abs(x_edge), r)
                height = r + math.sqrt(max(r * r - dx * dx, 0.0))
                volumes.append((
                    cx + (x0 + x1) / 2.0, cy, 0.0,
                    BoundingBox(slice_w, self.cell_length, height),
                ))
        return volumes

    def build(self):
        """Generate the pack solid: one cylinder per cell, lying along +Y,
        the pack bottom-aligned at the origin.
        """
        from utilities import cq_helpers

        cq_helpers.require_cq()
        result = None
        for cx, cy in self._cell_centers():
            # cylinder_centered builds along Z; lay it down onto +Y.
            cell = cq_helpers.cylinder_centered(self.cell_diameter, self.cell_length)
            cell = cell.rotate((0, 0, 0), (1, 0, 0), 90.0)
            cell = cq_helpers.translate(cell, cx, cy, self.cell_diameter / 2.0)
            result = cell if result is None else result.union(cell)
        return result
