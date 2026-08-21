"""Base shell generator.

The base holds the keyboard and SBC. Input: placed components and the resolved
:class:`~assemblies.assembly.EnclosureSize`. Output (CAD pass): base bottom
tray, base top deck with keyboard cutout, and the combined base assembly.

All dimensions derive from the enclosure size and the single wall-thickness
parameter.
"""

from __future__ import annotations

from assemblies.assembly import Assembly, EnclosureSize
from components.base import Component
from components.hinge import Hinge
from utilities.config_loader import Config


class Base:
    """Base half of the clamshell case.

    Parameters
    ----------
    assembly : Assembly
        The resolved assembly with all placements.
    config : Config
        Build configuration.
    keyboard : Component or None
        The keyboard component (needed to compute the deck level from the
        plate top). If None, the deck level falls back to the tallest
        base-floor component + clearance.
    hinge : Hinge or None
        Hinge part (for clearance checks).
    """

    def __init__(
        self,
        assembly: Assembly,
        config: Config,
        keyboard: Component | None = None,
        hinge: Hinge | None = None,
    ) -> None:
        self.assembly = assembly
        self.config = config
        self.keyboard = keyboard
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

    def _base_placements(self) -> list:
        """Placements on the base floor (z ≈ 0)."""
        return [p for p in self.assembly.placements if p.z <= 1e-6]

    def _keyboard_placement(self):
        """Return the keyboard placement, or None."""
        if self.keyboard is None:
            return None
        for p in self.assembly.placements:
            if p.component is self.keyboard:
                return p
        return None

    def deck_level(self) -> float:
        """Height of the deck (base_top bottom face) above the floor (mm).

        The deck sits at the keyboard plate top: the plate is raised on
        standoffs, and the deck covers the cavity at that level. Keycaps
        protrude through the cutout above the deck.

        If no keyboard is present, falls back to the tallest base-floor
        component + clearance (the old open-top tray height).
        """
        kb_placement = self._keyboard_placement()
        if kb_placement is not None and hasattr(self.keyboard, "_plate_raise"):
            plate_raise = self.keyboard._plate_raise
            plate_thickness = self.keyboard._plate_thickness
            return kb_placement.z + plate_raise + plate_thickness
        base_placements = self._base_placements()
        return max(
            (p.z + p.component.size().height for p in base_placements),
            default=0.0,
        ) + self.config.clearance.shell

    def _corner_positions(self) -> list[tuple[float, float]]:
        """Return the 4 deck-mount corner positions (mm, XY).

        Inset 3 mm from the interior wall faces.
        """
        size = self.size()
        wall = self.config.wall_thickness
        inset = 3.0
        half_iw = (size.width - 2 * wall) / 2
        half_id = (size.depth - 2 * wall) / 2
        return [
            (half_iw - inset, half_id - inset),
            (-half_iw + inset, half_id - inset),
            (-half_iw + inset, -half_id + inset),
            (half_iw - inset, -half_id + inset),
        ]

    def build_bottom(self):
        """Generate the base bottom tray solid.

        An open-top tray (shelled at >Z) with the floor, walls, mounting
        bosses, ribs, vents, connector cutouts, and 4 corner standoff bosses
        that support the deck.

        Returns
        -------
        cadquery.Workplane
            The base bottom tray solid.
        """
        from geometry import boss, cutouts, fillet, ribs, shell, vents
        from utilities import cq_helpers, fasteners

        cq_helpers.require_cq()
        config = self.config
        wall = config.wall_thickness
        clearance = config.clearance.shell
        size = self.size()
        dl = self.deck_level()

        # Outer tray box from -wall to deck_level; corner fillet first so
        # the shell keeps the outer envelope exactly (negative shell offset).
        outer = cq_helpers.box_centered(size.width, size.depth, dl + wall)
        outer = cq_helpers.translate(outer, 0.0, 0.0, (dl - wall) / 2.0)
        outer = fillet.fillet_corners(outer, config.corners.radius)
        body = outer.faces(">Z").shell(-wall)

        # Mounting bosses for base-floor components and stiffening ribs.
        interior_w = size.width - 2 * wall
        interior_d = size.depth - 2 * wall
        base_placements = self._base_placements()
        features = [
            boss.build(spec, x, y)
            for x, y, spec in self.assembly.bosses(base_placements)
        ]
        rspec = ribs.rib_layout(interior_w, interior_d, wall, rib_height=wall * 1.0)
        features.extend(ribs.build(rspec, interior_w, interior_d))

        # 4 corner standoff bosses for the deck (M2.5).
        screw = fasteners.screw("M2.5")
        sleeve = 1.2
        boss_od = screw.clearance + 2 * sleeve
        for cx, cy in self._corner_positions():
            standoff = cq_helpers.cylinder_centered(boss_od, dl)
            standoff = cq_helpers.translate(standoff, cx, cy, dl / 2.0)
            bore = cq_helpers.cylinder_centered(screw.pilot_hole, dl + 1.0)
            bore = cq_helpers.translate(bore, cx, cy, dl / 2.0)
            features.append(standoff.cut(bore))

        if features:
            fused = features[0]
            for part in features[1:]:
                fused = fused.union(part)
            body = body.union(fused)

        # Vent slots through the rear wall.
        vspec = vents.vent_slots(interior_w, dl - wall)
        slots = vents.build(vspec, wall)
        if slots:
            slots = cq_helpers.translate(
                slots, 0.0, -size.depth / 2 + wall / 2.0, dl / 2.0
            )
            body = body.cut(slots)

        # Connector cutouts (external, reach-aware), beveled for plug lead-in.
        body = cutouts.build(
            self.cutouts(), body, wall, chamfer=config.corners.cutout_chamfer
        )
        return body

    def build_top(self):
        """Generate the base top deck solid.

        A flat plate covering the base cavity, with a keyboard cutout and
        4 corner M2.5 clearance holes. The deck sits on the tray rim at
        ``deck_level``; its top face is at ``deck_level + wall``.

        Returns
        -------
        cadquery.Workplane
            The base top deck solid, or an empty Workplane if no keyboard
            is configured.
        """
        from geometry import fillet
        from utilities import cq_helpers, fasteners

        cq_helpers.require_cq()
        config = self.config
        wall = config.wall_thickness
        clearance = config.clearance.shell
        size = self.size()
        dl = self.deck_level()

        # Deck plate: full footprint, wall thick, bottom face on the rim.
        deck = cq_helpers.box_centered(size.width, size.depth, wall)
        deck = cq_helpers.translate(deck, 0.0, 0.0, dl + wall / 2.0)
        deck = fillet.fillet_corners(deck, config.corners.radius)

        # Keyboard cutout centered at the keyboard placement.
        kb_placement = self._keyboard_placement()
        if kb_placement is not None:
            kb_size = kb_placement.component.size()
            cut_w = kb_size.width + 2 * clearance
            cut_d = kb_size.depth + 2 * clearance
            cutout = cq_helpers.box_centered(cut_w, cut_d, wall + 0.1)
            cutout = cq_helpers.translate(
                cutout, kb_placement.x, kb_placement.y, dl + wall / 2.0
            )
            deck = deck.cut(cutout)

        # 4 corner M2.5 clearance holes for deck screws.
        screw = fasteners.screw("M2.5")
        for cx, cy in self._corner_positions():
            hole = cq_helpers.cylinder_centered(
                screw.clearance, wall + 2 * clearance
            )
            hole = cq_helpers.translate(
                hole, cx, cy, dl + wall / 2.0
            )
            deck = deck.cut(hole)

        return deck
