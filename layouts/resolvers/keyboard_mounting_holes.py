"""KeyboardMountingHoles resolver: computes mounting hole positions from layout.

Places two holes on the left (between row 0-1 and row 2-3) and two on the
right, aligned with edge switches and preferring gaps near wide keys (>1u).
"""

from __future__ import annotations

from typing import Any

from layouts.composer import ConstraintResolver, ResolverResult
from layouts.constraints import KeyboardMountingHoles
from keyboard.geometry.mounting import generate_mounting_holes


class KeyboardMountingHolesResolver:
    """Compute mounting hole positions from the keyboard layout."""

    kind = "keyboard_mounting_holes"

    def resolve(
        self,
        constraint: KeyboardMountingHoles,
        components: dict[str, Any],
        current: dict[str, Any],
        config: Any,
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
        plate.set_mounting_holes(hole_list)

        desc = "; ".join(f"({h.x:.1f}, {h.y:.1f})" for h in holes)
        return ResolverResult(
            True,
            {},
            f"{constraint.subject} mounting holes: {desc}",
        )


__all__ = ["KeyboardMountingHolesResolver"]
