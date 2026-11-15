"""The band joints' keyhole head recesses (ADR-0018).

Both band joints seat an ordinary button head in a counterbored pocket instead
of sinking a flat head flush: the head bears on a flat annulus ``depth`` below
the part's outer face, and the pocket's ceiling lifts back to that face on one
side in a 45 degree ramp. The ramp points **away** from the nearest wall, so

* the printed part never bridges a horizontal pocket ceiling (the seat ring is
  the only overhang, and 45 degrees is the print limit), and
* a driver still reaches the seated head from the side.

In plan the pocket is a stadium: ``pocket_diameter`` across and
``pocket_diameter + ramp_run`` long, with the head at its round wall-side end.
The mouth takes a 45 degree chamfer of whatever room is left over, which is
what fairs the edge in the reference renders.

The plan helpers are pure data so the joints can size their stations and check
them before any solid is built; only :func:`build_cutter` needs a CAD library.
"""

from __future__ import annotations

import math

from geometry.printability import OVERHANG_LIMIT_DEG
from utilities import fasteners

#: The recess ramp climbs at the print overhang limit, so it needs no support.
RAMP_ANGLE_DEG: float = OVERHANG_LIMIT_DEG


def mouth_chamfer(
    pocket_radius: float, margin: float, minimum_feature: float
) -> float:
    """The 45 degree chamfer that fairs a pocket's mouth (mm).

    ``margin`` is the plan distance from the screw axis to the nearest free
    face of the part. The chamfer takes only what is left over once the
    pocket's own radius and one ``minimum_feature`` of material are set aside,
    and never grows past ``minimum_feature`` itself. At a tight corner it
    shrinks to the little there is; :func:`edge_margin` stays truthful either
    way.
    """
    spare = margin - pocket_radius - minimum_feature
    return min(max(spare, 0.0), minimum_feature)


def edge_margin(
    pocket_radius: float, margin: float, minimum_feature: float
) -> float:
    """Material left between a pocket's mouth and the part's free face (mm)."""
    return margin - pocket_radius - mouth_chamfer(
        pocket_radius, margin, minimum_feature
    )


def build_cutter(
    recess: fasteners.HeadRecess,
    *,
    normal: tuple[float, float],
    mouth: float,
    x: float,
    y: float,
    z0: float,
    extra: float = 0.2,
):
    """The solid that cuts one head recess into a part (ADR-0018).

    The pocket opens into the part's outer face at ``z0`` -- the material lies
    at ``z > z0`` -- and runs ``recess.depth`` deep, so the head seats that far
    below the face. On one side the ceiling lifts back to the face at
    ``recess.ramp_angle``, pointing **away** from the wall (along
    ``-normal``), so the print never bridges it and the driver reaches the
    head. ``mouth`` is the 45 degree chamfer at the mouth; ``extra`` is how far
    the cutter overshoots the face so the boolean leaves no skin.

    The cutter is built along +X, turned onto ``-normal`` and lifted to
    ``z0``, so ``(x, y)`` is the station's screw axis.
    """
    from utilities import cad_helpers as ch

    radius = recess.pocket_radius
    depth = recess.depth
    run = recess.ramp_run
    if radius <= 0.0 or depth <= 0.0 or run <= 0.0:
        raise ValueError("a head recess needs a positive pocket, depth and ramp")
    if mouth < 0.0:
        raise ValueError("a head recess mouth chamfer cannot be negative")

    # The pocket proper, plus the chamfered throat that opens it at the face.
    # Both overshoot the face by `extra` so the cut never leaves a skin.
    pocket = ch.capsule_prism(radius, run, -extra, depth)
    throat = ch.capsule_frustum(
        radius + mouth + extra,
        run,
        radius,
        run,
        -extra,
        mouth,
    )
    cutter = ch.union(pocket, throat)
    # The ramp: above the plane through the seat's wall-side edge at 45
    # degrees, the ceiling has lifted clear of the face, so the material there
    # belongs to the part, not the pocket.
    ramp = ch.half_space(
        (radius, 0.0, depth),
        (1.0, 0.0, 1.0),
        size=2.0 * recess.length + 10.0,
    )
    cutter = ch.cut(cutter, ramp)
    angle = math.degrees(math.atan2(-normal[1], -normal[0]))
    cutter = ch.rotate_z(cutter, angle)
    return ch.translate(cutter, x, y, z0)


__all__ = [
    "RAMP_ANGLE_DEG",
    "build_cutter",
    "edge_margin",
    "mouth_chamfer",
]
