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

from dataclasses import dataclass
from typing import Any

from components.base import BoundingBox, Component
from geometry.boss import BossSpec, boss_spec
from layouts.base import Placement, volume_footprint, volume_z_span
from utilities.config_loader import Config


def select_placements(
    placements: list[Placement], keep: set[Component]
) -> list[Placement]:
    """Return the placements whose component is in ``keep``, in layout order.

    Identity-matches on the component objects so grouping never depends on
    component names. Used to build sub-assemblies (e.g. the display assembly:
    the panel and its HDMI driver) from a subset of the full placement set.
    """
    return [p for p in placements if p.component in keep]


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

        The XY envelope is sized symmetrically about the origin. Both shells
        are built with :func:`cad_helpers.box_centered` at the world origin,
        which is the center of the base by definition
        (``docs/coordinate_system.md``), so a raw min-to-max span would let an
        off-center layout report a case that does not actually contain it —
        the widest component would sit outside the wall on one side.
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
            # placement.box already folds in both the Z rotation and any
            # tilt_x, so a wedge-mounted part reports its true world extent.
            x0, y0, x1, y1 = placement.box
            xs.extend([x0, x1])
            ys.extend([y0, y1])
            z0, z1 = placement.z_bounds()
            zs.extend([z0, z1])

        width = 2 * max(abs(min(xs)), abs(max(xs))) + 2 * (clearance + wall)
        depth = 2 * max(abs(min(ys)), abs(max(ys))) + 2 * (clearance + wall)
        height = max(zs) - min(zs) + 2 * (clearance + wall)
        return EnclosureSize(width=width, depth=depth, height=height)

    def collisions(self) -> list[str]:
        """Return a list of overlapping placement descriptions (empty = clean).

        Two sub-volumes conflict only when they overlap in Z as well as XY:
        the lid stacks over the base, and parts sit in the hollow under the
        raised keyboard plate, so an XY-only test would report both as
        collisions.
        """
        from utilities.validation import _overlap_xy

        problems: list[str] = []
        for i in range(len(self.placements)):
            for j in range(i + 1, len(self.placements)):
                pa, pb = self.placements[i], self.placements[j]
                a, b = pa.component, pb.component
                for ax, ay, az, abox in a.occupied_volumes():
                    for bx, by, bz, bbox in b.occupied_volumes():
                        # World-frame volume centers (rotation + flip aware).
                        wx, wy, wz = pa.world_offset(ax, ay, az)
                        vx, vy, vz = pb.world_offset(bx, by, bz)
                        # Flipped components hang below their origin; a tilt
                        # swings depth into Z, widening both ranges.
                        a_z0, a_z1 = volume_z_span(pa, abox, wz)
                        b_z0, b_z1 = volume_z_span(pb, bbox, vz)
                        if a_z1 <= b_z0 or b_z1 <= a_z0:
                            continue
                        aw, ad = volume_footprint(pa, abox)
                        bw, bd = volume_footprint(pb, bbox)
                        if _overlap_xy(wx, wy, aw, ad, vx, vy, bw, bd):
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
                # Transform the hole into world space (rotation + flip aware).
                bx, by, _ = placement.world_offset(hole.x, hole.y, 0.0)
                result.append((bx, by, spec))
        return result

    def connector_cutout(
        self,
        placement: Placement,
        connector: Any,
        clearance: float | None = None,
    ) -> dict | None:
        """Return the shell cutout for one placed connector, or ``None``.

        ``None`` means the connector is internal (mates inside the case, no
        shell opening) or unreachable (its opening faces far from the
        nearest shell wall). Factored out of :meth:`connector_cutouts` so
        callers that already have a specific ``(placement, connector)`` pair
        — e.g. debug section-view tooling — can get its cutout without
        re-deriving the reach/direction math or scanning every placement.
        """
        from geometry.cutouts import from_connector

        if connector.internal:
            return None

        clearance = clearance if clearance is not None else self.config.clearance.shell
        wall = self.config.wall_thickness
        size = self.enclosure_size()
        half_w, half_d = size.width / 2, size.depth / 2
        box = placement.component.size()

        cutout = from_connector(connector, clearance)

        # World-space direction and origin after the placement's Z rotation
        # and optional X flip.
        direction = placement.world_direction(*connector.direction)
        cx, cy, cz = placement.world_offset(connector.x, connector.y, connector.z)
        wx, wy = direction[0], direction[1]

        # Distance from the connector origin to the wall outer face.
        # Determine the primary axis from the rotated direction (use a
        # tolerance for floating-point noise from sin(π)).
        if abs(wx) >= abs(wy):
            distance = (half_w - cx) if wx > 0.0 else (cx + half_w)
            reach = box.width / 2 + clearance + wall
        else:
            distance = (half_d - cy) if wy > 0.0 else (cy + half_d)
            reach = box.depth / 2 + clearance + wall
        if distance > reach:
            return None

        return {
            "type": cutout.connector_type,
            "x": cx,
            "y": cy,
            "z": cz,
            "width": cutout.width,
            "height": cutout.height,
            "direction": direction,
            "distance": distance,
        }

    def connector_cutouts(self, clearance: float | None = None) -> list:
        """Return the shell cutouts required by all placed connectors (mm).

        Internal connectors (``Connector.internal``) mate to parts inside the
        case and produce no shell cutout. Each remaining cutout is reach-aware:
        connectors whose opening faces far from the nearest shell wall (inside
        the case, unreachable from outside) are skipped, and the cutout box
        carries its world-space ``direction`` and wall ``distance`` so the
        shell pass can bore it through the wall.
        """
        cutouts = []
        for placement in self.placements:
            for connector in placement.component.connectors():
                cutout = self.connector_cutout(placement, connector, clearance)
                if cutout is not None:
                    cutouts.append(cutout)
        return cutouts

    def max_component_height(self) -> float:
        """Height of the highest component stack above z=0 (mm)."""
        return max(
            (placement.z_bounds()[1] for placement in self.placements),
            default=0.0,
        )

    def build(self):
        """Generate the assembled solid (all components in place).

        Unions every placed component's solid, transformed to its world
        placement (Z rotation first, then translation). See
        :meth:`build_subset` for the shared transform logic.

        Returns
        -------
        Shape
            The union of all component solids.
        """
        return self.build_subset(self.placements)

    def build_subset(self, placements: list[Placement]):
        """Generate the union solid for ``placements`` in their world frames.

        Each selected placement's solid is transformed to its world placement
        (Z rotation first, then optional 180° flip about X, then translation)
        and unioned into one compound. ``placements`` is any subset of the
        assembly's placements, so callers can build named sub-assemblies
        (e.g. the display assembly: panel + HDMI driver) without rebuilding
        the whole case.

        Returns
        -------
        Shape
            The union of the selected component solids.

        Raises
        ------
        ValueError
            ``placements`` is empty.
        """
        from utilities import cad_helpers

        parts = []
        for placement in placements:
            solid = placement.component.build()
            if placement.rotation:
                solid = cad_helpers.rotate_z(solid, placement.rotation)
            if placement.flip_x:
                solid = cad_helpers.rotate_x(solid, 180.0)
            if placement.tilt_x:
                solid = cad_helpers.rotate_x(solid, placement.tilt_x)
            solid = cad_helpers.translate(solid, placement.x, placement.y, placement.z)
            parts.append(solid)
        if not parts:
            raise ValueError("no placements to assemble")
        return cad_helpers.union(parts[0], *parts[1:])

    def build_colored(
        self,
        placements: list[Placement] | None = None,
        role_map: dict[int, str] | None = None,
        assembly: Any | None = None,
        extra_parts: list[tuple[str, Any]] | None = None,
    ):
        """Build a ``ColoredAssembly`` with one colored child per part.

        Unlike :meth:`build`/:meth:`build_subset`, which fuse everything into
        a single boolean solid, this keeps each component (and any
        ``extra_parts``, e.g. a case shell) as a separate named, colored
        child — for glTF export, where telling components and sub-assemblies
        apart by color is the point.

        Parameters
        ----------
        placements : list[Placement] or None
            Placements to add as colored components; defaults to the whole
            assembly's placements.
        role_map : dict[int, str] or None
            ``id(component) -> role`` (e.g. ``{id(sbc): "sbc"}``), used to
            look up each component's color in ``utilities.colors``. A
            component missing from the map falls back to its ``.name``,
            then to the palette's default color.
        assembly : ColoredAssembly or None
            Existing assembly to add children to; a new one is created if
            omitted (so callers can compose a case shell with components in
            one call, e.g. via ``extra_parts``).
        extra_parts : list[(str, shape)] or None
            Additional pre-built, already-world-positioned solids to add as
            colored children, keyed by role/name (e.g.
            ``[("case", base_shell_solid)]``).

        Returns
        -------
        ColoredAssembly
        """
        from utilities import cad_helpers
        from utilities.colors import color_for

        placements = self.placements if placements is None else placements
        role_map = role_map or {}
        assy = assembly if assembly is not None else cad_helpers.new_assembly()

        for placement in placements:
            solid = placement.component.build()
            if placement.rotation:
                solid = cad_helpers.rotate_z(solid, placement.rotation)
            if placement.flip_x:
                solid = cad_helpers.rotate_x(solid, 180.0)
            if placement.tilt_x:
                solid = cad_helpers.rotate_x(solid, placement.tilt_x)
            solid = cad_helpers.translate(solid, placement.x, placement.y, placement.z)
            role = role_map.get(id(placement.component), placement.component.name)
            cad_helpers.assembly_add(assy, solid, placement.component.name, color_for(role))

        for role, solid in extra_parts or []:
            cad_helpers.assembly_add(assy, solid, role, color_for(role))

        return assy
