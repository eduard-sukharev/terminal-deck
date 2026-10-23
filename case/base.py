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
from case.base_fastening import BaseFastening
from components.base import Component
from components.hinge import Hinge
from utilities.config_loader import Config


class Base(BaseFastening):
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
        #: Memo for the CAD-free fastening queries (see ``BaseFastening``).
        self._memo: dict = {}

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
        """Height of the deck (base_top bottom face) at the FRONT edge (mm).

        The deck sits at the keyboard plate top: the plate is raised on
        standoffs, and the deck covers the cavity at that level. Keycaps
        protrude through the cutout above the deck.

        With a sloped deck this is the wedge's low end — the plane's value at
        the front wall. It is found by taking the keyboard's plate-top height
        at the keyboard's own Y (the point the deck must actually meet) and
        back-projecting it down the slope to the front edge, so the deck and
        the keyboard mounted to it stay coincident whatever the slope.

        If no keyboard is present, falls back to the tallest base-floor
        component + clearance (the old open-top tray height).
        """
        kb_placement = self._keyboard_placement()
        if kb_placement is not None and hasattr(self.keyboard, "_plate_raise"):
            plate_raise = self.keyboard._plate_raise
            plate_thickness = self.keyboard._plate_thickness
            # Plate-top height above the keyboard's origin, foreshortened by
            # the keyboard's own tilt (it is tilted with the deck).
            stack = (plate_raise + plate_thickness) * math.cos(
                math.radians(kb_placement.tilt_x)
            )
            plate_top = kb_placement.z + stack
            front_y = self.size().depth / 2.0
            return plate_top - (front_y - kb_placement.y) * math.tan(
                math.radians(self.slope())
            )
        base_placements = self._base_placements()
        return max(
            (p.z + p.component.size().height for p in base_placements),
            default=0.0,
        ) + self.config.clearance.shell

    def slope(self) -> float:
        """Typing slope of the deck in degrees (0 = flat)."""
        deck = getattr(self.config, "deck", None)
        return deck.slope if deck is not None else 0.0

    def _deck_knee_y(self) -> float | None:
        """World Y of the keyboard's rear edge (mm), or ``None`` without one.

        Where the deck's slope ends: only the keyboard needs a rising floor
        (the typing tilt, and the pocket it opens up for the buried SBC) —
        the rear strip behind it holds ordinary floor-mounted parts (hub,
        battery, the SBC's own cable stubs) that get nothing from a sloped
        floor and would otherwise sit under a needlessly tall, tapering
        rear wall. :meth:`deck_level_at` flattens out at this Y; without a
        keyboard there is nothing to hinge a knee off, so the whole deck
        slopes for its full depth as it always did.
        """
        kb_placement = self._keyboard_placement()
        if kb_placement is None:
            return None
        return kb_placement.y - kb_placement.component.size().depth / 2.0

    def deck_level_at(self, y: float) -> float:
        """Deck bottom-face height at world ``y`` (mm).

        The deck is a plane tilted about X: it stays at :meth:`deck_level`
        along the front edge and rises toward the rear (-Y) — but only as
        far back as the keyboard's own rear edge (:meth:`_deck_knee_y`);
        behind that it holds at the height the slope reached there, flat
        and parallel to the floor, rather than continuing to rise all the
        way to the actual rear wall. This is the single source of the
        slope (and the knee) — every other piece of deck geometry (tray
        rim, corner standoffs, the deck slab, the hinge datum) asks this
        rather than re-deriving the tilt, so changing ``config.deck.slope``
        moves all of them together.
        """
        front_y = self.size().depth / 2.0
        knee_y = self._deck_knee_y()
        if knee_y is not None and y < knee_y:
            y = knee_y
        return self.deck_level() + (front_y - y) * math.tan(math.radians(self.slope()))

    def deck_rear_level(self) -> float:
        """Deck bottom-face height at the rear wall (mm) — the wedge's high
        end, i.e. the flattened height behind the keyboard's rear edge if
        there is a keyboard (see :meth:`_deck_knee_y`), or the true rear
        wall's own height on the old, unkneed slope otherwise."""
        return self.deck_level_at(-self.size().depth / 2.0)

    def deck_top_at(self, y: float) -> float:
        """Deck top-face height at world ``y`` (mm): the underside plus one wall."""
        return self.deck_level_at(y) + self.config.wall_thickness

    def visor_profile(self):
        """Visor height along Y that fills the wedge under the closed Lid.

        The Lid's flat underside lies on the plane through the Deck's highest
        point (the rear level), so the Visor is that plane minus the Deck top:
        full at the front, tapering to zero at the knee and flat behind it.
        """
        from geometry.visor import VisorProfile

        size = self.size()
        rear_y, front_y = -size.depth / 2.0, size.depth / 2.0
        knee_y = self._deck_knee_y()
        top = self.deck_top_at(rear_y)
        knots = [(rear_y, 0.0)]
        if knee_y is not None and self.slope() and rear_y < knee_y < front_y:
            knots.append((knee_y, 0.0))
        knots.append((front_y, top - self.deck_top_at(front_y)))
        return VisorProfile(tuple(knots))

    def closed_plane_z(self) -> float:
        """Height of the Lid's flat underside when closed (mm)."""
        return self.deck_top_at(-self.size().depth / 2.0)

    def hinge_axis_z(self) -> float:
        """Height of the hinge axis (mm): the closed Lid/Base interface plane.

        The one place the axis height is defined; the hinge builds around it
        and the closed-device checks measure against it.
        """
        return self.closed_plane_z()


    def _on_hinge_axis(self, solid):
        """Move an axis-at-origin hinge solid onto the hinge axis (rear edge)."""
        from utilities import cad_helpers

        return cad_helpers.translate(
            solid, 0.0, -self.size().depth / 2.0, self.hinge_axis_z()
        )

    def _mount_hinge(self, body):
        """Notch ``body`` where the Lid knuckles swing.

        The Base knuckle is its own part (ADR 0004), so nothing is fused on;
        without a hinge, ``body`` is returned unchanged.
        """
        from utilities import cad_helpers

        if self.hinge is None:
            return body
        return cad_helpers.cut(
            body, self._on_hinge_axis(self.hinge.build_base_notches(self.size().width))
        )

    def _slope_cut_tool(self, z_at_front: float, size, height: float):
        """A half-space solid lying above the deck-parallel plane through
        ``z_at_front`` (its height at the front edge), for cutting a solid
        down to the sloped profile.

        Built oversized in X/Y so it always overhangs the case footprint,
        then rotated about X by the slope angle. Returns a box whose bottom
        face is that plane and which extends ``height`` above it.
        """
        from utilities import cad_helpers

        slope = self.slope()
        # Long enough that the tilted box still covers the full footprint.
        pad = 4.0 * (size.width + size.depth)
        tool = cad_helpers.box_centered(size.width + pad, size.depth + pad, height)
        # Sit the box on z=0, tilt it about the origin, then lift the plane
        # to the requested front-edge height. Rotating about X by -slope
        # raises -Y (rear) and lowers +Y, matching deck_level_at.
        tool = cad_helpers.translate(tool, 0.0, 0.0, height / 2.0)
        if slope:
            tool = cad_helpers.rotate_x(tool, -slope)
        front_y = size.depth / 2.0
        # After the rotation the plane passes through the origin; shift it so
        # it passes through (y=front_y, z=z_at_front) as deck_level_at says.
        return cad_helpers.translate(
            tool, 0.0, 0.0,
            z_at_front + front_y * math.tan(math.radians(slope)),
        )

    def _deck_surface_tool(self, z_at_front: float, size, height: float):
        """Solid lying above the deck's actual underside surface, for
        cutting a solid down to that profile.

        Generalizes :meth:`_slope_cut_tool` for a deck that stops sloping
        behind the keyboard (:meth:`_deck_knee_y`) and continues flat from
        there back to the rear wall, at whatever height the slope reached
        at the knee: the union of the existing tilted half-space (clipped
        to the region at/in front of the knee, with a plain untilted box —
        the clip boundary is itself untilted, so it does not need to
        follow the slope) and a plain flat half-space behind it. The two
        clips are given a deliberate small overlap across the knee (not an
        exactly coincident face) — a union of solids that only touch along
        a zero-thickness face is a well-known OCC boolean-kernel crash
        (verified the hard way: base_bottom and base_top each built fine
        alone, but unioning them into the combined "base" target segfaulted
        the whole process, silently — no Python exception, nothing to
        catch, just gone). The overlap is provably inert: on the sloped
        side of the seam the flat clip's "above knee_z" volume is a subset
        of the sloped clip's own (lower there) volume, and vice versa on
        the flat side, so which one "wins" in the sliver never changes the
        actual boundary. Falls back to the plain :meth:`_slope_cut_tool`
        when there is no keyboard to hinge a knee off, or the deck is flat
        to begin with.
        """
        from utilities import cad_helpers

        knee_y = self._deck_knee_y()
        if knee_y is None or not self.slope():
            return self._slope_cut_tool(z_at_front, size, height)

        front_y = size.depth / 2.0
        # Matches deck_level_at's own sign: height rises toward the rear
        # (-Y), so a knee further back (more negative knee_y, larger
        # front_y - knee_y) means a *higher* knee_z, not lower.
        knee_z = z_at_front + (front_y - knee_y) * math.tan(math.radians(self.slope()))

        pad = 4.0 * (size.width + size.depth)
        reach = 1.0e3  # generous Z/Y reach without the numerical fragility of 1e5
        overlap = 1.0  # mm of deliberate overlap across the knee seam, see above

        sloped = self._slope_cut_tool(z_at_front, size, height)
        front_clip = cad_helpers.box_centered(size.width + pad, reach, reach)
        front_clip = cad_helpers.translate(
            front_clip, 0.0, knee_y - overlap + reach / 2.0, 0.0
        )
        sloped = cad_helpers.intersect(sloped, front_clip)

        flat = cad_helpers.box_centered(size.width + pad, reach, height)
        flat = cad_helpers.translate(
            flat, 0.0, knee_y + overlap - reach / 2.0, knee_z + height / 2.0
        )

        return cad_helpers.union(sloped, flat)

    def foot_positions(self) -> list[tuple[float, float]]:
        """Centers of the four rubber-foot recesses (config-derived)."""
        size = self.size()
        feet = self.config.feet
        hx = size.width / 2.0 - feet.inset_x
        hy = size.depth / 2.0 - feet.inset_y
        return [(sx * hx, sy * hy) for sx in (-1, 1) for sy in (-1, 1)]

    def all_bosses(self) -> list[tuple[float, float, float, float, Component | None]]:
        """Every boss on the base floor (mm, world frame), CAD-free.

        Each entry is ``(x, y, outer_diameter, height, owner)``: component
        mounting bosses (``owner`` the component the boss supports — a
        mounting boss legitimately touches/overlaps the part it holds up, so
        callers should skip that pair) and the Deck columns (``owner``
        ``None`` — a column belongs to no single component and should be
        checked against all of them).

        Bosses are case-build-time geometry (see :meth:`build_bottom`) —
        never themselves placed components, so the ordinary collision
        system (which compares placed components against each other) never
        sees them. This is what feeds
        :func:`utilities.validation.check_boss_collisions`, which closes
        that gap.
        """
        result: list[tuple[float, float, float, float, Component | None]] = [
            (bx, by, spec.outer_diameter, spec.height, owner)
            for bx, by, spec, owner in self.component_boss_specs()
        ]
        for col in self.columns():
            result.append((col.x, col.y, col.outer_diameter, col.height, None))
        return result

    def well_rim_height(self) -> float:
        """Height of the Well rim above the Deck top (mm); 0 without a keyboard."""
        from geometry import well

        if self.keyboard is None:
            return 0.0
        return well.rim_height(
            self.keyboard.switch_top_height,
            self.config.wall_thickness,
            self.config.well.switch_margin,
        )

    # -- Shell ------------------------------------------------------------------

    def _shell_blank(self):
        """The closed Base shell with no features: floor, walls and Deck slab.

        Floor outer face at ``z = -wall``, inner face at 0; the walls run up to
        the sloped Deck underside and the slab above it is one wall thick.
        The Tray and the Deck are this solid cut at the Parting plane.
        """
        from geometry import fillet
        from utilities import cad_helpers

        key = "shell_blank"
        if key in self._memo:
            return self._memo[key]
        config = self.config
        wall = config.wall_thickness
        size = self.size()
        dl = self.deck_level()
        rear_dl = self.deck_rear_level()
        height = rear_dl + 4 * wall
        outer = cad_helpers.box_centered(size.width, size.depth, height)
        outer = cad_helpers.translate(outer, 0.0, 0.0, height / 2.0 - wall)
        outer = fillet.fillet_corners(outer, config.corners.radius)
        outer = cad_helpers.cut(outer, self._deck_surface_tool(dl + wall, size, height))

        cavity = cad_helpers.box_centered(size.width - 2 * wall, size.depth - 2 * wall, height)
        cavity = cad_helpers.translate(cavity, 0.0, 0.0, height / 2.0)
        cavity = fillet.fillet_corners(cavity, max(config.corners.radius - wall, 0.0))
        cavity = cad_helpers.cut(cavity, self._deck_surface_tool(dl, size, height))
        blank = cad_helpers.cut(outer, cavity)
        self._memo[key] = blank
        return blank

    def _above_parting(self, z: float, below: bool):
        """A slab covering everything below (or above) height ``z``."""
        from utilities import cad_helpers

        size = self.size()
        reach = 4.0 * (size.width + size.depth)
        box = cad_helpers.box_centered(size.width + reach, size.depth + reach, reach)
        return cad_helpers.translate(box, 0.0, 0.0, z + (-1 if below else 1) * reach / 2.0)

    def _boss_with_hull(self, spec, x: float, y: float, bore: bool = True):
        """A boss at ``(x, y)``, fused into the wall beside it when Merged."""
        from geometry import boss, merged_boss
        from utilities import cad_helpers

        wall = self.config.wall_thickness
        solid = boss.build(spec, x, y, bore=bore)
        walls = merged_boss.merge_walls(
            x, y, spec.outer_diameter / 2.0, self.wall_bounds(), wall, self.config.merged_boss
        )
        if walls:
            hull = merged_boss.build_hull(
                x, y, spec.outer_diameter / 2.0, spec.height, walls, self.wall_bounds(), wall / 2.0
            )
            solid = cad_helpers.union(solid, hull)
            if bore:
                hole = cad_helpers.cylinder_centered(spec.hole_diameter, spec.height)
                solid = cad_helpers.cut(solid, cad_helpers.translate(hole, x, y, spec.height / 2.0))
        return solid

    def rib_spec(self):
        """Floor rib layout, clear of the Seam bands and lugs (ADR 0003)."""
        from geometry import ribs

        key = "rib_spec"
        if key not in self._memo:
            wall = self.config.wall_thickness
            b = self.wall_bounds()
            self._memo[key] = ribs.rib_layout(
                b.x1 - b.x0, b.y1 - b.y0, wall,
                rib_height=ribs.rib_height(wall), avoid=self.rib_avoid(),
            )
        return self._memo[key]

    def vent_spec(self):
        """Rear-wall vent slots, clear of the Seam bands, columns and cutouts."""
        from geometry import vents

        key = "vent_spec"
        if key not in self._memo:
            b = self.wall_bounds()
            self._memo[key] = vents.vent_slots(
                b.x1 - b.x0, self.deck_rear_level() - self.config.wall_thickness,
                keepouts=self.vent_keepout_ranges(),
            )
        return self._memo[key]

    def seam_features(self):
        """Every structural feature, for the Seam clearance check (CAD-free)."""
        rib, vent = self.rib_spec(), self.vent_spec()
        return self.structural_features(
            ribs=rib.positions, rib_thickness=rib.thickness,
            vents=vent.positions, vent_width=vent.slot_width,
        )

    def fastening_report(self, report) -> None:
        """Run the Base's data-level fastening checks onto ``report`` (HARD)."""
        from utilities.validation import (
            check_deck_screw, check_deck_seam_screws, check_screw_heads_clear_of_feet,
            check_seam_clearance,
        )

        columns = self.columns()
        deck = self._split("deck")
        if deck is not None:
            check_deck_seam_screws(
                [c.x for c in columns], deck.seams()[0].x,
                self.config.deck.seam_screw_reach, report,
            )
        check_deck_screw(self.config.screws.deck, self.deck_screw_grip(), report)
        feet = [(fx, fy, self.config.feet.diameter / 2.0) for fx, fy in self.foot_positions()]
        report.add(
            "parting-plane-in-walls", self.parting_height() < self.deck_level(),
            f"Parting plane {self.parting_height():.2f} mm vs front wall {self.deck_level():.2f} mm",
        )
        too_short = [c for c in columns if c.deck_boss_height < c.insert_depth + self.config.material.minimum_feature]
        report.add(
            "deck-boss-holds-insert", not too_short,
            "every Deck boss is tall enough for its heat-set insert" if not too_short
            else f"{len(too_short)} Deck boss(es) shorter than the insert plus a printable floor",
        )
        check_screw_heads_clear_of_feet(
            [(c.x, c.y, c.counterbore_diameter / 2.0) for c in columns], feet, report
        )
        check_seam_clearance(self.seam_bands(), self.seam_features(), report)
        self.knuckle_report(report)

    def knuckle_report(self, report) -> None:
        """Base knuckle mounting checks: HARD that it is screwed down at all, HARD
        that every Deck Section has a screw into its rear skirt, SOFT for each
        Tray Section without a floor screw (the Deck columns hold it instead)."""
        sites = self.knuckle_screw_sites()
        deck = self.deck_knuckle_sites()
        total = sum(len(v) for v in sites.values()) + sum(len(v) for v in deck.values())
        report.add(
            "knuckle-screwed-to-tray", total >= 1,
            f"{sum(len(v) for v in sites.values())} floor screw(s) into the Tray ("
            + ", ".join(f"{n} {len(p)}" for n, p in sites.items())
            + f") and {sum(len(v) for v in deck.values())} into the Deck skirt ("
            + ", ".join(f"{n} {len(p)}" for n, p in deck.items()) + ")",
        )
        if deck:
            bare = [n for n, pts in deck.items() if not pts]
            report.add(
                "knuckle-screwed-to-deck", not bare,
                "every Deck Section has a knuckle screw" if not bare
                else f"no knuckle screw into the Deck Section(s): {', '.join(bare)}",
            )

    # -- Tray -------------------------------------------------------------------

    def build_bottom(self):
        """Generate the Tray: floor, walls up to the Parting plane, and fittings.

        Mounting bosses, Deck columns (counterbored from the floor, M3
        clearance bore), battery cradles, stiffening ribs laid out between the
        Seam bands, vent slots, connector cutouts, three-Section Seam lugs and
        the rubber-foot recesses.

        Returns
        -------
        Shape
            The whole Tray, untreated: ``main`` splits it into Sections at its
            Seams and relieves the concave joints on each Section (OCC will not
            split a part whose joints are already chamfered).
        """
        from components.battery import Battery
        from geometry import cradle, cutouts, ribs, seam_joint, vents
        from utilities import cad_helpers, fasteners

        cad_helpers.require_cad()
        config = self.config
        wall = config.wall_thickness
        size = self.size()
        zp = self.parting_height()
        interior_w = size.width - 2 * wall
        interior_d = size.depth - 2 * wall

        body = cad_helpers.intersect(self._shell_blank(), self._above_parting(zp, below=True))

        features = [
            self._boss_with_hull(spec, x, y) for x, y, spec, _ in self.component_boss_specs()
        ]
        # Deck columns: posts up to the Parting plane. The bores are cut after
        # the union because they pass through the floor.
        for col in self.columns():
            features.append(self._boss_with_hull(col.spec, col.x, col.y, bore=False))

        # Battery cell cradles: printed floor saddles that key each cell's
        # lateral position (geometry.cradle) — the pack isn't fastened like a
        # bossed component. Scanned from the placements directly, not from
        # ``_base_placements`` (see that method's z-bounds filter), and exempt
        # from merging: they are solid blocks.
        for p in self.assembly.placements:
            if not isinstance(p.component, Battery):
                continue
            battery = p.component
            spec = cradle.CradleSpec(
                diameter=battery.cell_diameter, rest_height=p.z,
                height=battery.cradle_height, width=wall * 3,
            )
            saddle = cradle.build(spec)
            if p.rotation:
                saddle = cad_helpers.rotate_z(saddle, p.rotation)
            # Two saddles per cell, toward each end along the cell's own axis:
            # a cylinder on one narrow saddle rocks about that line.
            end_offset = max(0.0, battery.cell_length / 2.0 - spec.width / 2.0)
            for cx, cy in battery._cell_centers():
                for cy_end in (cy - end_offset, cy + end_offset):
                    wx, wy, _ = p.world_offset(cx, cy_end, 0.0)
                    features.append(cad_helpers.translate(saddle, wx, wy, 0.0))

        # Base knuckle screw bosses: M3 insert bosses merged into the rear wall.
        kspec = self.knuckle_boss_spec()
        for pts in self.knuckle_screw_sites().values():
            for kx, ky in pts:
                features.append(self._boss_with_hull(kspec, kx, ky, bore=False))

        # Stiffening ribs, kept clear of every boss: a rib crossing a bore
        # would plug the screw hole. Cradles are deliberately not cleared (no
        # bore to plug).
        rspec = self.rib_spec()
        rib_solids = ribs.build(rspec, interior_w, interior_d)
        keepouts = [(x, y, spec.base_diameter) for x, y, spec, _ in self.component_boss_specs()]
        keepouts += [(c.x, c.y, c.base_diameter) for c in self.columns()]
        keepouts += [
            (kx, ky, kspec.base_diameter)
            for pts in self.knuckle_screw_sites().values() for kx, ky in pts
        ]
        for bx, by, diameter in keepouts:
            clearance_cyl = cad_helpers.cylinder_centered(diameter + wall, rspec.height)
            clearance_cyl = cad_helpers.translate(clearance_cyl, bx, by, rspec.height / 2.0)
            rib_solids = [cad_helpers.cut(rib, clearance_cyl) for rib in rib_solids]
        features.extend(rib_solids)

        if features:
            body = cad_helpers.union(body, cad_helpers.union(features[0], *features[1:]))

        # Deck column bores: counterbore from the floor's underside for the
        # screw head, then the clearance bore the rest of the way up.
        for col in self.columns():
            cb = cad_helpers.cylinder_centered(col.counterbore_diameter, col.counterbore_depth + 0.5)
            cb = cad_helpers.translate(cb, col.x, col.y, -wall - 0.5 + (col.counterbore_depth + 0.5) / 2.0)
            through = cad_helpers.cylinder_centered(col.bore_diameter, zp + wall + 1.0)
            through = cad_helpers.translate(through, col.x, col.y, (zp - wall) / 2.0)
            body = cad_helpers.cut(body, cb, through)

        # Insert bores of the knuckle bosses.
        insert = fasteners.heat_insert("M3")
        for pts in self.knuckle_screw_sites().values():
            for kx, ky in pts:
                bore = cad_helpers.cylinder_centered(insert.printed_hole_diameter, insert.depth)
                body = cad_helpers.cut(
                    body, cad_helpers.translate(bore, kx, ky, kspec.height - insert.depth / 2.0)
                )

        # Vents and connector cutouts through the walls.
        slots = vents.build(self.vent_spec(), wall)
        if slots:
            rear_dl = self.deck_rear_level()
            slots = cad_helpers.translate(slots, 0.0, -size.depth / 2 + wall / 2.0, rear_dl / 2.0)
            body = cad_helpers.cut(body, slots)
        body = cutouts.build(self.cutouts(), body, wall, chamfer=config.corners.cutout_chamfer)

        # Seam lugs: two per Seam, at the sites planned clear of everything.
        split = config.split.get("tray")
        if split is not None:
            spec = self._lug_spec()
            sites = self.tray_lug_sites()
            for i, seam in enumerate(split.seams()):
                body = seam_joint.add_joints(
                    body, seam, size.depth, wall, spec, floor_top=0.0,
                    sites=sites[f"tray:{i}"],
                )

        # Rubber-foot recesses in the floor's underside. Positions come from
        # config alone (foot_positions), never from boss positions.
        feet = config.feet
        for fx, fy in self.foot_positions():
            recess = cad_helpers.cylinder_centered(feet.diameter, 2 * feet.depth)
            body = cad_helpers.cut(body, cad_helpers.translate(recess, fx, fy, -wall))
        return body

    # -- Base knuckle -----------------------------------------------------------

    def knuckle_drop(self) -> float:
        """Hinge axis height above the Tray floor's outer face (mm)."""
        return self.hinge_axis_z() + self.config.wall_thickness

    def build_knuckle(self):
        """The Base knuckle part, in world position (ADR 0004).

        D-bar with the display cable tunnel, outer end cheeks, a web behind the
        rear face and a flange under the Tray floor, screwed from below into
        the Tray's knuckle bosses. Flange cuts clear the rubber feet and the
        Deck screw heads. Prints flange down.
        """
        from utilities import cad_helpers

        if self.hinge is None:
            raise ValueError("no hinge configured")
        size = self.size()
        rear_y = -size.depth / 2.0
        screws = tuple(
            (x, y - rear_y) for pts in self.knuckle_screw_sites().values() for x, y in pts
        )
        cuts = [
            (fx, fy - rear_y, self.config.feet.diameter / 2.0 + 0.5)
            for fx, fy in self.foot_positions()
        ]
        cuts += [
            (c.x, c.y - rear_y, c.counterbore_diameter / 2.0 + 0.5) for c in self.columns()
        ]
        side_screws = tuple(
            (x, z - self.hinge_axis_z())
            for pts in self.deck_knuckle_sites().values() for x, z in pts
        )
        part = self.hinge.build_base_part(
            size.width, self.knuckle_drop(), screws=screws, flange_cuts=tuple(cuts),
            side_screws=side_screws,
        )
        return cad_helpers.translate(part, 0.0, rear_y, self.hinge_axis_z())

    # -- Deck -------------------------------------------------------------------

    def build_top(self):
        """Generate the Deck: the Parting-plane skirt, the sloped slab and the Well.

        The Deck is the shell above the Parting plane: a skirt of wall from the
        plane up to the sloped underside, then the one-wall-thick slab with the
        keyboard opening and its Well rim, plus a heat-set-insert boss over each
        Tray column. It prints Parting face down, supports under the roof.

        Returns
        -------
        Shape
            The whole Deck, untreated; ``main`` splits it into two Sections at
            its Seam and relieves the concave joints on each.
        """
        from geometry import cutouts, fillet, well
        from utilities import cad_helpers, fasteners

        cad_helpers.require_cad()
        config = self.config
        wall = config.wall_thickness
        clearance = config.clearance.shell
        size = self.size()
        zp = self.parting_height()
        slope = self.slope()
        blank = self._shell_blank()
        deck = cad_helpers.intersect(blank, self._above_parting(zp, below=False))
        blank_h = 4 * wall + self.deck_rear_level()
        footprint = cad_helpers.translate(
            fillet.fillet_corners(
                cad_helpers.box_centered(size.width, size.depth, blank_h), config.corners.radius
            ),
            0.0, 0.0, blank_h / 2.0,
        )

        # Deck bosses over the Tray columns, hanging from the slab's underside
        # down to the Parting plane, with the insert bore opening on that face.
        columns = self.columns()
        for col in columns:
            top = self.deck_level_at(col.y) + wall / 2.0
            height = top - zp
            boss_solid = cad_helpers.translate(
                cad_helpers.cylinder_centered(col.outer_diameter, height),
                col.x, col.y, zp + height / 2.0,
            )
            if col.walls:
                from geometry import merged_boss

                hull = merged_boss.build_hull(
                    col.x, col.y, col.outer_diameter / 2.0, height, col.walls,
                    self.wall_bounds(), wall / 2.0, z0=zp,
                )
                boss_solid = cad_helpers.union(boss_solid, hull)
            deck = cad_helpers.union(deck, boss_solid)

        kb_placement = self._keyboard_placement()
        if kb_placement is not None:
            kb_size = kb_placement.component.size()
            cut_w = kb_size.width + 2 * clearance
            cut_d = kb_size.depth + 2 * clearance
            cut_h = 4 * wall + self.deck_rear_level()
            pose = (kb_placement.x, kb_placement.y,
                    self.deck_level_at(kb_placement.y) + wall / 2.0)

            if self.well_rim_height() > 0.0:
                # Well rim: a wall-wide ring around the opening, tilted with the
                # slab (local z=0 is the slab's mid-plane), clipped to the case
                # footprint where the keyboard runs out to the edge.
                rim = well.build_rim(
                    cut_w, cut_d, wall, self.well_rim_height(), overlap=wall / 2.0
                )
                if slope:
                    rim = cad_helpers.rotate_x(rim, -slope)
                rim = cad_helpers.translate(rim, *pose)
                # Closed, the Lid's flat underside lies on closed_plane_z: a rim
                # taller than the Visor gap at its Y would thicken the device, so
                # the rim tapers away under that plane like the Visor does.
                ceiling_h = self.closed_plane_z()
                ceiling = cad_helpers.translate(
                    cad_helpers.box_centered(size.width, size.depth, ceiling_h),
                    0.0, 0.0, ceiling_h / 2.0,
                )
                rim = cad_helpers.intersect(rim, cad_helpers.intersect(footprint, ceiling))
                deck = cad_helpers.union(deck, rim)

            # Bored along the deck normal (tilted with the slab) so the opening
            # keeps its true width/depth in the deck's own plane.
            cutout = cad_helpers.box_centered(cut_w, cut_d, cut_h)
            if slope:
                cutout = cad_helpers.rotate_x(cutout, -slope)
            cutout = cad_helpers.translate(cutout, *pose)
            deck = cad_helpers.cut(deck, cutout)

        # Knuckle screw bosses on the rear skirt: a horizontal insert boss on a
        # solid block down to the Parting plane, so nothing overhangs.
        kspec = self.knuckle_boss_spec()
        insert = fasteners.heat_insert("M3")
        rear_in = self.wall_bounds().y0
        rear_out = rear_in - wall
        for kx, kz in (pt for pts in self.deck_knuckle_sites().values() for pt in pts):
            along_y = cad_helpers.rotate_x(cad_helpers.cylinder_centered(kspec.outer_diameter, kspec.height), 90)
            block = cad_helpers.box_centered(kspec.outer_diameter, kspec.height, kz - zp)
            boss_solid = cad_helpers.union(
                cad_helpers.translate(along_y, kx, rear_in + kspec.height / 2.0, kz),
                cad_helpers.translate(block, kx, rear_in + kspec.height / 2.0, (kz + zp) / 2.0),
            )
            deck = cad_helpers.union(deck, boss_solid)

        # Insert bores, opening on the Parting face.
        for col in columns:
            bore = cad_helpers.cylinder_centered(col.insert_diameter, col.insert_depth + 1.0)
            bore = cad_helpers.translate(bore, col.x, col.y, zp - 1.0 + (col.insert_depth + 1.0) / 2.0)
            deck = cad_helpers.cut(deck, bore)

        # Insert bores of the knuckle bosses (open to the interior) and the
        # screw's clearance bore through the wall.
        screw = fasteners.screw("M3")
        for kx, kz in (pt for pts in self.deck_knuckle_sites().values() for pt in pts):
            bore = cad_helpers.rotate_x(cad_helpers.cylinder_centered(insert.printed_hole_diameter, insert.depth + 1.0), 90)
            deck = cad_helpers.cut(deck, cad_helpers.translate(
                bore, kx, rear_in + kspec.height - insert.depth / 2.0 + 0.5, kz))
            lead = kspec.height - insert.depth + wall + 1.0
            thru = cad_helpers.rotate_x(cad_helpers.cylinder_centered(screw.clearance, lead + 1.0), 90)
            deck = cad_helpers.cut(deck, cad_helpers.translate(
                thru, kx, rear_out - 1.0 + (lead + 1.0) / 2.0, kz))

        # Vents and connector cutouts that reach above the Parting plane.
        from geometry import vents

        slots = vents.build(self.vent_spec(), wall)
        if slots:
            slots = cad_helpers.translate(
                slots, 0.0, -size.depth / 2 + wall / 2.0, self.deck_rear_level() / 2.0
            )
            deck = cad_helpers.cut(deck, slots)
        deck = cutouts.build(
            [c for c in self.cutouts() if c["z"] + c["height"] / 2.0 > zp],
            deck, wall, chamfer=config.corners.cutout_chamfer,
        )
        return self._mount_hinge(deck)
