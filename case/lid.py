"""Lid shell generator.

The lid is split into two halves that sandwich the display assembly:

* **Lid base** — the rear shell tray (open at +Z toward the user).  Five solid
  walls (left, right, front, back, bottom) form a bucket that the display
  assembly drops into.  Four bosses at the corners accept the bezel screws.
* **Lid bezel** — the front plate with a glass cutout and four mounting holes.
  Sits *inside* the lid_base opening (XY = interior dimensions) so its front
  face is flush with the lid_base shell walls.

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
    ) -> None:
        self.display = display
        self.config = config
        self.hinge = hinge
        self.lid_interior_height = lid_interior_height
        self.world_z = world_z
        self.footprint = footprint
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

    def build_base(self):
        """Generate the lid base solid (rear shell tray).

        A hollow shell (open at −Z toward the base) with a rectangular pocket
        on the +Z face where the bezel sits.  Four bosses at the corners of
        the pocket accept M2.5 screws from the bezel.

        Returns
        -------
        cadquery.Workplane
            The lid base solid.
        """
        from geometry import fillet, shell
        from utilities import cq_helpers

        cq_helpers.require_cq()
        config = self.config
        wall = config.wall_thickness
        clearance = config.clearance.shell
        width, depth, outer_bottom, outer_top = self._outer_bounds()

        # Full-height shell from outer_bottom to outer_top, open at −Z
        # (toward the base).  The +Z face stays solid; a pocket is cut into
        # it below for the bezel.
        total_height = outer_top - outer_bottom
        outer = cq_helpers.box_centered(width, depth, total_height)
        outer = cq_helpers.translate(outer, 0.0, 0.0, (outer_top + outer_bottom) / 2.0)
        outer = fillet.fillet_corners(outer, config.corners.radius)
        # Chamfer the bottom perimeter edges (before shelling so the rim
        # stays full thickness).
        outer = outer.faces("<Z").edges().chamfer(2.0)
        body = shell.offset_shell(outer, wall, open_face="<Z")

        # Rectangular pocket on the +Z face for the bezel.
        # The pocket is bezel_thickness deep; the bezel fills it flush.
        pocket_w = width - 2 * wall
        pocket_d = depth - 2 * wall
        pocket = cq_helpers.box_centered(
            pocket_w, pocket_d, self.bezel_thickness + 2 * clearance
        )
        pocket = cq_helpers.translate(
            pocket, 0.0, 0.0, outer_top - self.bezel_thickness / 2.0
        )
        body = body.cut(pocket)

        # Bosses at the 4 corners for bezel mounting.
        # Each boss is a cylinder with a pilot hole, sitting at the bottom
        # of the pocket (supporting the bezel from below).
        screw = fasteners.screw("M2.5")
        sleeve = 1.2
        boss_od = screw.clearance + 2 * sleeve
        boss_h = self.bezel_thickness + wall
        boss_z = outer_top - self.bezel_thickness - boss_h / 2.0

        for cx, cy in self._corner_positions():
            boss = cq_helpers.cylinder_centered(boss_od, boss_h)
            boss = cq_helpers.translate(boss, cx, cy, boss_z)
            bore = cq_helpers.cylinder_centered(screw.pilot_hole, boss_h + 1.0)
            bore = cq_helpers.translate(bore, cx, cy, boss_z)
            body = body.union(boss.cut(bore))

        return body

    def build_bezel(self):
        """Generate the lid bezel solid (front plate with glass cutout).

        A thin plate that sits *inside* the lid_base opening (XY = interior
        dimensions) so its front face is flush with the lid_base shell walls.
        Has a centered glass cutout and four M2.5 clearance holes at the
        corners.

        Returns
        -------
        cadquery.Workplane
            The lid bezel solid.
        """
        from geometry import fillet
        from utilities import cq_helpers

        cq_helpers.require_cq()
        config = self.config
        wall = config.wall_thickness
        clearance = config.clearance.shell
        width, depth, _, outer_top = self._outer_bounds()

        # Bezel sits inside the lid_base opening: XY = interior dimensions.
        bezel_w = width - 2 * wall
        bezel_d = depth - 2 * wall

        bezel = cq_helpers.box_centered(bezel_w, bezel_d, self.bezel_thickness)
        bezel = cq_helpers.translate(
            bezel, 0.0, 0.0, outer_top - self.bezel_thickness / 2.0
        )
        bezel = fillet.fillet_corners(bezel, config.corners.radius)

        # Glass cutout through the bezel.
        # The cutout box is just 0.1 mm taller than the bezel so the chamfer
        # on its top edge lands within the bezel's thickness, creating a
        # 2 mm bevel on the inner front edge of the hole.
        recess = self.glass_recess()
        cut_h = self.bezel_thickness + 0.1
        cutout = cq_helpers.box_centered(
            recess["width"], recess["height"], cut_h
        )
        cutout = cq_helpers.translate(
            cutout, 0.0, 0.0, outer_top - cut_h / 2.0
        )
        cutout = cutout.faces("<Z").edges().chamfer(2.0)
        bezel = bezel.cut(cutout)

        # M2.5 clearance holes at the 4 corners.
        screw = fasteners.screw("M2.5")
        for cx, cy in self._corner_positions():
            hole = cq_helpers.cylinder_centered(
                screw.clearance, self.bezel_thickness + 2 * clearance
            )
            hole = cq_helpers.translate(
                hole, cx, cy, outer_top - self.bezel_thickness / 2.0
            )
            bezel = bezel.cut(hole)

        return bezel
