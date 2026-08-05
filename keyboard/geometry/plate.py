"""Plate generator — assembles the complete keyboard geometry model.

Entry point: :func:`generate` takes a parsed layout, switch/stabilizer
families, and plate configuration, and returns a
:class:`~keyboard.metadata.KeyboardGeometryModel`.
"""

from __future__ import annotations

from keyboard.geometry.cutouts import stabilizer_cutouts, switch_cutouts
from keyboard.geometry.mounting import generate_mounting_holes
from keyboard.geometry.outline import generate_outline
from keyboard.layout.layout import KeyboardLayout
from keyboard.metadata import KeyboardGeometryModel, KeyboardMetadata
from keyboard.registry import get_switch


def generate(
    layout: KeyboardLayout,
    switch_family: str = "mx_alps",
    stabilizer_family: str = "cherry",
    plate_thickness: float = 1.5,
    edge_margin: float = 8.0,
    corner_radius: float = 8.0,
    screw_diameter: float = 2.0,
    screw_edge_offset: float = 5.0,
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
    edge_margin : float
        Margin beyond outermost switch centers (mm).
    corner_radius : float
        Plate corner radius (mm).
    screw_diameter : float
        Mounting screw hole diameter (mm).
    screw_edge_offset : float
        Mounting hole inset from plate edge (mm).

    Returns
    -------
    KeyboardGeometryModel
        Pure-data geometry model ready for the CadQuery adapter.
    """
    pitch = layout.pitch
    centroid = layout._centroid()
    centers = layout.switch_centers

    sw = get_switch(switch_family)()
    verts = sw.cutout_vertices()
    cutout_half_x = max(abs(v[0]) for v in verts)
    cutout_half_y = max(abs(v[1]) for v in verts)
    effective_margin = edge_margin + max(cutout_half_x, cutout_half_y)

    outline = generate_outline(centers, margin=effective_margin, corner_radius=corner_radius)

    sw_cuts = switch_cutouts(layout.keys, switch_family, pitch, centroid)
    stab_cuts = stabilizer_cutouts(layout.keys, stabilizer_family, pitch, centroid)

    holes = generate_mounting_holes(
        outline, edge_offset=screw_edge_offset, screw_diameter=screw_diameter,
        switch_cutouts=sw_cuts, stabilizer_cutouts=stab_cuts,
    )

    xs = [p[0] for p in outline]
    ys = [p[1] for p in outline]
    bbox = (max(xs) - min(xs), max(ys) - min(ys), plate_thickness)

    metadata = KeyboardMetadata(
        width=bbox[0],
        height=bbox[1],
        plate_thickness=plate_thickness,
        switch_centers=centers,
        mounting_points=[(h.x, h.y) for h in holes],
        bounding_box=bbox,
    )

    return KeyboardGeometryModel(
        plate_outline=outline,
        switch_cutouts=sw_cuts,
        stabilizer_cutouts=stab_cuts,
        mounting_holes=holes,
        metadata=metadata,
    )
