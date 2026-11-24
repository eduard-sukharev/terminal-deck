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

from keyboard.geometry.bands import grow_bands, keycap_bands, quantize_bands
from keyboard.geometry.cutouts import stabilizer_cutouts, switch_cutouts
from keyboard.geometry.keycaps import keycap_footprint, keycap_specs
from keyboard.geometry.outline import (
    PlateTab,
    attach_features,
    bands_to_polygon,
    treat_corners,
)
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
    minimum_feature: float = 0.6,
    mounting_holes: Iterable[MountingHole] = (),
    ears: Iterable = (),
    notches: Iterable[Rect] = (),
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
    minimum_feature : float
        Printable minimum (``config.material.minimum_feature``, mm). Row X
        differences below it are not a real step and are merged, so the plate
        adapts to any layout without emitting a sub-printable staircase.
    mounting_holes : Iterable[MountingHole]
        Holes the plate carries, in plate-local ``(x, y, diameter)`` mm. Empty
        by default: the enclosure injects its Well-mount holes (ADR-0014).
    ears : Iterable[PlateTab]
        Filleted tabs the enclosure needs outboard of the plate edge (the M2
        boss stations), plate-local mm. Merged into the outline; the solid and
        the holes stay the adapter's job.
    notches : Iterable[Rect]
        Rectangles the chassis forces the plate to give up, plate-local mm.
        Cut out of the outline; the plate must stay one connected sheet.

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

    pinned = cutout is not None
    if cutout is None:
        cutout = cutout_bounds(layout, keycap_profile, wobble)

    # The plate follows the rows: each band is one row's real keycap extent, so
    # a layout with a narrow spacebar row yields a staircase (ADR-0014's
    # ``plate = cutout + wall`` holds band by band). When the caller pins the
    # Cutout, there is no per-row information to step along, so it stays a
    # single rectangular band.
    specs = keycap_specs(
        list(layout.keys),
        get_keycap(keycap_profile)(),
        pitch=layout.pitch,
        layout_centroid=layout._centroid(),
    )
    row_bands: tuple[tuple[float, float, float, float], ...] = ()
    if pinned:
        cutout_bands = [(cutout[1], cutout[3], cutout[0], cutout[2])]
    else:
        bands = quantize_bands(keycap_bands(specs), minimum_feature)
        row_bands = tuple(bands)
        cutout_bands = grow_bands(bands, wobble, wobble)
    plate_bands = grow_bands(cutout_bands, wall, wall)

    cutout = (
        min(b[2] for b in cutout_bands),
        cutout_bands[0][0],
        max(b[3] for b in cutout_bands),
        cutout_bands[-1][1],
    )
    cx0, cy0, cx1, cy1 = cutout
    if not (cx0 < cx1 and cy0 < cy1):
        raise ValueError(f"degenerate Well Cutout: {cutout}")

    # Plate = Cutout + one wall per side (ADR-0014).
    plate = (
        min(b[2] for b in plate_bands),
        plate_bands[0][0],
        max(b[3] for b in plate_bands),
        plate_bands[-1][1],
    )
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
    # The Cutout is sharp where the plate is rounded (``radius - wall``); the
    # plate keeps the Well's bearing border one wall wide on the straight runs
    # (ADR-0014) and its outer corners rounded at ``corner_radius`` exactly as
    # the rectangular plate was. The concave step corners are chamfered.
    cutout_outline = treat_corners(
        bands_to_polygon(cutout_bands),
        max(0.0, corner_radius - wall),
        minimum_feature,
    )
    # The plate's plain stepped outline: the band polygon with its corners left
    # square. It is what the Well ring is built from -- the ring's structural
    # body must keep its corner columns' walls square, so the corner rounding
    # belongs to the plate's own outline only (``plate_outline`` below).
    plate_base_outline = bands_to_polygon(plate_bands)
    plate_outline = treat_corners(
        plate_base_outline, corner_radius, minimum_feature
    )
    outline = attach_features(plate_outline, ears, notches)

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
        row_bands=row_bands,
        cutout_outline=tuple(cutout_outline),
        plate_outline=tuple(plate_outline),
        plate_base_outline=tuple(plate_base_outline),
        plate_bands=tuple(plate_bands),
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
