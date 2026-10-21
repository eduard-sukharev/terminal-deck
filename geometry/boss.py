"""Mounting boss generator.

A boss couples a screw/insert to the shell wall. Inputs:

* hole diameter (for the heat-set insert or screw pilot)
* screw size (clearance/head from the fastener library)
* insert type (heat-set insert geometry)
* wall thickness

The boss geometry (outer diameter, height, wall standoff) is *calculated*
here; the solid is generated in :func:`build`.
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

    @property
    def base_diameter(self) -> float:
        """Diameter of the boss's floor-contact footprint (mm).

        Per the FDM boss-design rule ("widen the base"), the printed
        footprint that actually carries load into the floor is wider than
        the boss's nominal outer diameter: one more full
        :attr:`sleeve_thickness` of material on each side, i.e. the sleeve is
        doubled right at the floor. Derived from the boss's own proportions
        rather than an independent literal, so it scales with screw/insert
        size automatically.
        """
        return self.outer_diameter + 2 * self.sleeve_thickness

    @property
    def flare_height(self) -> float:
        """Height of the tapered flare from :attr:`base_diameter` to :attr:`outer_diameter` (mm).

        Tied to ``wall_thickness`` — the same local structural scale the
        rest of the shell is sized against — and capped at the boss's own
        height so a very short boss flares over its full height instead of
        overshooting it.
        """
        return min(self.height, self.wall_thickness)


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

    The body is a freestanding post that flares out to
    :attr:`BossSpec.base_diameter` over the bottom :attr:`BossSpec.flare_height`
    (self-supporting — it widens going *down* to the floor, not up, so it
    needs no bridging/overhang support) before continuing straight at
    :attr:`BossSpec.outer_diameter`, per the FDM "widen the base" rule: this
    also removes the sharp boss-to-floor right-angle junction the flat rule
    separately calls out, replacing it with a continuous taper instead of a
    tacked-on chamfer.

    Parameters
    ----------
    spec : BossSpec
        Calculated boss dimensions.
    x, y : float
        Boss center in the shell frame (mm).

    Returns
    -------
    Shape
        The boss solid, rising from the shell floor (z=0) to ``spec.height``,
        with the bore removed.
    """
    from utilities import cad_helpers

    cad_helpers.require_cad()
    flare_h = spec.flare_height
    flare = cad_helpers.frustum_centered(spec.base_diameter, spec.outer_diameter, flare_h)
    flare = cad_helpers.translate(flare, x, y, flare_h / 2.0)
    body = flare
    if flare_h < spec.height:
        upper_h = spec.height - flare_h
        upper = cad_helpers.cylinder_centered(spec.outer_diameter, upper_h)
        upper = cad_helpers.translate(upper, x, y, flare_h + upper_h / 2.0)
        body = cad_helpers.union(body, upper)
    bore = cad_helpers.cylinder_centered(spec.hole_diameter, spec.height)
    bore = cad_helpers.translate(bore, x, y, spec.height / 2.0)
    return cad_helpers.cut(body, bore)
