"""The band joints' screw head recesses (ADR-0018, ADR-0021).

Two profiles seat an ordinary button head in a counterbored pocket instead of
sinking a flat head flush:

* the **keyhole** (:class:`fasteners.HeadRecess`, ADR-0018) seats the head just
  below the part's outer face and lifts the pocket's ceiling back to that face
  on one side in a 45 degree ramp -- the lid's band joint. The ramp points
  **away** from the nearest wall, so the printed part never bridges a
  horizontal pocket ceiling (the seat ring is the only overhang, and 45 degrees
  is the print limit) and a driver still reaches the seated head from the side;
* the **deep cone** (:class:`DeepRecess`, ADR-0021) buries the head at the top
  of the Tray's floor cavity, one wall below the Parting plane, and reaches it
  down a rotationally symmetric cone that widens to the floor face. With no
  horizontal ceiling to bridge beyond the narrow seat ring, the driver enters
  straight along the axis and the part needs no ramp at all.

The keyhole's plan helpers are pure data so the joints can size their stations
and check them before any solid is built; only the cutters need a CAD library.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

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


@dataclass(frozen=True)
class DeepRecess:
    """A deep access cavity that buries an ordinary screw head (ADR-0021).

    The Tray's floor carries the heads of the screws that pull the Deck down.
    The head is buried at the top of a conical access cavity: its bearing face
    rests on the flat seat at ``z_seat``, with one wall of material between
    that seat and the Parting plane, and the driver reaches it down the cone,
    which widens to the part's floor face. The cone is rotationally symmetric,
    so it prints without a ramp and the driver enters straight along the screw
    axis.

    The seating geometry (``pocket_radius``, ``seat``, ``z_seat``) is shared
    by every station; the cone's mouth radius is per station, sized from the
    station's own column.

    Attributes
    ----------
    size : str
        Thread designation the recess is sized for.
    head : Head
        The head that seats in it.
    pocket_radius : float
        Head pocket half-width across the screw axis (mm).
    seat : float
        Width of the annular seat the head bears on (mm).
    z_seat : float
        Height of the seat (the cavity's ceiling) above the floor face (mm).
    """

    size: str
    head: fasteners.Head
    pocket_radius: float
    seat: float
    z_seat: float

    @property
    def pocket_diameter(self) -> float:
        """Head pocket width across the screw axis (mm)."""
        return 2.0 * self.pocket_radius

    @property
    def depth(self) -> float:
        """The cavity's run from the floor face to the seat (mm)."""
        return self.z_seat

    @property
    def z_neck(self) -> float:
        """Where the access cone meets the head pocket, above the floor (mm)."""
        return self.z_seat - self.head.depth

    def cone_angle(self, mouth_radius: float) -> float:
        """The access cone's half-angle from vertical (degrees).

        Raises ``ValueError`` when the mouth would be narrower than the head
        pocket -- a cone can only widen the cavity.
        """
        if mouth_radius < self.pocket_radius - 1e-9:
            raise ValueError(
                f"the access cone mouth Ø{2.0 * mouth_radius:.2f} is narrower "
                f"than the head pocket Ø{self.pocket_diameter:.2f}"
            )
        return math.degrees(
            math.atan2(mouth_radius - self.pocket_radius, self.z_neck)
        )


def deep_recess(
    size: str,
    kind: str = "button",
    *,
    fit: float = 0.2,
    z_seat: float,
) -> DeepRecess:
    """Size the deep conical recess that buries the ``kind`` head of ``size``.

    ``fit`` is the radial gap between the head and the head pocket wall, so the
    head drops in; ``z_seat`` is where the head's bearing face comes to rest
    above the floor face -- the caller derives it as one wall below the
    Parting plane (ADR-0021). The pocket is exactly the head's height, from
    ``z_seat`` down to :attr:`DeepRecess.z_neck`, and the cone runs from there
    to the floor.

    Raises ``ValueError`` when the fit would close the seat ring or when the
    pocket would not fit under the seat.
    """
    screw = fasteners.SCREWS[size]
    bolt = fasteners.HEADS[size][kind]
    pocket = bolt.diameter + 2.0 * fit
    seat = (pocket - screw.clearance) / 2.0
    if seat <= 0.0:
        raise ValueError(
            f"the {kind} {size} head needs a Ø{pocket:.2f} pocket but the "
            f"clearance hole is already Ø{screw.clearance:.2f}"
        )
    if z_seat <= bolt.depth:
        raise ValueError(
            f"a {bolt.depth:.2f} mm {kind} {size} head cannot be buried at "
            f"z {z_seat:.2f}: the pocket would reach through the floor face"
        )
    return DeepRecess(
        size=size,
        head=bolt,
        pocket_radius=pocket / 2.0,
        seat=seat,
        z_seat=z_seat,
    )


def build_deep_cutter(
    recess: DeepRecess,
    *,
    mouth_radius: float,
    x: float,
    y: float,
    z0: float = 0.0,
    extra: float = 0.2,
):
    """The solid that cuts one deep conical recess into a part (ADR-0021).

    The cavity opens into the part's floor face at ``z0`` (the material lies at
    ``z > z0``): a cone from ``mouth_radius`` at the face up to the head
    pocket, then the pocket cylinder to the seat at ``recess.z_seat`` -- the
    seat stays flat, so the head's bearing face comes to rest on it. The cone
    overshoots the face by ``extra`` (following its own slope) so the boolean
    leaves no skin; the pocket stops exactly at the seat.

    The cutter is axisymmetric and lifted to ``(x, y)``, so ``(x, y)`` is the
    station's screw axis.
    """
    from utilities import cad_helpers as ch

    radius = recess.pocket_radius
    z_neck = recess.z_neck
    if radius <= 0.0 or z_neck <= 0.0 or recess.z_seat <= 0.0:
        raise ValueError("a deep recess needs a positive pocket and seat height")
    if mouth_radius < radius - 1e-9:
        raise ValueError(
            f"the access cone mouth Ø{2.0 * mouth_radius:.2f} is narrower than "
            f"the head pocket Ø{recess.pocket_diameter:.2f}"
        )
    if extra < 0.0:
        raise ValueError("a deep recess overshoot cannot be negative")

    # The cone, continued through the floor face by `extra` so the boolean
    # trims a clean mouth.
    slope = (mouth_radius - radius) / z_neck
    bottom = mouth_radius + extra * slope
    bottom_z = z0 - extra
    cone_height = z_neck - bottom_z
    cone = ch.frustum_centered(2.0 * bottom, 2.0 * radius, cone_height)
    cone = ch.translate(cone, 0.0, 0.0, bottom_z + cone_height / 2.0)
    # The head pocket: a cylinder from the cone's neck to the seat, overlapped
    # into the cone so the two booleans share no coincident face, and ending
    # exactly on the seat.
    overlap = 0.1
    pocket_height = recess.z_seat - z_neck + overlap
    pocket = ch.cylinder_centered(2.0 * radius, pocket_height)
    pocket = ch.translate(
        pocket, 0.0, 0.0, z_neck - overlap + pocket_height / 2.0
    )
    return ch.translate(ch.union(cone, pocket), x, y, 0.0)


__all__ = [
    "RAMP_ANGLE_DEG",
    "DeepRecess",
    "build_cutter",
    "build_deep_cutter",
    "deep_recess",
    "edge_margin",
    "mouth_chamfer",
]
