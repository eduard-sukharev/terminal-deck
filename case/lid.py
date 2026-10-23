"""Lid shell generator.

The Lid is split into two parts that sandwich the display assembly:

* **Lid shell** — the rear shell tray (open at +Z toward the user).  Five solid
  walls (left, right, front, back, bottom) form a bucket that the display
  assembly drops into.  Eight bosses hold heat-set inserts for the bezel
  screws: four at the corners, and one above and one below the glass on each
  side of the Bezel's straight centre Seam.
* **Lid bezel** — the front plate with a glass cutout and eight countersunk
  mounting holes.
  Sits *inside* the lid_shell opening (XY = interior dimensions) so its front
  face is flush with the Lid shell walls.

The combined lid assembly (base + display assembly + bezel) is composed in
``main.py``; this module builds the two structural halves.

All dimensions derive from the display module, the driver board, and the
wall-thickness parameters.
"""

from __future__ import annotations

from components.base import Component
from components.hinge import Hinge
from utilities import fasteners
from utilities.config_loader import Config


class Lid:
    """Lid half of the clamshell case."""

    def __init__(
        self,
        display: Component,
        config: Config,
        hinge: Hinge | None = None,
        lid_interior_height: float = 12.0,
        world_z: float = 60.0,
        footprint: tuple[float, float] | None = None,
        bezel_thickness: float | None = None,
        interior=None,
        visor=None,
        assembly=None,
        interior_placements=None,
    ) -> None:
        self.display = display
        self.config = config
        self.hinge = hinge
        self.lid_interior_height = lid_interior_height
        self.world_z = world_z
        self.footprint = footprint
        #: Solid of what sits inside the shell (display, driver).
        self.interior = interior
        #: Assembly and the placements inside the shell (display, driver, plug):
        #: Seam lugs and Bezel bosses keep clear of their volumes (CAD-free).
        self.assembly = assembly
        self.interior_placements = interior_placements or []
        self._memo: dict = {}
        #: ``geometry.visor.VisorProfile`` for the Lid shell's tapered lip, or
        #: ``None`` for a flat-topped shell.
        self.visor = visor
        self.bezel_thickness = (
            bezel_thickness if bezel_thickness is not None else config.wall_thickness
        )

    def glass_recess(self) -> dict:
        """Glass recess geometry centered on the display (mm).

        The recess is keyed off the measured display size and the configured
        bezel inset/recess depth, never assumed centered.
        """
        display = self.config.display
        bezel_inset = self.config.bezel.inset
        recess_depth = self.config.glass.recess_depth
        return {
            "width": display.width - 2 * bezel_inset,
            "height": display.height - 2 * bezel_inset,
            "depth": recess_depth,
            "x": 0.0,
            "y": 0.0,
        }

    def _outer_bounds(self) -> tuple[float, float, float, float]:
        """Return ``(width, depth, outer_bottom, outer_top)`` (mm)."""
        config = self.config
        wall = config.wall_thickness
        clearance = config.clearance.shell

        if self.footprint is not None:
            width, depth = self.footprint
        else:
            width = self.display.size().width + 2 * (wall + clearance)
            depth = self.display.size().depth + 2 * (wall + clearance)

        display_top = self.world_z + self.display.size().height
        interior_top = display_top + clearance
        driver_height = float(
            config.hardware.get("driver_board", {}).get("height", 4.6)
        )
        driver_bottom = self.world_z - driver_height
        interior_bottom = driver_bottom - clearance
        outer_bottom = interior_bottom - wall
        outer_top = interior_top + wall
        return width, depth, outer_bottom, outer_top

    def height(self) -> float:
        """Lid shell + Bezel thickness, excluding the Visor (mm)."""
        _, _, outer_bottom, outer_top = self._outer_bounds()
        return outer_top - outer_bottom

    def wall_bounds(self):
        """Interior wall faces of the Lid shell (mm)."""
        from geometry.merged_boss import WallBounds

        width, depth, _, _ = self._outer_bounds()
        wall = self.config.wall_thickness
        return WallBounds(-width / 2 + wall, width / 2 - wall, -depth / 2 + wall, depth / 2 - wall)

    def _corner_positions(self) -> list[tuple[float, float]]:
        """The 4 corner Bezel-mount positions (mm, XY), inset 3 mm from the
        interior wall faces (the Bezel's edges)."""
        b = self.wall_bounds()
        inset = 3.0
        return [
            (b.x1 - inset, b.y1 - inset),   # NE
            (b.x0 + inset, b.y1 - inset),   # NW
            (b.x0 + inset, b.y0 + inset),   # SW
            (b.x1 - inset, b.y0 + inset),   # SE
        ]

    def _seam_screw_positions(self) -> list[tuple[float, float]]:
        """The 4 screws beside the Bezel's centre Seam (mm, XY).

        One above and one below the glass on each side of the Seam, centred in
        the band between the glass opening and the Bezel's edge, where the
        display panel is not.
        """
        b = self.wall_bounds()
        glass_half = self.glass_recess()["height"] / 2.0
        y = glass_half + (b.y1 - glass_half) / 2.0
        seam = self.config.split["bezel"].seams()[0].x if "bezel" in self.config.split else 0.0
        dx = self.config.bezel.seam_screw_offset
        return [(seam + sx * dx, sy * y) for sx in (-1, 1) for sy in (-1, 1)]

    def screw_positions(self) -> list[tuple[float, float]]:
        """All eight Bezel screw positions (mm, XY): corners, then Seam side."""
        return self._corner_positions() + self._seam_screw_positions()

    def boss_outer_diameter(self) -> float:
        """Outer diameter of a Bezel boss: the insert bore plus a sleeve (mm)."""
        return self._insert().printed_hole_diameter + 2 * 1.2

    def _floor_top(self) -> float:
        _, _, outer_bottom, _ = self._outer_bounds()
        return outer_bottom + self.config.wall_thickness

    def seam_bands(self):
        """Seam bands of the Lid shell and the Bezel, keyed ``"<part>:<index>"``."""
        from utilities.validation import seam_bands

        depth = self._outer_bounds()[1]
        splits = {p: self.config.split[p] for p in ("lid_shell", "bezel") if p in self.config.split}
        return seam_bands(splits, {p: depth for p in splits}, self.config.wall_thickness)

    def _interior_rects(self, top: float):
        if self.assembly is None:
            return []
        return self.assembly.keepout_rects(
            self._floor_top(), top, self.interior_placements or None
        ) if self.interior_placements else []

    def knuckle_rects(self) -> list[tuple[float, float, float, float]]:
        """XY footprint of the Lid knuckles on the rear wall (mm)."""
        if self.hinge is None:
            return []
        width, depth, _, _ = self._outer_bounds()
        reach = self.hinge.diameter
        return [
            (x0, x1, -depth / 2.0 - reach / 2.0, -depth / 2.0 + self.config.wall_thickness)
            for x0, x1 in self.hinge.lid_knuckle_spans(width)
        ]

    def lug_sites(self):
        """Seam-joint sites per Lid shell Seam (``"lid_shell:<index>"``), two each.

        Clear of the display stack, the Bezel bosses and the Lid knuckles.
        """
        from geometry import seam_joint

        if "lug_sites" in self._memo:
            return self._memo["lug_sites"]
        split = self.config.split.get("lid_shell")
        sites = {}
        if split is not None:
            wall = self.config.wall_thickness
            depth = self._outer_bounds()[1]
            spec = seam_joint.joint_spec(self.config.screws.body)
            keepouts = self._interior_rects(self._floor_top() + spec.size + self.config.clearance.shell)
            r = self.boss_outer_diameter() / 2.0
            keepouts += [(x - r, x + r, y - r, y + r) for x, y in self.screw_positions()]
            keepouts += self.knuckle_rects()
            for i, seam in enumerate(split.seams()):
                sites[f"lid_shell:{i}"] = seam_joint.plan_joints(
                    seam, depth, wall, spec, floor_top=self._floor_top(),
                    clearance=self.config.clearance.shell, keepouts=keepouts,
                )
        self._memo["lug_sites"] = sites
        return sites

    def structural_features(self):
        """Structural features the Lid's Seams must keep clear of (CAD-free)."""
        from geometry import seam_joint
        from utilities.validation import Feature

        wall = self.config.wall_thickness
        spec = seam_joint.joint_spec(self.config.screws.body)
        r = self.boss_outer_diameter() / 2.0
        features = []
        for x, y in self.screw_positions():
            features.append(Feature("boss", f"({x:.1f}, {y:.1f})", x - r, x + r, y - r, y + r, part="lid_shell"))
            hole = fasteners.screw(self.config.screws.body).head_diameter / 2.0
            features.append(Feature("boss", f"bezel hole ({x:.1f}, {y:.1f})", x - hole, x + hole, y - hole, y + hole, part="bezel"))
        for i, (x0, x1, y0, y1) in enumerate(self.knuckle_rects()):
            features.append(Feature("knuckle", f"#{i}", x0, x1, y0, y1, part="lid_shell"))
        for sid, sites in self.lug_sites().items():
            for sx, sy, backed in sites:
                x0, x1, y0, y1 = seam_joint.lug_footprint(spec, sx, sy, wall, backed)
                features.append(Feature("lug", f"({sx:.1f}, {sy:.1f})", x0, x1, y0, y1, joins=sid, part="lid_shell"))
        return features

    def fastening_report(self, report) -> None:
        """Data-level Seam checks for the Lid (HARD)."""
        from utilities.validation import check_seam_clearance

        check_seam_clearance(self.seam_bands(), self.structural_features(), report)
        r = self.boss_outer_diameter() / 2.0
        rects = self._interior_rects(self._boss_top())
        hits = [
            f"({x:.1f}, {y:.1f})" for x, y in self.screw_positions()
            for x0, x1, y0, y1 in rects
            if x + r > x0 and x - r < x1 and y + r > y0 and y - r < y1
        ]
        report.add(
            "bezel-bosses-clear-of-display", not hits,
            "every Bezel boss stands clear of the display panel and driver" if not hits
            else f"Bezel boss at {', '.join(sorted(set(hits)))} lands on the display stack",
        )

    def _insert(self):
        """Heat-set insert the Bezel screws thread into (M2, from config)."""
        return fasteners.heat_insert(self.config.screws.body)

    def _boss_top(self) -> float:
        """Z of the boss tops: the Bezel's rear face (mm)."""
        _, _, _, outer_top = self._outer_bounds()
        return outer_top - self.bezel_thickness

    def build_shell(self):
        """Generate the Lid shell: the rear tray, open toward the Bezel.

        Floor and four walls form a tray (open at +Z, the display side). The
        four Bezel bosses grow from the floor, so they are part of the same
        solid, and carry heat-set insert holes for the Bezel's countersunk
        M2 screws.

        Returns
        -------
        Shape
            The Lid shell solid.
        """
        from geometry import fillet, merged_boss
        from utilities import cad_helpers

        cad_helpers.require_cad()
        config = self.config
        wall = config.wall_thickness
        width, depth, outer_bottom, outer_top = self._outer_bounds()
        height = outer_top - outer_bottom

        outer = cad_helpers.box_centered(width, depth, height)
        outer = cad_helpers.translate(outer, 0.0, 0.0, (outer_top + outer_bottom) / 2.0)
        outer = fillet.fillet_corners(outer, config.corners.radius)
        # Chamfer the rear (bottom) perimeter before the cavity is cut so the
        # rim stays full thickness.
        outer = cad_helpers.chamfer_face_edges(outer, cad_helpers.FaceRef.BOTTOM, 2.0)

        inner_h = height - wall
        cavity = cad_helpers.box_centered(width - 2 * wall, depth - 2 * wall, inner_h + 1.0)
        cavity = cad_helpers.translate(
            cavity, 0.0, 0.0, outer_bottom + wall + (inner_h + 1.0) / 2.0
        )
        cavity = fillet.fillet_corners(cavity, max(config.corners.radius - wall, 0.0))
        body = cad_helpers.cut(outer, cavity)

        # Bezel bosses: floor up to the Bezel's rear face, insert hole in top.
        # A boss within 2 walls of a wall is merged into it (ADR 0003).
        insert = self._insert()
        floor_top = outer_bottom + wall
        boss_od = self.boss_outer_diameter()
        # Start a little inside the floor so the union is a real overlap.
        boss_bottom = floor_top - 0.5
        boss_h = self._boss_top() - boss_bottom
        rule = config.merged_boss
        for cx, cy in self.screw_positions():
            boss = cad_helpers.cylinder_centered(boss_od, boss_h)
            boss = cad_helpers.translate(boss, cx, cy, boss_bottom + boss_h / 2.0)
            walls = merged_boss.merge_walls(cx, cy, boss_od / 2.0, self.wall_bounds(), wall, rule)
            if walls:
                hull = merged_boss.build_hull(
                    cx, cy, boss_od / 2.0, boss_h, walls, self.wall_bounds(), wall / 2.0,
                    z0=boss_bottom,
                )
                boss = cad_helpers.union(boss, hull)
            body = cad_helpers.union(body, boss)
        for cx, cy in self.screw_positions():
            hole = cad_helpers.cylinder_centered(insert.printed_hole_diameter, insert.depth)
            hole = cad_helpers.translate(
                hole, cx, cy, self._boss_top() - insert.depth / 2.0
            )
            body = cad_helpers.cut(body, hole)

        # Visor: front and side walls rising above the rim to fill the Deck's
        # wedge when closed (zero at the hinge end).
        if self.visor is not None and self.visor.max_height > 0.0:
            from geometry import visor as visor_geometry

            body = cad_helpers.union(
                body,
                visor_geometry.build_walls(
                    self.visor, width, depth, wall, config.corners.radius, outer_top
                ),
            )

        # Screw lugs on each Lid shell Seam, two per Seam, at the planned sites.
        split = config.split.get("lid_shell")
        if split is not None:
            from geometry import seam_joint

            sites = self.lug_sites()
            for i, seam in enumerate(split.seams()):
                body = seam_joint.add_joints(
                    body, seam, depth, wall, seam_joint.joint_spec(config.screws.body),
                    floor_top=floor_top, sites=sites[f"lid_shell:{i}"],
                )

        return self._mount_hinge(body)

    def _on_hinge_axis(self, solid):
        """Move an axis-at-origin hinge solid onto the hinge axis.

        In the Lid's own frame the axis runs along the rear edge, in the Bezel's
        front plane (the plane the Lid closes on).
        """
        from utilities import cad_helpers

        _, depth, _, outer_top = self._outer_bounds()
        return cad_helpers.translate(solid, 0.0, -depth / 2.0, outer_top)

    def _mount_hinge(self, body):
        """Notch the shell for the Base knuckle and fuse the Lid knuckles on.

        The knuckles keep to the rear wall's thickness so they stay out of the
        display cavity. Without a hinge, ``body`` is returned unchanged.
        """
        from utilities import cad_helpers

        if self.hinge is None:
            return body
        width, depth, _, outer_top = self._outer_bounds()
        wall = self.config.wall_thickness
        reach = self.hinge.diameter
        # Rolled rear edge: the Lid half of a full-width barrel on the hinge
        # axis, kept to the rear wall's thickness like the knuckles.
        roll_slab = cad_helpers.translate(
            cad_helpers.box_centered(width, reach + wall, reach),
            0.0, -depth / 2.0 - reach / 2.0 + wall / 2.0, outer_top - reach / 2.0,
        )
        roll = cad_helpers.intersect(
            self._on_hinge_axis(self.hinge.build_lid_roll(width)), roll_slab
        )
        body = cad_helpers.union(body, roll)
        body = cad_helpers.cut(body, self._on_hinge_axis(self.hinge.build_lid_notch(width)))
        slab = cad_helpers.translate(
            cad_helpers.box_centered(width, reach + wall, 4 * reach),
            0.0, -depth / 2.0 - reach / 2.0 + wall / 2.0, outer_top,
        )
        knuckles = cad_helpers.intersect(
            self._on_hinge_axis(self.hinge.build_lid_knuckles(width)), slab
        )
        body = cad_helpers.union(body, knuckles)
        return cad_helpers.cut(body, self._on_hinge_axis(self.hinge.build_lid_bores(width)))

    def build_bezel(self):
        """Generate the Bezel: the front plate with the glass opening.

        Sits inside the Lid shell's opening (XY = interior dimensions) on the
        bosses, front face flush with the shell. Four countersunk M2 holes
        take the screws from the front into the bosses' heat-set inserts.

        Returns
        -------
        Shape
            The Bezel solid.
        """
        from geometry import fillet
        from utilities import cad_helpers

        cad_helpers.require_cad()
        config = self.config
        wall = config.wall_thickness
        width, depth, _, outer_top = self._outer_bounds()

        bezel_w = width - 2 * wall
        bezel_d = depth - 2 * wall

        bezel = cad_helpers.box_centered(bezel_w, bezel_d, self.bezel_thickness)
        bezel = cad_helpers.translate(
            bezel, 0.0, 0.0, outer_top - self.bezel_thickness / 2.0
        )
        bezel = fillet.fillet_corners(bezel, max(config.corners.radius - wall, 0.0))

        # Glass opening through the Bezel. The cutter is 0.1 mm taller than
        # the Bezel so the chamfer on its rear edge lands within the plate.
        recess = self.glass_recess()
        cut_h = self.bezel_thickness + 0.1
        cutout = cad_helpers.box_centered(recess["width"], recess["height"], cut_h)
        cutout = cad_helpers.translate(cutout, 0.0, 0.0, outer_top - cut_h / 2.0)
        cutout = cad_helpers.chamfer_face_edges(cutout, cad_helpers.FaceRef.BOTTOM, 2.0)
        bezel = cad_helpers.cut(bezel, cutout)

        # Countersunk clearance holes: through-hole plus a cone from the
        # head diameter at the front face down to the shaft.
        screw = fasteners.screw(config.screws.body)
        for cx, cy in self.screw_positions():
            hole = cad_helpers.cylinder_centered(screw.clearance, self.bezel_thickness + 1.0)
            hole = cad_helpers.translate(
                hole, cx, cy, outer_top - self.bezel_thickness / 2.0
            )
            sink_h = min(screw.head_depth, self.bezel_thickness)
            sink = cad_helpers.frustum_centered(screw.clearance, screw.head_diameter, sink_h)
            sink = cad_helpers.translate(sink, cx, cy, outer_top - sink_h / 2.0)
            bezel = cad_helpers.cut(bezel, hole, sink)

        return bezel
