"""Mounting boss generator.

A boss couples a screw/insert to the shell wall. Inputs:

* hole diameter (for the heat-set insert or screw pilot)
* screw size (clearance/head from the fastener library)
* insert type (heat-set insert geometry)
* wall thickness

The boss geometry (outer diameter, height, wall standoff) is *calculated*
here; the CadQuery solid is generated in :func:`build`.
"""

from __future__ import annotations

from dataclasses import dataclass

from utilities import fasteners


@dataclass(frozen=True)
class BossSpec:
    """Fully-calculated dimensions of a boss.

    Attributes
    ----------
    hole_diameter : float
        Bore through the boss (mm).
    outer_diameter : float
        Outer diameter of the boss body (mm).
    height : float
        Boss height above the shell floor (mm).
    wall_thickness : float
        Shell wall thickness the boss is attached to (mm).
    insert_diameter : float | None
        Heat-set insert outside diameter when an insert is used (mm).
    """

    hole_diameter: float
    outer_diameter: float
    height: float
    wall_thickness: float
    insert_diameter: float | None = None

    @property
    def sleeve_thickness(self) -> float:
        """Material between the bore and the boss outer diameter (mm)."""
        return (self.outer_diameter - self.hole_diameter) / 2


def boss_spec(
    wall_thickness: float,
    screw_size: str = "M2.5",
    insert_type: str | None = "M2.5",
    hole_diameter: float | None = None,
    height: float | None = None,
    sleeve: float = 1.2,
) -> BossSpec:
    """Compute a :class:`BossSpec` from standard inputs.

    Parameters
    ----------
    wall_thickness : float
        Shell wall thickness (mm).
    screw_size : str
        Screw library key ("M2", "M2.5", "M3").
    insert_type : str or None
        Heat-set insert key, or ``None`` for a tapped hole.
    hole_diameter : float or None
        Bore diameter; defaults from insert library or screw pilot hole.
    height : float or None
        Boss height; defaults to ``2 * wall_thickness``.
    sleeve : float
        Minimum material sleeve between bore and outer diameter (mm).

    Returns
    -------
    BossSpec
        The calculated boss dimensions.
    """
    screw = fasteners.screw(screw_size)

    if insert_type is not None:
        insert = fasteners.heat_insert(insert_type)
        bore = hole_diameter if hole_diameter is not None else insert.printed_hole_diameter
        insert_d = insert.outside_diameter
    else:
        bore = hole_diameter if hole_diameter is not None else screw.pilot_hole
        insert_d = None

    # Never invent a bore smaller than the insert/screw allows.
    if insert_d is not None:
        bore = max(bore, insert.printed_hole_diameter)

    outer = bore + 2 * sleeve
    boss_height = height if height is not None else 2 * wall_thickness
    return BossSpec(
        hole_diameter=bore,
        outer_diameter=outer,
        height=boss_height,
        wall_thickness=wall_thickness,
        insert_diameter=insert_d,
    )


def build(spec: BossSpec, x: float = 0.0, y: float = 0.0):
    """Generate a boss solid centered at (x, y).

    Parameters
    ----------
    spec : BossSpec
        Calculated boss dimensions.
    x, y : float
        Boss center in the shell frame (mm).

    Returns
    -------
    cadquery.Workplane
        The boss solid, rising from the shell floor (z=0) to ``spec.height``,
        with the bore removed.
    """
    from utilities import cq_helpers

    cq_helpers.require_cq()
    body = cq_helpers.cylinder_centered(spec.outer_diameter, spec.height)
    body = cq_helpers.translate(body, x, y, spec.height / 2.0)
    bore = cq_helpers.cylinder_centered(spec.hole_diameter, spec.height)
    bore = cq_helpers.translate(bore, x, y, spec.height / 2.0)
    return body.cut(bore)
