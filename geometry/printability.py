"""Print orientation, bed face and overhang checks (ADR 0003).

Every Section declares how it prints as the direction from the part toward the
bed (``PrintOrientation.normal``; ``(0, 0, -1)`` is floor-down). The bed face
is a planar face on the part's surface facing that way. A part with none can't
be printed without a bespoke setup (HARD). Faces beyond 45 degrees from
vertical facing the bed need support (SOFT, reported only).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from utilities import cad_helpers

#: A face's plane may sit this far (mm) from the part's extreme to count as the bed.
_PLANE_TOL = 1.0e-3
#: A face normal may deviate this far (cosine) from the bed normal to count as planar-down.
_NORMAL_TOL = 1.0e-4
#: Overhang limit, degrees from vertical.
OVERHANG_LIMIT_DEG = 45.0


@dataclass(frozen=True)
class PrintOrientation:
    """Direction from the part toward the bed (unit vector)."""

    normal: tuple[float, float, float]

    def __post_init__(self) -> None:
        length = math.sqrt(sum(c * c for c in self.normal))
        if abs(length - 1.0) > 1e-6:
            raise ValueError("print orientation normal must be a unit vector")


#: Printed as modelled, lowest face on the bed.
BED_DOWN = PrintOrientation((0.0, 0.0, -1.0))


@dataclass(frozen=True)
class OverhangFace:
    """A face needing support: its area (mm^2) and angle from vertical."""

    area: float
    angle_from_vertical: float
    center: tuple[float, float, float]


def _dot(a, b) -> float:
    return sum(x * y for x, y in zip(a, b))


def _extreme(shape, normal) -> float:
    """Furthest extent of the part along ``normal`` (mm)."""
    box = cad_helpers.bounding_box(shape)
    corners = [
        (x, y, z)
        for x in (box.xmin, box.xmax) for y in (box.ymin, box.ymax) for z in (box.zmin, box.zmax)
    ]
    return max(_dot(c, normal) for c in corners)


def bed_face_area(shape, orientation: PrintOrientation) -> float:
    """Total area (mm^2) of planar faces lying flat on the bed.

    A face counts when its outward normal is the bed normal and its plane is
    the part's furthest extent that way.
    """
    n = orientation.normal
    extreme = _extreme(shape, n)
    area = 0.0
    for face in cad_helpers.faces(shape):
        if not cad_helpers.is_planar(face):
            continue
        fn = cad_helpers.face_normal(face)
        if _dot(fn, n) < 1.0 - _NORMAL_TOL:
            continue
        if abs(_dot(cad_helpers.face_center(face), n) - extreme) <= _PLANE_TOL:
            area += cad_helpers.face_area(face)
    return area


def check_bed_face(name: str, shape, orientation: PrintOrientation, min_area: float, report) -> None:
    """HARD: a planar face of at least ``min_area`` lies on the bed."""
    area = bed_face_area(shape, orientation)
    report.add(
        f"bed-face:{name}", area >= min_area,
        f"bed face {area:.0f} mm^2 (need >= {min_area:.0f}), "
        f"normal {tuple(round(c, 3) for c in orientation.normal)}",
    )


def overhang_faces(shape, orientation: PrintOrientation, limit_deg: float = OVERHANG_LIMIT_DEG):
    """Faces facing the bed more than ``limit_deg`` from vertical, largest first.

    The bed face itself is excluded. Curved faces are judged at the worst of a
    small grid of sample points.
    """
    n = orientation.normal
    extreme = _extreme(shape, n)
    limit = math.sin(math.radians(limit_deg)) + 1e-6
    found = []
    for face in cad_helpers.faces(shape):
        worst = max(_dot(fn, n) for fn in cad_helpers.face_sample_normals(face))
        if worst <= limit:
            continue
        if cad_helpers.is_planar(face) and abs(_dot(cad_helpers.face_center(face), n) - extreme) <= _PLANE_TOL:
            continue
        found.append(OverhangFace(
            area=cad_helpers.face_area(face),
            angle_from_vertical=math.degrees(math.asin(min(1.0, worst))),
            center=cad_helpers.face_center(face),
        ))
    return sorted(found, key=lambda f: -f.area)
