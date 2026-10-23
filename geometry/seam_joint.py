"""Screw joints that hold adjacent Sections of a part together (ADR 0003).

A joint is a square lug that straddles the Seam and grows from the part's
floor and the wall at the end of the Seam. A horizontal M2 screw runs along X
through it: a clearance bore on the left side, a heat-set insert pocket on
the right. The lug is added to the whole part before it is split, so each
Section receives its share, and both stay connected to the floor. A part with
three Sections gets its own pair of lugs on each Seam.

Sites are chosen clear of the components inside and of the structural
features (bosses, standoffs, columns, cradles) given as ``keepouts``.
"""

from __future__ import annotations

from dataclasses import dataclass

from utilities import cad_helpers, fasteners


@dataclass(frozen=True)
class JointSpec:
    """Calculated lug dimensions for one screw/insert pair (mm)."""

    size: float
    left_length: float
    right_length: float
    clearance_diameter: float
    insert_diameter: float
    insert_depth: float


def joint_spec(screw_size: str, sleeve: float = 1.2) -> JointSpec:
    """Lug dimensions from the fastener library.

    The lug is square, one insert bore plus a ``sleeve`` of material per
    side. The right side holds the insert; the left side holds the rest of the
    screw shank, so the tip reaches the insert's full depth.
    """
    screw = fasteners.screw(screw_size)
    insert = fasteners.heat_insert(screw_size)
    return JointSpec(
        size=insert.printed_hole_diameter + 2 * sleeve,
        left_length=screw.length - insert.depth,
        right_length=insert.depth + sleeve,
        clearance_diameter=screw.clearance,
        insert_diameter=insert.printed_hole_diameter,
        insert_depth=insert.depth,
    )


def _lug(
    spec: JointSpec, sx: float, sy: float, z: float, wall: float,
    backed: bool, grow: float = 0.0,
):
    """Lug box straddling the Seam at ``(sx, sy)``.

    A ``backed`` lug extends one ``wall`` toward its end wall; the bore stays
    centered on ``sy`` either way.

    ``grow`` inflates the box on every side (used for keep-out probes).
    """
    total = spec.left_length + spec.right_length
    # Start a little inside the floor so the union is a real overlap.
    lug = cad_helpers.box_centered(
        total + 2 * grow, spec.size + (wall if backed else 0.0) + 2 * grow, spec.size + 0.5 + 2 * grow
    )
    return cad_helpers.translate(
        lug,
        sx + (spec.right_length - spec.left_length) / 2.0,
        sy + ((wall if sy > 0 else -wall) / 2.0 if backed else 0.0),
        z - 0.25,
    )


def joint_sites(
    seam, depth: float, wall: float, spec: JointSpec
) -> list[tuple[float, float, bool]]:
    """Candidate ``(x, y, backed)`` joint sites, best first.

    The Seam's front and rear segments come first, each backed onto its end
    wall; then the remaining segments, front to rear, centered on the segment
    they straddle.
    """
    segments = seam.segments(depth)
    edge = depth / 2.0 - wall - spec.size / 2.0
    sites = [(segments[0][2], -edge, True), (segments[-1][2], edge, True)]
    sites += [(sx, (y0 + y1) / 2.0, False) for y0, y1, sx in segments[1:-1]]
    return sites


def lug_footprint(
    spec: JointSpec, sx: float, sy: float, wall: float, backed: bool
) -> tuple[float, float, float, float]:
    """``(x0, x1, y0, y1)`` of the lug box at a site (mm)."""
    total = spec.left_length + spec.right_length
    cx = sx + (spec.right_length - spec.left_length) / 2.0
    width = spec.size + (wall if backed else 0.0)
    cy = sy + ((wall if sy > 0 else -wall) / 2.0 if backed else 0.0)
    return (cx - total / 2.0, cx + total / 2.0, cy - width / 2.0, cy + width / 2.0)


def _overlaps(a: tuple[float, float, float, float], b: tuple[float, float, float, float], grow: float) -> bool:
    return a[0] < b[1] + grow and a[1] > b[0] - grow and a[2] < b[3] + grow and a[3] > b[2] - grow


def plan_joints(
    seam,
    depth: float,
    wall: float,
    spec: JointSpec,
    floor_top: float,
    obstacles=None,
    clearance: float = 0.0,
    count: int = 2,
    keepouts=(),
) -> list[tuple[float, float, bool]]:
    """Choose ``count`` joint sites on ``seam``.

    ``floor_top`` is the Z of the floor's inner face; the lugs sit on it. A
    site is skipped when its lug, grown by ``clearance``, would touch
    ``obstacles`` (a solid of whatever else occupies the interior) or an XY
    ``keepouts`` rectangle ``(x0, x1, y0, y1)`` (structural features). Raises
    ``ValueError`` if fewer than ``count`` free sites exist.
    """
    z = floor_top + spec.size / 2.0
    chosen = []
    for sx, sy, backed in joint_sites(seam, depth, wall, spec):
        if len(chosen) == count:
            break
        rect = lug_footprint(spec, sx, sy, wall, backed)
        if any(_overlaps(rect, k, clearance) for k in keepouts):
            continue
        if obstacles is not None:
            probe = _lug(spec, sx, sy, z, wall, backed, grow=clearance)
            if cad_helpers.volume_mm3(cad_helpers.intersect(probe, obstacles)) > 1e-6:
                continue
        chosen.append((sx, sy, backed))
    if len(chosen) < count:
        raise ValueError(
            f"only {len(chosen)} of {count} Seam joints fit clear of the interior"
        )
    return chosen


def add_joints(
    body,
    seam,
    depth: float,
    wall: float,
    spec: JointSpec,
    floor_top: float,
    obstacles=None,
    clearance: float = 0.0,
    count: int = 2,
    keepouts=(),
    sites=None,
):
    """Add ``count`` Seam-straddling lugs (with bores) to ``body``.

    The sites come from :meth:`plan_joints` unless given as ``sites`` (a
    caller that needs the footprints first plans, then adds).
    """
    z = floor_top + spec.size / 2.0
    chosen = sites if sites is not None else plan_joints(
        seam, depth, wall, spec, floor_top, obstacles, clearance, count, keepouts
    )
    for sx, sy, backed in chosen:
        body = cad_helpers.union(body, _lug(spec, sx, sy, z, wall, backed))
    for sx, sy, _ in chosen:
        left = cad_helpers.rotate_y(
            cad_helpers.cylinder_centered(spec.clearance_diameter, spec.left_length + 1.0), 90
        )
        left = cad_helpers.translate(left, sx - spec.left_length / 2.0 - 0.5, sy, z)
        right = cad_helpers.rotate_y(
            cad_helpers.cylinder_centered(spec.insert_diameter, spec.insert_depth), 90
        )
        right = cad_helpers.translate(right, sx + spec.insert_depth / 2.0, sy, z)
        body = cad_helpers.cut(body, left, right)
    return body
