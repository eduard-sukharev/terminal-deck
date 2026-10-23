"""Section splitting along X (ADR 0003).

A part too wide for the build volume is cut into two or three Sections along
Seams. A Seam is a line in plan view: straight, or stepped (``__--__--__``)
so that walking along Y it jogs by ``step`` in X on alternate segments. The
jogs are plain butt joints (no tongue-and-groove, no dowels). The cut is a
boolean partition, so the Sections rejoin to the original with no gap and no
overlap by construction.
"""

from __future__ import annotations

from utilities import cad_helpers

#: Printer build volume (X, Y, Z) in mm — see AGENTS.md "Build volume".
#: Slack (mm) added around a part so the splitting region always overhangs it.
_MARGIN: float = 1.0

BUILD_VOLUME: tuple[float, float, float] = (220.0, 220.0, 256.0)


def _left_region(seam, depth: float, x_extent: float, z_extent: float):
    """Solid covering everything left of the Seam (oversized in X/Z)."""
    pad = 2.0 * x_extent
    pieces = []
    for y0, y1, sx in seam.segments(depth):
        width = sx + pad
        box = cad_helpers.box_centered(width, y1 - y0, 2.0 * z_extent)
        pieces.append(cad_helpers.translate(box, sx - width / 2.0, (y0 + y1) / 2.0, 0.0))
    return cad_helpers.union(pieces[0], *pieces[1:])


def split_sections(shape, seams, depth: float) -> list:
    """Split ``shape`` along ``seams`` into ``len(seams) + 1`` Sections.

    ``seams`` are ordered left to right; each is anything with
    ``segments(depth) -> [(y0, y1, x)]`` (a config
    :class:`~utilities.config_loader.Seam` or a plate ``RowSeam``). ``depth``
    is the part's extent in Y (centered on the origin). Returns the Sections
    left to right.
    """
    box = cad_helpers.bounding_box(shape)
    seam_x = max(abs(x) for seam in seams for _, _, x in seam.segments(depth))
    x_extent = max(abs(box.xmin), abs(box.xmax), seam_x) + _MARGIN
    z_extent = max(abs(box.zmin), abs(box.zmax)) + _MARGIN
    # Pad Y so Sections of a part slightly off-center are still fully covered.
    y_depth = max(depth, 2.0 * max(abs(box.ymin), abs(box.ymax))) + 2.0 * _MARGIN
    sections = []
    remainder = shape
    for seam in seams:
        region = _left_region(seam, y_depth, x_extent, z_extent)
        sections.append(cad_helpers.intersect(remainder, region))
        remainder = cad_helpers.cut(remainder, region)
    sections.append(remainder)
    return sections


def check_build_volume(
    parts: dict[str, object],
    volume: tuple[float, float, float] = BUILD_VOLUME,
) -> list[str]:
    """Return a violation message per part that does not fit as modelled.

    Parts are modelled flat in their print orientation (ADR 0003 declares each
    Section's orientation), so Z must fit the build height and X/Y the bed, with
    the bed's X and Y interchangeable.
    """
    errors = []
    bed = sorted(volume[:2])
    for name, shape in parts.items():
        x, y, z = cad_helpers.bounding_box_mm(shape)
        footprint = sorted((x, y))
        if z > volume[2] + 1e-6 or any(d > l + 1e-6 for d, l in zip(footprint, bed)):
            errors.append(
                f"{name}: {x:.1f} x {y:.1f} x {z:.1f} mm exceeds "
                f"build volume {volume[0]:g} x {volume[1]:g} x {volume[2]:g} mm"
            )
    return errors


def check_sections(whole, sections, tol: float = 1e-6) -> list[str]:
    """Violations of the Section contract: each connected, and a lossless split."""
    errors = []
    whole_volume = cad_helpers.volume_mm3(whole)
    for i, section in enumerate(sections):
        n = cad_helpers.solid_count(section)
        if n != 1:
            errors.append(f"Section {i} is {n} solids, expected 1 connected solid")
    for i, a in enumerate(sections):
        for j in range(i + 1, len(sections)):
            overlap = cad_helpers.volume_mm3(cad_helpers.intersect(a, sections[j]))
            if overlap > tol * max(1.0, whole_volume):
                errors.append(f"Sections {i} and {j} overlap by {overlap:.3f} mm^3")
    gap = whole_volume - sum(cad_helpers.volume_mm3(s) for s in sections)
    if abs(gap) > tol * max(1.0, whole_volume):
        errors.append(f"Sections do not rejoin: {gap:.3f} mm^3 missing")
    return errors
