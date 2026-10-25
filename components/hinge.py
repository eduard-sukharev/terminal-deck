"""Purchased Torque hinges (ADR 0007), described in config; the case adapts.

A Torque hinge is a barrel on the Hinge axis and two Leaves, each a flat
plate with screw holes. It is described in its own frame (the *hinge
frame*), closed:

* the Hinge axis along X through the origin, the hinge centred on ``x = 0``
* ``+Y`` toward the case interior; a Leaf runs from ``start`` to
  ``start + length`` along Y
* the Base leaf below the axis, its near face ``offset`` under it; the Lid
  leaf above, its near face ``offset`` over it; both ``leaf_thickness`` thick
* each hole at ``u`` from the axis along the Leaf and ``v`` from the Leaf's
  centre along X

Two hinges, the left the mirror of the right about the case centerline (a
hole's ``v`` flips with it). The case derives the rest: the axis sits
``setback`` behind the rear face, clear of the barrel and the Cable guard
for the Lid's whole swing; each Leaf gets a pocket and a pad with a heat-set
insert per hole, the pad reaching from the Leaf to the shell's surface.

The hinge turns further than is comfortable, so a travel stop holds the Lid
at ``travel``: a rib on the Deck outboard of each barrel, standing on the
Parting plane behind the rear face, whose face lies on the Lid's rear face
turned by ``travel``. The Lid never comes nearer the axis than ``setback``,
so the rib may fill everything inside that radius; elsewhere it keeps to
where no part of the Lid passes before ``travel``.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from components.base import BoundingBox, Component
from utilities import fasteners

SIDES = ("left", "right")
LEAVES = ("base", "lid")


@dataclass(frozen=True)
class LeafHole:
    u: float          # from the axis along the Leaf (mm)
    v: float          # from the Leaf's centre along X, right hinge (mm)
    diameter: float


@dataclass(frozen=True)
class Leaf:
    offset: float     # axis to the Leaf's near face (mm)
    start: float      # axis to the Leaf's inner end, along the Leaf (mm)
    length: float
    width: float      # along X
    holes: tuple[LeafHole, ...]


@dataclass(frozen=True)
class TorqueHinge:
    """One purchased hinge, in its own frame."""

    name: str
    barrel_diameter: float
    barrel_length: float
    leaf_thickness: float
    leaves: dict[str, Leaf]

    @classmethod
    def from_config(cls, data: dict[str, Any]) -> "TorqueHinge":
        leaves = {}
        for which in LEAVES:
            raw = data["leaves"][which]
            leaf = Leaf(
                offset=float(raw["offset"]), start=float(raw["start"]),
                length=float(raw["length"]), width=float(raw["width"]),
                holes=tuple(LeafHole(float(u), float(v), float(d)) for u, v, d in raw["holes"]),
            )
            for h in leaf.holes:
                r = h.diameter / 2.0
                inside = (
                    leaf.start + r <= h.u <= leaf.start + leaf.length - r
                    and abs(h.v) + r <= leaf.width / 2.0
                )
                if not inside:
                    raise ValueError(f"{which} leaf hole at u={h.u:g}, v={h.v:g} lies outside its leaf")
            leaves[which] = leaf
        return cls(
            name=str(data.get("name", "torque hinge")),
            barrel_diameter=float(data["barrel_diameter"]),
            barrel_length=float(data["barrel_length"]),
            leaf_thickness=float(data["leaf_thickness"]),
            leaves=leaves,
        )


class Hinge(Component):
    """The pair of Torque hinges and how the case takes them."""

    name = "Torque hinge"

    def __init__(self, cfg: Any, wall_thickness: float = 2.0, guard: Any = None) -> None:
        self.x = float(cfg.x)
        self.travel = float(cfg.travel)
        self.swing_clearance = float(cfg.swing_clearance)
        self.fit = float(cfg.fit)
        self.insert_size = str(cfg.insert)
        self.part = TorqueHinge.from_config(cfg.part)
        self.wall_thickness = wall_thickness
        self.guard = guard
        stop = getattr(cfg, "stop", None)
        self.has_stop = stop is not None
        self.stop_width = float(stop["width"]) if stop else 0.0
        self.stop_face = float(stop["face"]) if stop else 0.0
        if self.has_stop and not 90.0 < self.travel < 180.0:
            raise ValueError(f"hinge: a travel stop needs a travel between 90 and 180 deg, not {self.travel:g}")

    def size(self) -> BoundingBox:
        p = self.part
        reach = max(l.start + l.length for l in p.leaves.values())
        return BoundingBox(p.barrel_length, reach, p.barrel_diameter)

    # -- layout -------------------------------------------------------------------

    def centers(self) -> tuple[float, float]:
        return (-self.x, self.x)

    @staticmethod
    def _mirror(side: str) -> float:
        return -1.0 if side == "left" else 1.0

    def center(self, side: str) -> float:
        return self._mirror(side) * self.x

    @property
    def setback(self) -> float:
        """How far the Hinge axis sits behind the case rear face (mm): the
        barrel and the Cable guard swing on the axis clear of the shells."""
        reach = self.part.barrel_diameter / 2.0
        if self.guard is not None:
            reach = max(reach, self.guard.outer_radius)
        return reach + self.swing_clearance

    def leaf_z(self, which: str) -> tuple[float, float]:
        """(z0, z1) of a Leaf in the hinge frame, closed."""
        leaf, t = self.part.leaves[which], self.part.leaf_thickness
        return (-leaf.offset - t, -leaf.offset) if which == "base" else (leaf.offset, leaf.offset + t)

    def leaf_rect(self, which: str, rear_y: float, side: str) -> tuple[float, float, float, float]:
        """World XY ``(x0, x1, y0, y1)`` of a Leaf, the case rear face at ``rear_y``."""
        leaf = self.part.leaves[which]
        cx = self.center(side)
        y0 = rear_y - self.setback + leaf.start
        return (cx - leaf.width / 2.0, cx + leaf.width / 2.0, y0, y0 + leaf.length)

    def pad_rect(self, which: str, rear_y: float, side: str) -> tuple[float, float, float, float]:
        """World XY of a Leaf's pad: the Leaf a wall wider all round, inside
        the case (from the rear face in)."""
        x0, x1, y0, y1 = self.leaf_rect(which, rear_y, side)
        w = self.wall_thickness
        return (x0 - w, x1 + w, max(y0 - w, rear_y), y1 + w)

    def holes(self, which: str, rear_y: float, side: str) -> list[tuple[float, float, float]]:
        """World ``(x, y, diameter)`` of a Leaf's holes."""
        cx, m = self.center(side), self._mirror(side)
        axis_y = rear_y - self.setback
        return [(cx + m * h.v, axis_y + h.u, h.diameter) for h in self.part.leaves[which].holes]

    def insert(self) -> fasteners.HeatInsert:
        return fasteners.heat_insert(self.insert_size)

    def screw_count(self) -> int:
        return len(SIDES) * sum(len(l.holes) for l in self.part.leaves.values())

    # -- checks ---------------------------------------------------------------------

    def _lid_outline(self, lid_depth: float, lid_height: float, setback: float, step: float = 1.0):
        """Points on the closed Lid's side profile and its Leaf (hinge frame)."""
        pts = []
        n_y = max(2, int(lid_depth / step) + 1)
        n_z = max(2, int(lid_height / step) + 1)
        for i in range(n_y):
            y = setback + lid_depth * i / (n_y - 1)
            pts += [(y, 0.0), (y, lid_height)]
        for j in range(n_z):
            z = lid_height * j / (n_z - 1)
            pts += [(setback, z), (setback + lid_depth, z)]
        leaf = self.part.leaves["lid"]
        z0, z1 = self.leaf_z("lid")
        for y in (leaf.start, leaf.start + leaf.length):
            pts += [(y, z0), (y, z1)]
        return pts

    def sweep_hits(
        self, lid_depth: float, lid_height: float,
        setback: float | None = None, travel: float | None = None, step: float = 1.0,
    ) -> list[tuple[float, float, float]]:
        """Points of the Lid that enter the Base while it opens (side profile).

        The Lid turns about the axis by ``theta`` in ``[0, travel]``; the Base
        fills ``y >= setback`` below ``z = 0`` (hinge frame). Returns
        ``(theta, y, z)`` of every hit; empty when the swing is clear.
        """
        setback = self.setback if setback is None else setback
        travel = self.travel if travel is None else travel
        pts = self._lid_outline(lid_depth, lid_height, setback)
        hits = []
        n = max(2, int(travel / step) + 1)
        for k in range(n):
            th = math.radians(travel * k / (n - 1))
            c, s = math.cos(th), math.sin(th)
            for y, z in pts:
                yy, zz = y * c - z * s, y * s + z * c
                if zz < -1e-6 and yy > setback - self.swing_clearance:
                    hits.append((math.degrees(th), yy, zz))
        return hits

    # -- travel stop ----------------------------------------------------------------

    def stop_span(self, side: str) -> tuple[float, float]:
        """(x0, x1) of a side's stop rib: outboard of its barrel, clear of the
        Lid leaf turning with it."""
        inner = self.x + self.part.barrel_length / 2.0 + self.swing_clearance
        outer = inner + self.stop_width
        return (-outer, -inner) if side == "left" else (inner, outer)

    def stop_profile(self, parting: float, setback: float | None = None) -> list[tuple[float, float]]:
        """The stop rib's side profile (hinge frame ``(y, z)``), face first.

        The face runs from the Lid's inner rear edge, turned by ``travel``,
        ``face`` mm along the Lid's rear face; the rib drops from there to the
        Parting plane, runs into the Deck's rear wall, and returns just below
        the closed plane and back through the axis region inside ``setback``,
        where the Lid never reaches.
        """
        s = self.setback if setback is None else setback
        th = math.radians(self.travel)
        ty, tz = math.cos(th), math.sin(th)        # along the Lid, turned
        ny, nz = -math.sin(th), math.cos(th)       # across it, toward its back
        q0 = (s * ty, s * tz)
        q1 = (q0[0] + self.stop_face * ny, q0[1] + self.stop_face * nz)
        root = s + self.wall_thickness             # into the Deck's rear wall
        below = -self.swing_clearance              # clear of the closed Lid
        return [q0, q1, (q1[0], parting), (root, parting), (root, below), (0.0, below)]

    @staticmethod
    def _inside(y: float, z: float, poly: list[tuple[float, float]], tol: float = 1e-6) -> bool:
        """Strictly inside ``poly`` (points within ``tol`` of an edge are not)."""
        n, inside = len(poly), False
        for i in range(n):
            (ay, az), (by, bz) = poly[i], poly[(i + 1) % n]
            dy, dz = by - ay, bz - az
            ln = math.hypot(dy, dz)
            if ln > 0.0:
                t = max(0.0, min(1.0, ((y - ay) * dy + (z - az) * dz) / ln ** 2))
                if math.hypot(y - ay - t * dy, z - az - t * dz) <= tol:
                    return False
            if (az > z) != (bz > z) and y < ay + (z - az) * dy / dz:
                inside = not inside
        return inside

    def stop_hits(
        self, lid_depth: float, lid_height: float, parting: float,
        profile: list[tuple[float, float]] | None = None, step: float = 1.0,
    ) -> list[tuple[float, float, float]]:
        """Points of the Lid's side profile inside the stop rib while it opens
        to ``travel`` (exclusive): ``(theta, y, z)``; empty when it lands only
        at ``travel``."""
        poly = self.stop_profile(parting) if profile is None else profile
        pts = self._lid_outline(lid_depth, lid_height, self.setback, step)
        n = max(2, int(self.travel / step) + 1)
        hits = []
        for k in range(n - 1):
            th = math.radians(self.travel * k / (n - 1))
            c, s = math.cos(th), math.sin(th)
            for y, z in pts[: -4]:  # the Lid leaf turns inside the barrel's X span
                yy, zz = y * c - z * s, y * s + z * c
                if self._inside(yy, zz, poly):
                    hits.append((math.degrees(th), yy, zz))
        return hits

    def build_stop(self, side: str, parting: float):
        """A side's stop rib (hinge frame, X in world)."""
        from utilities import cad_helpers

        x0, x1 = self.stop_span(side)
        rib = cad_helpers.extrude_profile_x(self.stop_profile(parting), x1 - x0)
        return cad_helpers.translate(rib, (x0 + x1) / 2.0, 0.0, 0.0)

    def insert_room(self, which: str, outer: float, minimum_feature: float) -> float:
        """Depth an insert can take from a Leaf's mounting face toward the
        shell's outer surface at hinge-frame ``outer``, less a printable skin."""
        z0, z1 = self.leaf_z(which)
        face = z1 if outer >= z1 else z0
        return abs(outer - face) - minimum_feature

    # -- geometry (hinge frame, X in world) ---------------------------------------

    def _box(self, x0, x1, y0, y1, z0, z1):
        from utilities import cad_helpers

        return cad_helpers.translate(
            cad_helpers.box_centered(x1 - x0, y1 - y0, z1 - z0),
            (x0 + x1) / 2.0, (y0 + y1) / 2.0, (z0 + z1) / 2.0,
        )

    def _x_cylinder(self, diameter: float, x0: float, x1: float):
        from utilities import cad_helpers

        body = cad_helpers.rotate_y(cad_helpers.cylinder_centered(diameter, x1 - x0), 90)
        return cad_helpers.translate(body, (x0 + x1) / 2.0, 0.0, 0.0)

    def _leaf_with_web(self, which: str, side: str, grow: float = 0.0):
        """A Leaf and the web joining it to the barrel, grown by ``grow``."""
        from utilities import cad_helpers

        leaf = self.part.leaves[which]
        cx = self.center(side)
        x0, x1 = cx - leaf.width / 2.0 - grow, cx + leaf.width / 2.0 + grow
        z0, z1 = self.leaf_z(which)
        plate = self._box(x0, x1, leaf.start - grow, leaf.start + leaf.length + grow, z0 - grow, z1 + grow)
        t = self.part.leaf_thickness
        web_y = leaf.start + t
        if which == "base":
            web = self._box(x0, x1, leaf.start - grow, web_y + grow, z0 - grow, 0.0)
        else:
            web = self._box(x0, x1, leaf.start - grow, web_y + grow, 0.0, z1 + grow)
        return cad_helpers.union(plate, web)

    def build_part(self, side: str, opened: float = 0.0):
        """One Torque hinge: barrel, both Leaves and their webs, the Lid leaf
        turned ``opened`` deg about the axis (0 = closed)."""
        from utilities import cad_helpers

        cx, half = self.center(side), self.part.barrel_length / 2.0
        barrel = self._x_cylinder(self.part.barrel_diameter, cx - half, cx + half)
        lid = cad_helpers.rotate_x(self._leaf_with_web("lid", side), opened)
        return cad_helpers.union(barrel, self._leaf_with_web("base", side), lid)

    def build_pocket(self, which: str, side: str):
        """The void a Leaf, its web and the barrel take in a shell (``fit`` all round)."""
        from utilities import cad_helpers

        cx, half = self.center(side), self.part.barrel_length / 2.0 + self.fit
        barrel = self._x_cylinder(self.part.barrel_diameter + 2 * self.fit, cx - half, cx + half)
        return cad_helpers.union(barrel, self._leaf_with_web(which, side, grow=self.fit))

    def build_pad(self, which: str, side: str, support: float, setback: float | None = None, bored: bool = True):
        """The pad between a Leaf and the shell surface at hinge-frame ``support``.

        The pad is the Leaf's footprint a wall wider all round, inside the case
        (``y >= setback``), from the Leaf's face toward the shell; each hole
        gets an insert bore from that face.
        """
        from utilities import cad_helpers

        setback = self.setback if setback is None else setback
        leaf, w = self.part.leaves[which], self.wall_thickness
        cx = self.center(side)
        z0, z1 = self.leaf_z(which)
        lo, hi = (z1, support) if support >= z1 else (support, z0)
        pad = self._box(
            cx - leaf.width / 2.0 - w, cx + leaf.width / 2.0 + w,
            max(leaf.start - w, setback), leaf.start + leaf.length + w, lo, hi,
        )
        if bored:
            pad = cad_helpers.cut(pad, self.build_insert_bores(which, side, support))
        return pad

    def build_insert_bores(self, which: str, side: str, support: float):
        """An insert bore per hole, from the Leaf's mounting face into the pad."""
        from utilities import cad_helpers

        insert = self.insert()
        z0, z1 = self.leaf_z(which)
        face, sign = (z1, 1.0) if support >= z1 else (z0, -1.0)
        # Starts ``fit`` inside the Leaf's pocket so the cut opens cleanly.
        depth = insert.depth + self.fit
        m, cx = self._mirror(side), self.center(side)
        bores = []
        for h in self.part.leaves[which].holes:
            bore = cad_helpers.cylinder_centered(insert.printed_hole_diameter, depth)
            bores.append(cad_helpers.translate(bore, cx + m * h.v, h.u, face + sign * (depth / 2.0 - self.fit)))
        return cad_helpers.union(*bores)

    def build(self, opened: float = 0.0):
        """Both Torque hinges in the hinge frame, opened ``opened`` deg."""
        from utilities import cad_helpers

        return cad_helpers.union(*[self.build_part(s, opened) for s in SIDES])
