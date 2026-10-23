"""KeyboardMountingHoles resolver: computes mounting hole positions from layout.

Places two holes on the left (between row 0-1 and row 2-3) and two on the
right, aligned with edge switches and preferring gaps near wide keys (>1u),
plus (ADR 0003) two holes per plate Section within one key unit of the plate
Seam, one in the upper rows and one in the lower rows. The Seam holes become
standoffs from the floor to the plate, so they have to clear whatever is buried
under the plate: the resolver vetoes any spot a floor-mounted component's solid
volume occupies, and reports a Section it cannot fit as a failure (HARD).
"""

from __future__ import annotations

from typing import Any

import math

from geometry.boss import boss_spec
from keyboard.geometry.mounting import generate_mounting_holes
from keyboard.geometry.seam import plate_seam
from keyboard.geometry.seam_holes import seam_holes
from layouts.base import volume_footprint, volume_z_span
from layouts.composer import ResolverResult
from layouts.constraints import KeyboardMountingHoles


def _buried_volumes(components: dict[str, Any], current: dict[str, Any], subject: str, z1: float):
    """``(x0, x1, y0, y1)`` of every other part's solid volume below ``z1`` (world)."""
    rects = []
    for role, placement in current.items():
        if role == subject:
            continue
        for vx, vy, vz, box in components[role].occupied_volumes():
            wx, wy, wz = placement.world_offset(vx, vy, vz)
            lo, hi = volume_z_span(placement, box, wz)
            if hi <= 0.0 or lo >= z1:
                continue
            w, d = volume_footprint(placement, box)
            rects.append((wx - w / 2, wx + w / 2, wy - d / 2, wy + d / 2))
    return rects


class KeyboardMountingHolesResolver:
    """Compute mounting hole positions from the keyboard layout."""

    kind = "keyboard_mounting_holes"

    def resolve(
        self,
        constraint: KeyboardMountingHoles,
        components: dict[str, Any],
        current: dict[str, Any],
        config: Any,
        context: dict[str, Any],
    ) -> ResolverResult:
        subj = components.get(constraint.subject)
        if subj is None:
            return ResolverResult(
                False, {},
                f"component {constraint.subject!r} not found",
            )

        plate = getattr(subj, "_plate", None)
        if plate is None:
            return ResolverResult(
                False, {},
                f"{constraint.subject!r} has no _plate attribute",
            )

        plate._ensure_model()
        model = plate._model
        layout = plate._layout
        if model is None or layout is None:
            return ResolverResult(
                False, {},
                f"{constraint.subject!r} model not loaded",
            )

        screw_d = constraint.screw_diameter or plate._screw_diameter

        holes = generate_mounting_holes(
            outline=model.plate_outline,
            screw_diameter=screw_d,
            switch_cutouts=model.switch_cutouts,
            stabilizer_cutouts=model.stabilizer_cutouts,
            keys=layout.keys,
            pitch=layout.pitch,
            centroid=layout._centroid(),
        )

        hole_list = [(h.x, h.y, h.diameter) for h in holes]

        # Seam holes: standoffs from the floor up to the plate. Vetoed where a
        # buried part's volume (plus the boss's own radius and a screw
        # clearance) stands in the way.
        kb_placement = current.get(constraint.subject)
        shortfall: list[str] = []
        seam_list: list[tuple[float, float, float]] = []
        if kb_placement is not None:
            raise_h = getattr(subj, "_plate_raise", 0.0)
            screw_size = subj.mounting_screw() or config.screws.standoff
            boss = boss_spec(
                config.wall_thickness, screw_size, screw_size,
                hole_diameter=screw_d, height=raise_h,
            )
            reach = boss.outer_diameter / 2.0 + config.clearance.screw
            rects = _buried_volumes(components, current, constraint.subject, raise_h)

            def blocked(x: float, y: float, _d: float) -> bool:
                wx, wy, _ = kb_placement.world_offset(x, y, 0.0)
                for x0, x1, y0, y1 in rects:
                    nx, ny = min(max(wx, x0), x1), min(max(wy, y0), y1)
                    if math.hypot(wx - nx, wy - ny) < reach:
                        return True
                return False

            xs = [p[0] for p in model.plate_outline]
            ys = [p[1] for p in model.plate_outline]
            found = seam_holes(
                model.switch_cutouts, model.stabilizer_cutouts, plate_seam(model),
                (min(xs), min(ys), max(xs), max(ys)), layout.pitch, screw_d, blocked,
            )
            have = {(h.section, h.rows) for h in found}
            shortfall = [
                f"{section} {rows}"
                for section in ("left", "right") for rows in ("lower", "upper")
                if (section, rows) not in have
            ]
            seam_list = [(h.x, h.y, h.diameter) for h in found]
        plate.set_mounting_holes(hole_list + seam_list)

        desc = "; ".join(f"({x:.1f}, {y:.1f})" for x, y, _ in hole_list + seam_list)
        if shortfall:
            return ResolverResult(
                False,
                {},
                f"{constraint.subject}: no free Seam standoff spot within one key unit "
                f"of the plate Seam for: {', '.join(shortfall)} (buried parts in the way)",
            )
        return ResolverResult(
            True,
            {},
            f"{constraint.subject} mounting holes: {desc}",
        )


__all__ = ["KeyboardMountingHolesResolver"]
