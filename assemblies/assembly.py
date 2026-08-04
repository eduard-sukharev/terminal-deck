"""Assembly: resolves placements into a consistent whole.

The assembly consumes placed components and computes:

* enclosure size (from bounding boxes + wall thickness + clearances)
* collisions and cable clearance
* connector accessibility (cutout list)
* mounting bosses (from component mounting holes)

CAD generation of the assembly is deferred (:meth:`Assembly.build`); all
data-side math here is implemented.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from components.base import BoundingBox, Component
from geometry.boss import BossSpec, boss_spec
from layouts.base import Placement
from utilities.config_loader import Config


@dataclass(frozen=True)
class EnclosureSize:
    """Overall envelope of the closed case (mm)."""

    width: float
    depth: float
    height: float


class Assembly:
    """Resolves a set of placements into enclosure-driving geometry."""

    def __init__(self, placements: list[Placement], config: Config) -> None:
        self.placements = placements
        self.config = config

    def enclosure_size(self) -> EnclosureSize:
        """Overall envelope of the base + lid around all placements (mm).

        Calculated from the placement footprint plus the shell clearance and
        wall thickness — never guessed.
        """
        wall = self.config.wall_thickness
        clearance = self.config.clearance.shell

        if not self.placements:
            return EnclosureSize(2 * wall, 2 * wall, 2 * wall)

        xs: list[float] = []
        ys: list[float] = []
        zs: list[float] = []
        for placement in self.placements:
            box = placement.component.size()
            # Rotation about Z swaps footprint width/depth (axis-aligned bound).
            rad = math.radians(placement.rotation)
            half_w = abs(box.width * math.cos(rad)) / 2 + abs(box.depth * math.sin(rad)) / 2
            half_d = abs(box.width * math.sin(rad)) / 2 + abs(box.depth * math.cos(rad)) / 2
            xs.extend([placement.x - half_w, placement.x + half_w])
            ys.extend([placement.y - half_d, placement.y + half_d])
            zs.extend([placement.z, placement.z + box.height])

        width = max(xs) - min(xs) + 2 * (clearance + wall)
        depth = max(ys) - min(ys) + 2 * (clearance + wall)
        height = max(zs) - min(zs) + 2 * (clearance + wall)
        return EnclosureSize(width=width, depth=depth, height=height)

    def collisions(self) -> list[str]:
        """Return a list of overlapping placement descriptions (empty = clean)."""
        from utilities.validation import _overlap_xy

        problems: list[str] = []
        for i in range(len(self.placements)):
            for j in range(i + 1, len(self.placements)):
                pa, pb = self.placements[i], self.placements[j]
                a, b = pa.component, pb.component
                if _overlap_xy(
                    pa.x, pa.y, a.size().width, a.size().depth,
                    pb.x, pb.y, b.size().width, b.size().depth,
                ):
                    problems.append(f"{a.name} overlaps {b.name}")
        return problems

    def bosses(self, placements: list[Placement] | None = None) -> list[tuple[float, float, BossSpec]]:
        """Return mounting bosses for every component with mounting holes.

        Each entry is ``(x, y, BossSpec)`` in the world frame (mm). Bosses are
        generated only for holes that sit over a wall (checked upstream).
        Pass ``placements`` to restrict to a subset (e.g. base-floor or
        lid-side components only).
        """
        wall = self.config.wall_thickness
        default_screw = self.config.screws.standoff

        selected = placements if placements is not None else self.placements
        result: list[tuple[float, float, BossSpec]] = []
        for placement in selected:
            component: Component = placement.component
            screw_size = component.mounting_screw() or default_screw
            for hole in component.mounting_holes():
                spec = boss_spec(
                    wall_thickness=wall,
                    screw_size=screw_size,
                    insert_type=screw_size,
                    hole_diameter=hole.diameter,
                    height=hole.height,
                )
                result.append((placement.x + hole.x, placement.y + hole.y, spec))
        return result

    def connector_cutouts(self, clearance: float | None = None) -> list:
        """Return the shell cutouts required by all placed connectors (mm).

        Internal connectors (``Connector.internal``) mate to parts inside the
        case and produce no shell cutout. Each remaining cutout is reach-aware:
        connectors whose opening faces far from the nearest shell wall (inside
        the case, unreachable from outside) are skipped, and the cutout box
        carries its world-space ``direction`` and wall ``distance`` so the
        shell pass can bore it through the wall.
        """
        from geometry.cutouts import from_connector

        clearance = clearance if clearance is not None else self.config.clearance.shell
        wall = self.config.wall_thickness
        size = self.enclosure_size()
        half_w, half_d = size.width / 2, size.depth / 2

        cutouts = []
        for placement in self.placements:
            component: Component = placement.component
            rad = math.radians(placement.rotation)
            box = component.size()
            for connector in component.connectors():
                if connector.internal:
                    continue
                cutout = from_connector(connector, clearance)

                # World-space direction after the placement's Z rotation.
                wx = connector.direction[0] * math.cos(rad) - connector.direction[1] * math.sin(rad)
                wy = connector.direction[0] * math.sin(rad) + connector.direction[1] * math.cos(rad)
                direction = (wx, wy, connector.direction[2])

                # Distance from the connector origin to the wall outer face.
                px, py = placement.x + cutout.x, placement.y + cutout.y
                if wx > 0.0:
                    distance = half_w - px
                elif wx < 0.0:
                    distance = px + half_w
                elif wy > 0.0:
                    distance = half_d - py
                elif wy < 0.0:
                    distance = py + half_d
                else:
                    distance = 0.0

                # Reach check: the connector must be near the shell boundary.
                # Half-extent along the connector axis plus the shell gap.
                if abs(direction[0]) >= abs(direction[1]):
                    reach = box.width / 2 + clearance + wall
                else:
                    reach = box.depth / 2 + clearance + wall
                if distance > reach:
                    continue

                cutouts.append(
                    {
                        "type": cutout.connector_type,
                        "x": placement.x + cutout.x,
                        "y": placement.y + cutout.y,
                        "z": placement.z + cutout.z,
                        "width": cutout.width,
                        "height": cutout.height,
                        "direction": direction,
                        "distance": distance,
                    }
                )
        return cutouts

    def max_component_height(self) -> float:
        """Height of the highest component stack above z=0 (mm)."""
        return max(
            (placement.z + placement.component.size().height for placement in self.placements),
            default=0.0,
        )

    def build(self):
        """Generate the assembled solid (all components in place).

        Unions every placed component's solid, transformed to its world
        placement (Z rotation first, then translation).

        Returns
        -------
        cadquery.Workplane
            The union of all component solids.
        """
        from utilities import cq_helpers

        cq_helpers.require_cq()
        parts = []
        for placement in self.placements:
            solid = placement.component.build()
            if placement.rotation:
                solid = cq_helpers.rotate_z(solid, placement.rotation)
            solid = cq_helpers.translate(solid, placement.x, placement.y, placement.z)
            parts.append(solid)
        if not parts:
            raise ValueError("no placements to assemble")
        result = parts[0]
        for part in parts[1:]:
            result = result.union(part)
        return result
