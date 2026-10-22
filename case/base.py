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

    def _corner_standoff_outer_diameter(self) -> float:
        """Outer diameter of a corner deck-mount standoff boss (mm, M2.5)."""
        from utilities import fasteners

        screw = fasteners.screw("M2.5")
        sleeve = 1.2
        return screw.clearance + 2 * sleeve

    def _deck_standoff_conflict_test(self):
        """Return ``conflicts(cx, cy) -> bool`` for a deck-mount standoff.

        A standoff runs the full height up to the deck, so it conflicts with
        another boss it would fuse into (within one wall thickness, so their
        pilot bores don't merge into one ragged hole neither screw seats in
        correctly), or with any base-floor component's XY footprint outright
        — regardless of Z, since a floor-mounted part and a standoff spanning
        0..deck_level always overlap in Z in practice (every part this recipe
        places is well under deck_level).
        """
        wall = self.config.wall_thickness
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

        return conflicts

    def _nearest_free_spot(
        self, tx: float, ty: float, conflicts, bounds: tuple[float, float, float, float]
    ) -> tuple[float, float] | None:
        """Nearest point to ``(tx, ty)`` clear of ``conflicts``, within ``bounds``.

        A full 2D search (expanding rings around the target), not just a
        nudge along one line toward the case center: with a component (the
        keyboard) now spanning almost the entire footprint, the straight
        path from a nominal corner toward the center is blocked along its
        whole length, and only a 2D search finds the gaps that exist off to
        the side of it. Returns ``None`` if nothing within ``bounds`` clears.
        """
        if not conflicts(tx, ty):
            return (tx, ty)
        x0, y0, x1, y1 = bounds
        step = 1.0
        max_radius = math.hypot(x1 - x0, y1 - y0)
        r = step
        while r <= max_radius:
            n = max(12, int(2 * math.pi * r / step))
            for i in range(n):
                theta = 2 * math.pi * i / n
                cx = tx + r * math.cos(theta)
                cy = ty + r * math.sin(theta)
                if x0 <= cx <= x1 and y0 <= cy <= y1 and not conflicts(cx, cy):
                    return (cx, cy)
            r += step
        return None

    def _corner_positions(self) -> list[tuple[float, float]]:
        """Return deck-mount standoff positions (mm, XY).

        Nominally the 4 corners, inset 3 mm from the interior wall faces,
        each snapped to the nearest clear spot (see
        :meth:`_nearest_free_spot`) — a component mounting boss or a whole
        component's footprint (the SBC, the USB hub) can otherwise sit right
        on top of the nominal spot.

        With the keyboard now spanning nearly the full footprint, "nearest
        clear spot to a corner" alone tends to cluster near wherever the
        corner search happens to escape to and leave the rest of the deck
        unsupported, so three more targets — the quarter-width and center
        points of the rear (-Y) inset line — are added to reach into the
        rear strip's own free space. All targets are snapped the same way
        (:meth:`_nearest_free_spot`), so this tracks the layout rather than
        hardcoding where the rear strip's gaps happen to be. Targets that
        snap too close together to exist as separate printed bosses are
        merged.
        """
        size = self.size()
        wall = self.config.wall_thickness
        inset = 3.0
        half_iw = (size.width - 2 * wall) / 2
        half_id = (size.depth - 2 * wall) / 2
        bounds = (-half_iw + inset, -half_id + inset, half_iw - inset, half_id - inset)
        conflicts = self._deck_standoff_conflict_test()

        targets = [
            (sx * (half_iw - inset), sy * (half_id - inset))
            for sx, sy in ((1, 1), (-1, 1), (-1, -1), (1, -1))
        ]
        # Quarter- and center-width points at the rear (-Y) inset line: a
        # second pass of targets to reach into the rear strip's own free
        # space, distinct from whatever spot the corner search already
        # found. Without the center target, the two corner searches and the
        # two quarter searches all tend to get pulled toward whichever side
        # (west/east) has a clear channel, leaving the middle — often the
        # widest actually-free span, once the components crowding the
        # corners are dodged — with no standoff at all.
        targets += [
            (sx * half_iw / 2.0, -(half_id - inset))
            for sx in (1, -1)
        ]
        targets.append((0.0, -(half_id - inset)))

        # Two targets squeezed toward the same tight gap (common once the
        # keyboard and rear-strip parts leave only one or two clear pockets)
        # can snap only a few mm apart — closer than two standoff bodies can
        # actually sit without nearly fusing. Merge distance is one
        # standoff diameter beyond touching, not just a token epsilon.
        standoff_diameter = self._corner_standoff_outer_diameter()
        min_separation = 2 * standoff_diameter + wall

        positions: list[tuple[float, float]] = []
        for tx, ty in targets:
            spot = self._nearest_free_spot(tx, ty, conflicts, bounds)
            if spot is None:
                continue
            if any(
                math.hypot(spot[0] - px, spot[1] - py) < min_separation
                for px, py in positions
            ):
                continue
            positions.append(spot)
        return positions

    def all_bosses(self) -> list[tuple[float, float, float, float, Component | None]]:
        """Every boss on the base floor (mm, world frame), CAD-free.

        Each entry is ``(x, y, outer_diameter, height, owner)``: component
        mounting bosses (``owner`` the component the boss supports — a
        mounting boss legitimately touches/overlaps the part it holds up,
        so callers should skip that pair) and deck-mount standoffs
        (:meth:`_corner_positions`, ``owner`` ``None`` — a standoff belongs
        to no single component and should be checked against all of them).

        Bosses are case-build-time geometry (see :meth:`build_bottom`) —
        never themselves placed components, so the ordinary collision
        system (which compares placed components against each other) never
        sees them. This is what feeds
        :func:`utilities.validation.check_boss_collisions`, which closes
        that gap.
        """
        from geometry.boss import boss_spec

        wall = self.config.wall_thickness
        default_screw = self.config.screws.standoff
        result: list[tuple[float, float, float, float, Component | None]] = []
        for placement in self._base_placements():
            component = placement.component
            screw_size = component.mounting_screw() or default_screw
            for hole in component.mounting_holes():
                spec = boss_spec(
                    wall_thickness=wall,
                    screw_size=screw_size,
                    insert_type=screw_size,
                    hole_diameter=hole.diameter,
                    height=hole.height,
                )
                bx, by, _ = placement.world_offset(hole.x, hole.y, 0.0)
                result.append((bx, by, spec.outer_diameter, spec.height, component))

        boss_od = self._corner_standoff_outer_diameter()
        for cx, cy in self._corner_positions():
            result.append((cx, cy, boss_od, self.deck_level_at(cy), None))
        return result

    def foot_positions(self) -> list[tuple[float, float]]:
        """Centers of the four rubber-foot recesses (config-derived)."""
        size = self.size()
        feet = self.config.feet
        hx = size.width / 2.0 - feet.inset_x
        hy = size.depth / 2.0 - feet.inset_y
        return [(sx * hx, sy * hy) for sx in (-1, 1) for sy in (-1, 1)]

    def well_rim_height(self) -> float:
        """Height of the Well rim above the Deck top (mm); 0 without a keyboard."""
        from geometry import well

        if self.keyboard is None or not hasattr(self.keyboard, "switch_top_height"):
            return 0.0
        return well.rim_height(
            self.keyboard.switch_top_height,
            self.config.wall_thickness,
            self.config.well.switch_margin,
        )

    def build_bottom(self):
        """Generate the base bottom tray solid.

        An open-top tray (shelled at >Z) with the floor, walls, mounting
        bosses, ribs, vents, connector cutouts, and the deck-mount standoff
        bosses (see :meth:`_corner_positions` — nominally 4, more if the
        layout leaves the corners too crowded to support the deck alone).

        Returns
        -------
        Shape
            The base bottom tray solid.
        """
        from components.battery import Battery
        from geometry import boss, cradle, cutouts, fillet, ribs, vents
        from utilities import cad_helpers, fasteners

        cad_helpers.require_cad()
        config = self.config
        wall = config.wall_thickness
        clearance = config.clearance.shell
        size = self.size()
        dl = self.deck_level()
        rear_dl = self.deck_rear_level()

        # Outer tray box, tall enough to reach the wedge's high (rear) end;
        # corner fillet first so the shell keeps the outer envelope exactly
        # (negative shell offset). The sloped rim is cut afterwards — shelling
        # a prism and then slicing it leaves the walls following the slope,
        # which is what the deck seats against.
        outer = cad_helpers.box_centered(size.width, size.depth, rear_dl + wall)
        outer = cad_helpers.translate(outer, 0.0, 0.0, (rear_dl - wall) / 2.0)
        outer = fillet.fillet_corners(outer, config.corners.radius)
        # Not geometry.shell.offset_shell: that helper's chain includes an
        # extra .workplane() call (needed by the lid) that is numerically
        # different from this literal chain — see
        # utilities.cad_helpers.shell_open_face's docstring.
        body = cad_helpers.shell_open_face(outer, wall, cad_helpers.FaceRef.TOP)
        if self.slope():
            # Trim the prism down to the sloped rim: everything above the
            # deck's own underside plane goes, leaving walls whose top edge
            # is the seat the deck lies on.
            body = cad_helpers.cut(
                body, self._deck_surface_tool(dl, size, rear_dl + 2 * wall)
            )

        # Mounting bosses for base-floor components.
        interior_w = size.width - 2 * wall
        interior_d = size.depth - 2 * wall
        base_placements = self._base_placements()
        mounting_bosses = self.assembly.bosses(base_placements)
        features = [boss.build(spec, x, y) for x, y, spec in mounting_bosses]

        # Deck-mount standoff bosses (M2.5), see _corner_positions(). Each
        # rises to the deck's underside *at its own Y*, so on a sloped deck
        # ones further back are taller than ones toward the front and all of
        # them still meet the plate.
        screw = fasteners.screw("M2.5")
        boss_od = self._corner_standoff_outer_diameter()
        corner_positions = self._corner_positions()
        corner_base_diameters = []
        for cx, cy in corner_positions:
            corner_dl = self.deck_level_at(cy)
            # Built through geometry.boss.build (a widened, tapered base per
            # the FDM boss-design rule) rather than a bare cylinder, same as
            # every component mounting boss below.
            standoff_spec = boss.BossSpec(
                hole_diameter=screw.pilot_hole,
                outer_diameter=boss_od,
                height=corner_dl,
                wall_thickness=wall,
            )
            corner_base_diameters.append(standoff_spec.base_diameter)
            standoff = boss.build(standoff_spec, cx, cy)
            # Square off the top against the sloped underside so the standoff
            # meets the deck flush instead of poking a cylinder through it.
            if self.slope():
                standoff = cad_helpers.cut(
                    standoff, self._deck_surface_tool(dl, size, rear_dl + 2 * wall)
                )
            features.append(standoff)

        # Battery cell cradles: printed floor saddles that key each cell's
        # lateral position (geometry.cradle) — the pack isn't fastened like
        # a bossed component, so this isn't part of mounting_bosses above.
        # Not sourced from base_placements: that list is filtered to
        # z-bounds within one wall thickness of the floor, which the
        # battery's own raise (below) happens to satisfy too, but scanning
        # placements directly here doesn't depend on that coincidence.
        cradle_solids = []
        for p in self.assembly.placements:
            if not isinstance(p.component, Battery):
                continue
            battery = p.component
            spec = cradle.CradleSpec(
                diameter=battery.cell_diameter,
                # The cell's actual floor raise (config/layouts/clamshell.yaml
                # sets it to config.wall_thickness, same rib clearance every
                # other floor part uses) — the groove is cut to match the
                # cell's true resting height, not an independent guess.
                rest_height=p.z,
                height=battery.cradle_height,
                # Extent along the cell's own axis: tied to the shell's own
                # wall parameter rather than a bare number.
                width=wall * 3,
            )
            # cradle.build()'s groove runs along local Y, matching Battery's
            # own cell-axis convention, so the same placement rotation that
            # orients the cells orients the saddle.
            saddle = cradle.build(spec)
            if p.rotation:
                saddle = cad_helpers.rotate_z(saddle, p.rotation)
            # Two saddles per cell, offset toward each end along the cell's
            # own axis (local Y), not one centred on the cell's midpoint: a
            # cylinder resting on a single narrow saddle (width = wall * 3,
            # a fraction of the cell's 65+ mm length) has no resistance to
            # rocking about that one line of contact, the same way a pencil
            # balanced on one finger tips either way. Two contact points near
            # the ends is how a resting cylinder is actually kept steady.
            # Inset by the saddle's own half-width so the block sits fully
            # under the cell rather than overhanging its end; clamped to 0 so
            # a cell shorter than the saddle degenerates to the old single
            # centred saddle instead of an inverted (crossed-over) offset.
            end_offset = max(0.0, battery.cell_length / 2.0 - spec.width / 2.0)
            for cx, cy in battery._cell_centers():
                for cy_end in (cy - end_offset, cy + end_offset):
                    wx, wy, _ = p.world_offset(cx, cy_end, 0.0)
                    cradle_solids.append(cad_helpers.translate(saddle, wx, wy, 0.0))
        features.extend(cradle_solids)

        # Stiffening ribs, kept clear of every boss above: a rib crossing a
        # boss's bore would plug the screw hole with rib material once
        # unioned into the shell. Cradles are deliberately not included here
        # (unlike component mounting bosses and the corner standoffs): a
        # cradle has no bore for rib material to plug — it's a solid block
        # resting at the same floor-raise convention as the ribs themselves
        # (rest_height above, same as every other floor part's rib
        # clearance) — so a rib crossing under one simply becomes part of
        # the same solid once unioned, no clearance cut needed. Cutting one
        # anyway just perforates the (thin) rib wall it crosses into an
        # unnecessary, oddly-shaped remnant for no structural benefit.
        rspec = ribs.rib_layout(
            interior_w, interior_d, wall, rib_height=ribs.rib_height(wall)
        )
        rib_solids = ribs.build(rspec, interior_w, interior_d)
        # base_diameter (not outer_diameter): the rib clearance cut has to
        # clear the boss's widest point, at the floor, where the tapered
        # base flares out beyond the post's nominal diameter.
        boss_keepouts = [(x, y, spec.base_diameter) for x, y, spec in mounting_bosses]
        boss_keepouts += [
            (cx, cy, base_d) for (cx, cy), base_d in zip(corner_positions, corner_base_diameters)
        ]
        for bx, by, diameter in boss_keepouts:
            clearance_cyl = cad_helpers.cylinder_centered(diameter + wall, rspec.height)
            clearance_cyl = cad_helpers.translate(clearance_cyl, bx, by, rspec.height / 2.0)
            rib_solids = [cad_helpers.cut(rib, clearance_cyl) for rib in rib_solids]
        features.extend(rib_solids)

        if features:
            fused = cad_helpers.union(features[0], *features[1:])
            body = cad_helpers.union(body, fused)

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
        # Same reasoning for a deck-mount standoff boss (above) that happens
        # to land near the rear wall: a vent slat cutting through it would
        # perforate the very thing holding the deck up. X-only, whatever the
        # boss's Y — a slot this far off in Y from a corner near the front
        # wouldn't be in the rear-wall vent row's Y-band to begin with, so
        # the extra keepout there is harmless, not just unnecessary.
        vent_keepouts += tuple(
            (cx - boss_od / 2 - config.corners.cutout_chamfer,
             cx + boss_od / 2 + config.corners.cutout_chamfer)
            for cx, _cy in corner_positions
        )
        # The rear wall is the wedge's high end, so the slots span its full
        # (taller) height. The slope tilts about X, so this wall's top edge
        # stays horizontal at rear_dl and the slot row needs no tilt itself.
        vspec = vents.vent_slots(interior_w, rear_dl - wall, keepouts=vent_keepouts)
        slots = vents.build(vspec, wall)
        if slots:
            slots = cad_helpers.translate(
                slots, 0.0, -size.depth / 2 + wall / 2.0, rear_dl / 2.0
            )
            body = cad_helpers.cut(body, slots)

        # Connector cutouts (external, reach-aware), beveled for plug lead-in.
        body = cutouts.build(
            self.cutouts(), body, wall, chamfer=config.corners.cutout_chamfer
        )

        # Screw lugs that straddle the Tray Seam (US28), on the inner floor.
        seam = config.split.get("tray")
        if seam is not None:
            from geometry import seam_joint

            body = seam_joint.add_joints(
                body, seam, size.depth, wall,
                seam_joint.joint_spec(config.screws.body),
                floor_top=cad_helpers.bounding_box(body).zmin + wall,
                obstacles=self.assembly.build_subset(self.assembly.placements),
                clearance=clearance,
            )

        # Rubber-foot recesses in the floor's underside. Positions come from
        # config alone (foot_positions), never from boss positions.
        feet = config.feet
        floor_z = cad_helpers.bounding_box(body).zmin
        for fx, fy in self.foot_positions():
            recess = cad_helpers.cylinder_centered(feet.diameter, 2 * feet.depth)
            body = cad_helpers.cut(
                body, cad_helpers.translate(recess, fx, fy, floor_z)
            )
        return body

    def build_top(self):
        """Generate the base top deck solid.

        A plate covering the base cavity, with a keyboard cutout and M2.5
        clearance holes at each deck-mount standoff (see
        :meth:`_corner_positions`). The deck seats on the tray rim: its underside
        follows :meth:`deck_level_at`, so with a non-zero
        ``config.deck.slope`` it is a wedge-tilted slab (rear high) rather
        than a flat plate, and the keyboard mounted to it gets that tilt.

        Returns
        -------
        Shape
            The base top deck solid, or an empty Workplane if no keyboard
            is configured.
        """
        from geometry import fillet, well
        from utilities import cad_helpers, fasteners

        cad_helpers.require_cad()
        config = self.config
        wall = config.wall_thickness
        clearance = config.clearance.shell
        size = self.size()
        dl = self.deck_level()
        rear_dl = self.deck_rear_level()
        slope = self.slope()

        # Deck plate: full footprint, sliced to a slab between two
        # deck-parallel planes (underside at deck_level_at, top one wall
        # above it). Slicing a tall prism rather than tilting a thin plate
        # keeps the outer sides vertical and the footprint exactly the case
        # footprint, so the fillet and the walls below still line up.
        blank_h = rear_dl + 4 * wall
        deck = cad_helpers.box_centered(size.width, size.depth, blank_h)
        deck = cad_helpers.translate(deck, 0.0, 0.0, blank_h / 2.0)
        deck = fillet.fillet_corners(deck, config.corners.radius)
        footprint = deck
        # Keep only the material between the two deck-parallel planes. At
        # slope 0 these tools degenerate to plain half-spaces, reproducing
        # the original flat plate exactly.
        deck = cad_helpers.cut(deck, self._deck_surface_tool(dl + wall, size, blank_h))
        deck = cad_helpers.intersect(deck, self._deck_surface_tool(dl, size, blank_h))

        # Keyboard cutout centered at the keyboard placement. Bored along the
        # deck normal (tilted with the slab) so the opening keeps its true
        # width/depth in the deck's own plane instead of being sheared.
        kb_placement = self._keyboard_placement()
        if kb_placement is not None:
            kb_size = kb_placement.component.size()
            cut_w = kb_size.width + 2 * clearance
            cut_d = kb_size.depth + 2 * clearance
            cut_h = blank_h
            pose = (kb_placement.x, kb_placement.y,
                    self.deck_level_at(kb_placement.y) + wall / 2.0)

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

            cutout = cad_helpers.box_centered(cut_w, cut_d, cut_h)
            if slope:
                cutout = cad_helpers.rotate_x(cutout, -slope)
            cutout = cad_helpers.translate(cutout, *pose)
            deck = cad_helpers.cut(deck, cutout)

        # M2.5 clearance holes for the deck screws, each bored normal to the
        # deck surface at its own Y — tilted with the slab in front of the
        # knee, vertical behind it where the deck has flattened out (see
        # _deck_knee_y): a hole there still tilted by the keyboard's slope
        # would bore in at an angle through a surface that isn't tilted at
        # all, missing the flat deck's own normal.
        screw = fasteners.screw("M2.5")
        knee_y = self._deck_knee_y()
        for cx, cy in self._corner_positions():
            # Generously longer than the slab is thick, so a tilted bore still
            # exits both faces cleanly.
            hole = cad_helpers.cylinder_centered(screw.clearance, 4 * wall + 2 * clearance)
            if slope and (knee_y is None or cy >= knee_y):
                hole = cad_helpers.rotate_x(hole, -slope)
            hole = cad_helpers.translate(
                hole, cx, cy, self.deck_level_at(cy) + wall / 2.0
            )
            deck = cad_helpers.cut(deck, hole)

        return deck
