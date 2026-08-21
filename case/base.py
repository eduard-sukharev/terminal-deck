"""Base shell generator.

The base holds the keyboard and SBC. Input: placed components and the resolved
:class:`~assemblies.assembly.EnclosureSize`. Output (CAD pass): base bottom
tray, base top deck with keyboard cutout, and the combined base assembly.

All dimensions derive from the enclosure size and the single wall-thickness
parameter.
"""

from __future__ import annotations

import math

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
        """Placements resting on the base floor, at or near z=0 (mm).

        The threshold is one wall thickness, not a bare epsilon: components
        raised onto the floor's stiffening ribs (``geometry.ribs.rib_height``,
        e.g. the SBC and USB hub) still sit at that elevation, well below
        anything mounted in the lid.
        """
        wall = self.config.wall_thickness
        return [p for p in self.assembly.placements if p.z_bounds()[0] <= wall + 1e-6]

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

    def _corner_standoff_outer_diameter(self) -> float:
        """Outer diameter of a corner deck-mount standoff boss (mm, M2.5)."""
        from utilities import fasteners

        screw = fasteners.screw("M2.5")
        sleeve = 1.2
        return screw.clearance + 2 * sleeve

    def _corner_positions(self) -> list[tuple[float, float]]:
        """Return the 4 deck-mount corner positions (mm, XY).

        Nominally inset 3 mm from the interior wall faces. A component
        mounting boss (e.g. the SBC, which sits hard against a corner) can
        land right on top of that nominal spot, so each corner is nudged
        further inward along its diagonal until it clears every base-floor
        boss by at least one wall thickness of material — otherwise the two
        bosses fuse into one oversized, off-shape blob and their pilot bores
        merge into a single ragged hole neither screw seats in correctly —
        and until it clears every base-floor component's footprint outright:
        a standoff runs the full height up to the deck, so if its XY lands
        inside a board's outline (the SBC and USB hub both occupy a rear
        corner) it punches straight through the board regardless of Z.
        """
        size = self.size()
        wall = self.config.wall_thickness
        inset = 3.0
        half_iw = (size.width - 2 * wall) / 2
        half_id = (size.depth - 2 * wall) / 2
        standoff_radius = self._corner_standoff_outer_diameter() / 2
        margin = wall

        base_placements = self._base_placements()
        other_bosses = self.assembly.bosses(base_placements)

        def conflicts(cx: float, cy: float) -> bool:
            if any(
                math.hypot(cx - bx, cy - by)
                < standoff_radius + spec.outer_diameter / 2 + margin
                for bx, by, spec in other_bosses
            ):
                return True
            for placement in base_placements:
                x0, y0, x1, y1 = placement.box
                nx = min(max(cx, x0 - margin), x1 + margin)
                ny = min(max(cy, y0 - margin), y1 + margin)
                if math.hypot(cx - nx, cy - ny) < standoff_radius:
                    return True
            return False

        positions = []
        for sx, sy in ((1, 1), (-1, 1), (-1, -1), (1, -1)):
            shift = 0.0
            max_shift = min(half_iw, half_id) - inset
            while True:
                cx = sx * (half_iw - inset - shift)
                cy = sy * (half_id - inset - shift)
                if not conflicts(cx, cy) or shift >= max_shift:
                    break
                shift += 0.5
            positions.append((cx, cy))
        return positions

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

        # Mounting bosses for base-floor components.
        interior_w = size.width - 2 * wall
        interior_d = size.depth - 2 * wall
        base_placements = self._base_placements()
        mounting_bosses = self.assembly.bosses(base_placements)
        features = [boss.build(spec, x, y) for x, y, spec in mounting_bosses]

        # 4 corner standoff bosses for the deck (M2.5).
        screw = fasteners.screw("M2.5")
        boss_od = self._corner_standoff_outer_diameter()
        corner_positions = self._corner_positions()
        for cx, cy in corner_positions:
            standoff = cq_helpers.cylinder_centered(boss_od, dl)
            standoff = cq_helpers.translate(standoff, cx, cy, dl / 2.0)
            bore = cq_helpers.cylinder_centered(screw.pilot_hole, dl + 1.0)
            bore = cq_helpers.translate(bore, cx, cy, dl / 2.0)
            features.append(standoff.cut(bore))

        # Stiffening ribs, kept clear of every boss above: a rib crossing a
        # boss's bore would plug the screw hole with rib material once
        # unioned into the shell.
        rspec = ribs.rib_layout(
            interior_w, interior_d, wall, rib_height=ribs.rib_height(wall)
        )
        rib_solids = ribs.build(rspec, interior_w, interior_d)
        boss_keepouts = [(x, y, spec.outer_diameter) for x, y, spec in mounting_bosses]
        boss_keepouts += [(cx, cy, boss_od) for cx, cy in corner_positions]
        for bx, by, diameter in boss_keepouts:
            clearance_cyl = cq_helpers.cylinder_centered(diameter + wall, rspec.height)
            clearance_cyl = cq_helpers.translate(clearance_cyl, bx, by, rspec.height / 2.0)
            rib_solids = [rib.cut(clearance_cyl) for rib in rib_solids]
        features.extend(rib_solids)

        if features:
            fused = features[0]
            for part in features[1:]:
                fused = fused.union(part)
            body = body.union(fused)

        # Vent slots through the rear wall, skipping any slat that would
        # land inside a rear-wall connector cutout — left in, a vent slat
        # interleaved with a cutout is cut on both sides down to a sliver:
        # unsupported, brittle, and often too thin to print at all.
        rear_cutouts = [
            c for c in self.cutouts()
            if c["direction"][1] < 0 and abs(c["direction"][1]) >= abs(c["direction"][0])
        ]
        vent_keepouts = tuple(
            (
                c["x"] - c["width"] / 2 - config.corners.cutout_chamfer,
                c["x"] + c["width"] / 2 + config.corners.cutout_chamfer,
            )
            for c in rear_cutouts
        )
        vspec = vents.vent_slots(interior_w, dl - wall, keepouts=vent_keepouts)
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
