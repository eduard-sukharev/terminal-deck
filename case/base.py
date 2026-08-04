"""Base shell generator.

The base holds the keyboard and SBC. Input: placed components and the resolved
:class:`~assemblies.assembly.EnclosureSize`. Output (CAD pass): base shell,
walls, bosses, ribs, vent slots, and connector cutouts.

All dimensions derive from the enclosure size and the single wall-thickness
parameter.
"""

from __future__ import annotations

from assemblies.assembly import Assembly, EnclosureSize
from components.hinge import Hinge
from utilities.config_loader import Config


class Base:
    """Base half of the clamshell case."""

    def __init__(
        self,
        assembly: Assembly,
        config: Config,
        hinge: Hinge | None = None,
    ) -> None:
        self.assembly = assembly
        self.config = config
        self.hinge = hinge

    def size(self) -> EnclosureSize:
        """Overall base envelope (mm)."""
        return self.assembly.enclosure_size()

    def interior_dimensions(self) -> tuple[float, float, float]:
        """Interior width/depth/height of the base cavity (mm)."""
        size = self.size()
        wall = self.config.wall_thickness
        return (
            size.width - 2 * wall,
            size.depth - 2 * wall,
            size.height - 2 * wall,
        )

    def bosses(self) -> list[tuple[float, float, object]]:
        """Bosses placed on the base floor (mm, world frame)."""
        return self.assembly.bosses()

    def cutouts(self) -> list[dict]:
        """Shell openings required by connectors exposed on the base (mm)."""
        return self.assembly.connector_cutouts()

    def build(self):
        """Generate the base shell solid.

        Builds the open-top tray that holds the keyboard and SBC: the shell
        envelope, mounting bosses, floor ribs, rear-wall vents, and connector
        cutouts. All dimensions derive from the enclosure size and the single
        wall-thickness parameter.

        Returns
        -------
        cadquery.Workplane
            The base shell with walls, bosses, ribs, vents, and cutouts.
        """
        from geometry import boss, cutouts, fillet, ribs, shell, vents
        from utilities import cq_helpers

        cq_helpers.require_cq()
        config = self.config
        wall = config.wall_thickness
        clearance = config.clearance.shell
        size = self.size()

        # Base cavity top: the tallest base-floor component plus clearance.
        # Lid components (display/driver) stack above in the lid pass.
        base_placements = [p for p in self.assembly.placements if p.z <= 1e-6]
        base_top = max(
            (p.z + p.component.size().height for p in base_placements), default=0.0
        ) + clearance
        # Outer tray box spans z in [-wall, base_top]; corner fillet first so
        # the shell keeps the outer envelope exactly (negative shell offset).
        outer = cq_helpers.box_centered(size.width, size.depth, base_top + wall)
        outer = cq_helpers.translate(outer, 0.0, 0.0, (base_top - wall) / 2.0)
        outer = fillet.fillet_corners(outer, config.corners.radius)
        body = shell.offset_shell(outer, wall)

        # Mounting bosses for base-floor components (from mounting holes) and
        # stiffening ribs across the base floor — fused into one compound so
        # a single boolean against the shell does all the work.
        interior_w = size.width - 2 * wall
        interior_d = size.depth - 2 * wall
        features = [boss.build(spec, x, y) for x, y, spec in self.assembly.bosses(base_placements)]
        rspec = ribs.rib_layout(interior_w, interior_d, wall)
        features.extend(ribs.build(rspec, interior_w, interior_d))
        if features:
            fused = features[0]
            for part in features[1:]:
                fused = fused.union(part)
            body = body.union(fused)

        # Vent slots through the rear wall (SBC cooling) — one compound cut.
        vspec = vents.vent_slots(interior_w, base_top - wall)
        slots = vents.build(vspec, wall)
        if slots:
            slots = cq_helpers.translate(
                slots, 0.0, -size.depth / 2 + wall / 2.0, base_top / 2.0
            )
            body = body.cut(slots)

        # Connector cutouts (external, reach-aware).
        body = cutouts.build(self.cutouts(), body, wall)
        return body
