"""Lid shell generator.

The Lid is split into two parts that sandwich the display assembly:

* **Lid shell** — the rear shell tray (open at +Z toward the user).  Five solid
  walls (left, right, front, back, bottom) form a bucket that the display
  assembly drops into.  Four bosses at the corners hold heat-set inserts for
  the bezel screws.
* **Lid bezel** — the front plate with a glass cutout and four mounting holes.
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
    ) -> None:
        self.display = display
        self.config = config
        self.hinge = hinge
        self.lid_interior_height = lid_interior_height
        self.world_z = world_z
        self.footprint = footprint
        #: Solid of what sits inside the shell (display, driver); Seam
        #: joints keep clear of it.
        self.interior = interior
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

    def _corner_positions(self) -> list[tuple[float, float]]:
        """Return the 4 bezel-mount corner positions (mm, XY).

        Inset 3 mm from the interior wall faces (the bezel's edges).
        """
        width, depth, _, outer_top = self._outer_bounds()
        wall = self.config.wall_thickness
        inset = 3.0
        half_iw = (width - 2 * wall) / 2
        half_id = (depth - 2 * wall) / 2
        return [
            (half_iw - inset, half_id - inset),   # NE
            (-half_iw + inset, half_id - inset),  # NW
            (-half_iw + inset, -half_id + inset), # SW
            (half_iw - inset, -half_id + inset),  # SE
        ]

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
        from geometry import fillet
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
        insert = self._insert()
        sleeve = 1.2
        boss_od = insert.printed_hole_diameter + 2 * sleeve
        floor_top = outer_bottom + wall
        # Start a little inside the floor so the union is a real overlap.
        boss_bottom = floor_top - 0.5
        boss_h = self._boss_top() - boss_bottom
        for cx, cy in self._corner_positions():
            boss = cad_helpers.cylinder_centered(boss_od, boss_h)
            boss = cad_helpers.translate(boss, cx, cy, boss_bottom + boss_h / 2.0)
            body = cad_helpers.union(body, boss)
        for cx, cy in self._corner_positions():
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

        # Screw lugs that straddle the Lid shell Seam (US28).
        seam = config.split.get("lid_shell")
        if seam is not None:
            from geometry import seam_joint

            body = seam_joint.add_joints(
                body, seam, depth, wall,
                seam_joint.joint_spec(config.screws.body),
                floor_top=floor_top,
                obstacles=self.interior,
                clearance=config.clearance.shell,
            )

        return body

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
        for cx, cy in self._corner_positions():
            hole = cad_helpers.cylinder_centered(screw.clearance, self.bezel_thickness + 1.0)
            hole = cad_helpers.translate(
                hole, cx, cy, outer_top - self.bezel_thickness / 2.0
            )
            sink_h = min(screw.head_depth, self.bezel_thickness)
            sink = cad_helpers.frustum_centered(screw.clearance, screw.head_diameter, sink_h)
            sink = cad_helpers.translate(sink, cx, cy, outer_top - sink_h / 2.0)
            bezel = cad_helpers.cut(bezel, hole, sink)

        return bezel
