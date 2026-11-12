"""Plate generator — assembles the complete keyboard geometry model.

Entry point: :func:`generate` takes a parsed layout, switch/stabilizer
families, the Well ring's wall thickness and (optionally) the Well Cutout, and
returns a :class:`~keyboard.metadata.KeyboardGeometryModel`.

The plate is **derived**, never chosen (ADR-0014): the Well Cutout is the real
keycap footprint plus the wobble allowance, and the plate is the Cutout grown by
one wall thickness on each side so it bears on the Well walls' lower faces. The
switch-free border therefore falls out of the two sizes; there is no free
``edge_margin`` knob. The plate carries **no** mounting holes of its own — the
enclosure injects the Well-mount holes it needs.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import replace

from keyboard.geometry.cutouts import stabilizer_cutouts, switch_cutouts
from keyboard.geometry.keycaps import keycap_footprint, keycap_specs
from keyboard.geometry.outline import generate_outline
from keyboard.geometry.seam import (
    plate_seam,
    seam_conflicts,
    section_outlines,
)
from keyboard.layout.layout import KeyboardLayout
from keyboard.metadata import Cutout, KeyboardGeometryModel, KeyboardMetadata, MountingHole
from keyboard.registry import get_keycap, get_switch

#: A rectangle ``(x0, y0, x1, y1)`` in plate-local mm.
Rect = tuple[float, float, float, float]


def cutout_bounds(
    layout: KeyboardLayout,
    keycap_profile: str = "xda",
    wobble: float = 0.0,
) -> Rect:
    """The Well Cutout rect: the real keycap footprint + the wobble allowance.

    The Cutout is sized by the keycaps, not by the plate and not by
    ``clearance.shell``: a keycap rocking under switch play must never strike a
    Well wall, so every cap's base gets ``wobble`` of clearance per side.
    """
    specs = keycap_specs(
        list(layout.keys),
        get_keycap(keycap_profile)(),
        pitch=layout.pitch,
        layout_centroid=layout._centroid(),
    )
    x0, y0, x1, y1 = keycap_footprint(layout.switch_centers, specs)
    return (x0 - wobble, y0 - wobble, x1 + wobble, y1 + wobble)


def _border(
    cutouts: list[Cutout], plate: Rect
) -> tuple[float, float, float, float]:
    """Switch-free border per side ``(left, right, bottom, top)`` in mm."""
    px0, py0, px1, py1 = plate
    if not cutouts:
        return (0.0, 0.0, 0.0, 0.0)
    left = right = bottom = top = float("inf")
    for cut in cutouts:
        xs = [cut.x + vx for vx, _ in cut.vertices]
        ys = [cut.y + vy for _, vy in cut.vertices]
        left = min(left, min(xs) - px0)
        right = min(right, px1 - max(xs))
        bottom = min(bottom, min(ys) - py0)
        top = min(top, py1 - max(ys))
    return (left, right, bottom, top)


def generate(
    layout: KeyboardLayout,
    switch_family: str = "mx_alps",
    stabilizer_family: str = "cherry",
    plate_thickness: float = 1.5,
    *,
    wall: float,
    cutout: Rect | None = None,
    keycap_profile: str = "xda",
    wobble: float = 0.0,
    corner_radius: float = 2.0,
    mounting_holes: Iterable[MountingHole] = (),
) -> KeyboardGeometryModel:
    """Generate the complete keyboard geometry model.

    Parameters
    ----------
    layout : KeyboardLayout
        Parsed keyboard layout.
    switch_family : str
        Default switch family name (default ``"mx_alps"``).  Per-key ``_t``
        overrides are resolved by :func:`switch_cutouts`.
    stabilizer_family : str
        Registered stabilizer family name (default ``"cherry"``).
    plate_thickness : float
        Plate thickness in mm.
    wall : float
        The Well ring / plate border per side (``config.wall.thickness``, mm).
        The plate extends exactly this far past the Cutout on every side. No
        default: the border is otherwise a guess.
    cutout : Rect | None
        The Well Cutout ``(x0, y0, x1, y1)`` in plate-local mm. ``None``
        derives it from the real keycap footprint plus *wobble*.
    keycap_profile : str
        Keycap profile used to derive the footprint when *cutout* is ``None``.
    wobble : float
        Keycap wobble allowance each side of the Cutout (mm, ADR-0014).
    corner_radius : float
        Plate corner radius (mm).
    mounting_holes : Iterable[MountingHole]
        Holes the plate carries, in plate-local ``(x, y, diameter)`` mm. Empty
        by default: the enclosure injects its Well-mount holes (ADR-0014).

    Returns
    -------
    KeyboardGeometryModel
        Pure-data geometry model ready for the CAD adapter.
    """
    if wall <= 0.0:
        raise ValueError(f"the plate needs a positive Well wall, got {wall}")
    centers = layout.switch_centers
    if not centers:
        raise ValueError("layout has no switches: no plate to generate")

    if cutout is None:
        cutout = cutout_bounds(layout, keycap_profile, wobble)
    cx0, cy0, cx1, cy1 = cutout
    if not (cx0 < cx1 and cy0 < cy1):
        raise ValueError(f"degenerate Well Cutout: {cutout}")

    # Plate = Cutout + one wall per side (ADR-0014).
    plate = (cx0 - wall, cy0 - wall, cx1 + wall, cy1 + wall)
    plate_x0, plate_y0, plate_x1, plate_y1 = plate

    # The margin of the plate past the switch centers is what the outline
    # needs; it is asymmetric whenever the Cutout is off their bounding box.
    xs = [p[0] for p in centers]
    ys = [p[1] for p in centers]
    margins = (
        min(xs) - plate_x0,
        plate_x1 - max(xs),
        min(ys) - plate_y0,
        plate_y1 - max(ys),
    )
    if min(margins) <= 0.0:
        raise ValueError(
            f"the Well Cutout {cutout} does not contain the switch grid: "
            "the outline would fold over itself"
        )
    outline = generate_outline(
        centers, margin=margins, corner_radius=corner_radius,
    )

    sw_cuts = switch_cutouts(layout.keys, switch_family, layout.pitch, layout._centroid())
    stab_cuts = stabilizer_cutouts(
        layout.keys, stabilizer_family, layout.pitch, layout._centroid()
    )

    holes = list(mounting_holes)
    width = plate_x1 - plate_x0
    height = plate_y1 - plate_y0

    metadata = KeyboardMetadata(
        width=width,
        height=height,
        plate_thickness=plate_thickness,
        switch_centers=list(centers),
        mounting_points=[(h.x, h.y) for h in holes],
        bounding_box=(width, height, plate_thickness),
        cutout=cutout,
        edge_margins=_border(sw_cuts + stab_cuts, plate),
    )

    model = KeyboardGeometryModel(
        plate_outline=outline,
        switch_cutouts=sw_cuts,
        stabilizer_cutouts=stab_cuts,
        mounting_holes=holes,
        metadata=metadata,
    )

    # The plate splits **between keys** (ADR-0003, ADR-0014). Compute the Seam
    # here so every consumer gets it, and fail HARD if it would cut a switch or
    # stabilizer cutout: a layout change must never silently bring back the
    # straight x=0 cut through the keys (issue #9).
    seam = plate_seam(model)
    conflicts = seam_conflicts(model, seam)
    if conflicts:
        raise ValueError(
            "the keyboard plate Seam crosses a cutout, so the Sections cannot "
            "rejoin cleanly: " + "; ".join(conflicts)
        )

    return replace(
        model,
        seam=seam,
        section_outlines=list(section_outlines(outline, seam, height)),
    )
