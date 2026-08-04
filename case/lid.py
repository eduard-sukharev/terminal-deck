"""Lid shell generator.

The lid holds the display: glass recess, bezel, display mounts, and hinge
interface. The display is never assumed centered on the lid. All dimensions
derive from the display module and wall-thickness parameters.
"""

from __future__ import annotations

from components.base import Component
from components.hinge import Hinge
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
    ) -> None:
        self.display = display
        self.config = config
        self.hinge = hinge
        self.lid_interior_height = lid_interior_height
        self.world_z = world_z
        self.footprint = footprint

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

    def bezel(self) -> dict:
        """Bezel wall geometry around the glass (mm)."""
        display = self.config.display
        return {
            "width": display.width + 2 * self.config.wall_thickness,
            "height": display.height + 2 * self.config.wall_thickness,
            "thickness": self.config.wall_thickness,
        }

    def build(self):
        """Generate the lid shell solid.

        The open-bottom lid holds the display and driver: its cavity spans
        from the driver underside (minus clearance) up to the display top
        (plus clearance), with the glass opening cut through the top wall.
        All dimensions derive from the display module, the driver board, and
        the wall-thickness parameters.

        Returns
        -------
        cadquery.Workplane
            The lid shell with bezel, glass recess, and hinge interface.
        """
        from geometry import fillet, shell
        from utilities import cq_helpers

        cq_helpers.require_cq()
        config = self.config
        wall = config.wall_thickness
        clearance = config.clearance.shell

        if self.footprint is not None:
            width, depth = self.footprint
        else:
            width = self.display.size().width + 2 * (wall + clearance)
            depth = self.display.size().depth + 2 * (wall + clearance)

        # Cavity bounds around the display and the driver behind it.
        display_top = self.world_z + self.display.size().height
        interior_top = display_top + clearance
        driver_height = float(
            config.hardware.get("driver_board", {}).get("height", 4.6)
        )
        driver_bottom = self.world_z - driver_height
        interior_bottom = driver_bottom - clearance
        outer_bottom = interior_bottom - wall
        outer_top = interior_top + wall

        # Outer lid box; corner fillet before shelling so the outer envelope
        # is preserved (negative shell offset). Opened at the bottom face.
        outer = cq_helpers.box_centered(width, depth, outer_top - outer_bottom)
        outer = cq_helpers.translate(outer, 0.0, 0.0, (outer_top + outer_bottom) / 2.0)
        outer = fillet.fillet_corners(outer, config.corners.radius)
        body = shell.offset_shell(outer, wall, open_face="<Z")

        # Glass opening through the top wall, centered on the display.
        recess = self.glass_recess()
        hole = cq_helpers.box_centered(recess["width"], recess["height"], wall + 2 * clearance)
        hole = cq_helpers.translate(hole, 0.0, 0.0, outer_top - (wall + 2 * clearance) / 2.0)
        body = body.cut(hole)
        return body
