"""Rib generator.

Adds stiffening ribs to the base/lid interior. Rib layout (pitch, thickness,
height) is calculated from the panel size and wall thickness — never
hardcoded.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class RibSpec:
    """Calculated rib layout.

    Attributes
    ----------
    thickness : float
        Rib wall thickness (mm).
    height : float
        Rib height above the floor (mm).
    pitch : float
        Center-to-center spacing between parallel ribs (mm).
    positions : tuple[float, ...]
        Rib center offsets along the long axis (mm).
    """

    thickness: float
    height: float
    pitch: float
    positions: tuple[float, ...] = field(default_factory=tuple)


def rib_layout(
    panel_width: float,
    panel_depth: float,
    wall_thickness: float,
    pitch: float | None = None,
    rib_thickness: float | None = None,
    rib_height: float | None = None,
) -> RibSpec:
    """Compute a rib layout across a panel.

    Parameters
    ----------
    panel_width : float
        Interior width along X (mm).
    panel_depth : float
        Interior depth along Y (mm).
    wall_thickness : float
        Shell wall thickness (mm).
    pitch : float or None
        Rib spacing; defaults to ``wall_thickness * 12``.
    rib_thickness : float or None
        Defaults to ``wall_thickness * 0.6``.
    rib_height : float or None
        Defaults to ``wall_thickness * 2``.

    Returns
    -------
    RibSpec
        The calculated layout.
    """
    pitch = pitch if pitch is not None else wall_thickness * 12
    thickness = rib_thickness if rib_thickness is not None else wall_thickness * 0.6
    height = rib_height if rib_height is not None else wall_thickness * 2

    # Ribs run along Y, spaced across X. Insets at the panel edges.
    margin = pitch / 2
    count = max(0, int((panel_width - 2 * margin) // pitch))
    positions = tuple(
        -panel_width / 2 + margin + pitch / 2 + i * pitch for i in range(count)
    )
    return RibSpec(thickness=thickness, height=height, pitch=pitch, positions=positions)


def build(spec: RibSpec, panel_width: float, panel_depth: float):
    """Generate rib solids inside a panel.

    Ribs run along Y at the calculated X positions, rising from the panel
    floor (z=0) to ``spec.height``.

    Parameters
    ----------
    spec : RibSpec
        Calculated rib layout.
    panel_width : float
        Interior width along X (mm).
    panel_depth : float
        Interior depth along Y (mm).

    Returns
    -------
    list[cadquery.Workplane]
        The rib solids (union into the shell by the caller).
    """
    from utilities import cq_helpers

    cq_helpers.require_cq()
    ribs = []
    for pos in spec.positions:
        rib = cq_helpers.box_centered(spec.thickness, panel_depth, spec.height)
        ribs.append(cq_helpers.translate(rib, pos, 0.0, spec.height / 2.0))
    return ribs
