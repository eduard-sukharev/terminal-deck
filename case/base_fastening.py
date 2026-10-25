"""Base fastening: the Parting plane, Deck columns, Seam bands and lugs.

Everything here is pure data (no CAD library): where the Deck meets the Tray,
where the Deck screws go, where the Seams run and which structural features
they must keep clear of. :class:`BaseFastening` is a mixin for
:class:`case.base.Base`, which builds the solids from these answers.

Terms (see ``CONTEXT.md`` and ADR 0003): the **Parting plane** is the
horizontal plane the Tray top and the Deck bottom are both cut to; a
**column** is a Tray post, counterbored from the floor, that the Deck screw
runs up through into a heat-set insert in a **Deck boss**; a **Seam** joins
Sections of one part; each Torque hinge's Base leaf screws into a pad on the
Deck (ADR 0007).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from geometry import merged_boss, seam_joint
from geometry.boss import BossSpec
from geometry.merged_boss import WallBounds
from geometry.parting import deck_screw, parting_height
from geometry.spot_search import drop_close, nearest_free_spot
from utilities import fasteners
from utilities.validation import Feature, seam_bands

#: Sleeve of material round a column's counterbore (mm); same as ``boss_spec``.
COLUMN_SLEEVE = 1.2


@dataclass(frozen=True)
class Column:
    """One Deck fastening point: a Tray column and the Deck boss above it.

    ``x``/``y`` are world XY (mm). ``height`` is the column's run from the
    inner floor (z = 0) up to the Parting plane; ``deck_boss_height`` the Deck
    boss's run from the Parting plane up to the Deck's underside at that spot.
    ``walls`` are the walls it is merged into (empty for a free column).
    """

    x: float
    y: float
    spec: BossSpec
    bore_diameter: float
    counterbore_diameter: float
    counterbore_depth: float
    insert_diameter: float
    insert_depth: float
    height: float
    deck_boss_height: float
    walls: tuple[str, ...]

    @property
    def outer_diameter(self) -> float:
        return self.spec.outer_diameter

    @property
    def base_diameter(self) -> float:
        return self.spec.base_diameter


class BaseFastening:
    """Mixin giving :class:`case.base.Base` its fastening data.

    Expects the host to provide ``assembly``, ``config``, ``size()``,
    ``deck_level_at()``, ``deck_level()``, ``_base_placements()``,
    ``cutouts()``, ``foot_positions()``, ``_keyboard_placement()`` and
    ``_memo`` (a dict).
    """

    # -- Parting plane and walls ------------------------------------------------

    def parting_height(self) -> float:
        """Height of the Parting plane above the inner floor (mm).

        The one source the Tray top and the Deck bottom are both cut to.
        """
        return parting_height(self.config.parting, self.deck_level())

    def wall_bounds(self) -> WallBounds:
        """Interior wall faces of the Base (mm)."""
        size = self.size()
        wall = self.config.wall_thickness
        return WallBounds(
            -size.width / 2 + wall, size.width / 2 - wall,
            -size.depth / 2 + wall, size.depth / 2 - wall,
        )

    # -- Seams ------------------------------------------------------------------

    def _split(self, part: str):
        return self.config.split.get(part)

    def seam_bands(self) -> dict[str, list[tuple[float, float, float, float]]]:
        """Seam bands of the Tray and the Deck, keyed ``"<part>:<index>"``."""
        splits = {p: self._split(p) for p in ("tray", "deck") if self._split(p) is not None}
        depths = {p: self.size().depth for p in splits}
        return seam_bands(splits, depths, self.config.wall_thickness)

    def _band_rects(self) -> list[tuple[float, float, float, float]]:
        return [r for rects in self.seam_bands().values() for r in rects]

    # -- Columns ----------------------------------------------------------------

    def _deck_fastener(self):
        return fasteners.screw(self.config.screws.deck), fasteners.heat_insert(self.config.screws.deck)

    def column_geometry(self) -> dict[str, float]:
        """Counterbore, bore and sleeve of a Deck column (mm), from the fastener library."""
        screw, insert = self._deck_fastener()
        counterbore = screw.head_diameter + self.config.clearance.screw
        return {
            "bore": screw.clearance,
            "counterbore": counterbore,
            # Head seat: the head's own depth plus a half-millimetre of slack.
            "counterbore_depth": screw.head_depth + 0.5,
            "outer": counterbore + 2 * COLUMN_SLEEVE,
            "insert": insert.printed_hole_diameter,
            "insert_depth": insert.depth,
        }

    def deck_screw_grip(self) -> float:
        """The Deck screw's run from head seat to the Parting plane (mm)."""
        wall = self.config.wall_thickness
        g = self.column_geometry()
        return self.parting_height() + wall - g["counterbore_depth"]

    def deck_screw(self):
        """The stock Deck screw (raises ``ValueError`` if none engages)."""
        return deck_screw(self.config.screws.deck, self.deck_screw_grip())

    def _column_keepouts(self):
        """Everything a column must clear: ``(rect, margin)`` pairs plus circles."""
        z_top = self.parting_height()
        margin = self.config.clearance.screw
        rects = [
            (r, margin) for r in self.assembly.keepout_rects(0.0, z_top, self._base_placements())
        ]
        rects += [(r, margin) for r in self.cradle_rects()]
        rects += [(r, margin) for r in self.cutout_rects()]
        rects += [(r, margin) for r in self.cable_runs()]
        # The Deck boss needs Deck material above it: stay out of the keyboard
        # opening, with a printable sliver of Deck beside it.
        kb = self._keyboard_placement()
        if kb is not None:
            ks = kb.component.size()
            clr = self.config.clearance.shell
            rects.append((
                (kb.x - ks.width / 2 - clr, kb.x + ks.width / 2 + clr,
                 kb.y - ks.depth / 2 - clr, kb.y + ks.depth / 2 + clr),
                self.config.material.minimum_feature,
            ))
        circles = [
            (bx, by, spec.base_diameter / 2.0 + margin)
            for bx, by, spec in self.assembly.bosses(self._base_placements())
        ]
        return rects, circles

    def cable_runs(self) -> list[tuple[float, float, float, float]]:
        """XY strips ``(x0, x1, y0, y1)`` kept free for ribbon cables (mm).

        The mini-HDMI cable leaving the SBC is a flat FPC routed to the hinge
        tunnel: past its plug it may lie over the hub or fold sideways, which
        no placement models. Its strip runs from the plug's back to the rear
        wall, the plug's width plus a shell clearance either side, and keeps
        Deck columns out of the way.
        """
        from components.hdmi_plug import MiniHdmiPlug

        clr = self.config.clearance.shell
        rear = self.wall_bounds().y0
        runs = []
        # All placements: the plug rides its host's connector height, above the
        # ``_base_placements`` floor threshold (the driver-side plug is in the Lid).
        for p in self.assembly.placements:
            if isinstance(p.component, MiniHdmiPlug) and p.z_bounds()[1] < self.parting_height():
                x0, y0, x1, _ = p.box
                runs.append((x0 - clr, x1 + clr, rear, y0))
        return runs

    def _column_flare_extra(self) -> float:
        """How far the column's floor flare reaches beyond its post (mm)."""
        g = self.column_geometry()
        spec = BossSpec(
            hole_diameter=g["counterbore"], outer_diameter=g["outer"],
            height=self.parting_height(), wall_thickness=self.config.wall_thickness,
        )
        return (spec.base_diameter - spec.outer_diameter) / 2.0

    def _column_conflict_test(self, radius: float, head_radius: float):
        """``conflicts(cx, cy) -> bool`` for a column of outer ``radius``."""
        rects, circles = self._column_keepouts()
        # Seam bands are cleared by the column's widest footprint (the flare at
        # the floor), as a square: the same footprint the Seam clearance check
        # compares, so the two cannot disagree at a band's corner.
        half = radius + self._column_flare_extra()
        bands = self._band_rects()
        feet = [(fx, fy, self.config.feet.diameter / 2.0) for fx, fy in self.foot_positions()]
        head_gap = self.config.clearance.screw

        def conflicts(cx: float, cy: float) -> bool:
            for (x0, x1, y0, y1), margin in rects:
                # A square footprint, like the boss-collision check compares.
                reach = radius + margin
                if cx + reach > x0 and cx - reach < x1 and cy + reach > y0 and cy - reach < y1:
                    return True
            for x0, x1, y0, y1 in bands:
                if cx + half > x0 and cx - half < x1 and cy + half > y0 and cy - half < y1:
                    return True
            for bx, by, br in circles:
                if math.hypot(cx - bx, cy - by) < radius + br:
                    return True
            for fx, fy, fr in feet:
                if math.hypot(cx - fx, cy - fy) < head_radius + fr + head_gap:
                    return True
            return False

        return conflicts

    def _column_positions(self) -> list[tuple[float, float]]:
        """Deck column positions (mm, XY).

        Nominally the four corners plus three points on the rear inset line,
        each snapped to the nearest free spot. The Deck Seam needs none of its
        own: its Sections are pinned together (ADR 0006). A column may sit as
        close to a wall as a Merged boss's bore allows.
        """
        key = "column_positions"
        if key in self._memo:
            return self._memo[key]
        g = self.column_geometry()
        radius = g["outer"] / 2.0
        head_radius = g["counterbore"] / 2.0
        bounds_w = self.wall_bounds()
        lx0, lx1, ly0, ly1 = merged_boss.bore_center_limits(
            head_radius, bounds_w, self.config.merged_boss
        )
        bounds = (lx0, ly0, lx1, ly1)
        conflicts = self._column_conflict_test(radius, head_radius)

        rear_line = ly0 + 0.0
        spots: list[tuple[float, float]] = []

        half_iw = (bounds_w.x1 - bounds_w.x0) / 2
        targets = [
            (sx * (half_iw - head_radius), sy * (bounds_w.y1 - head_radius))
            for sx, sy in ((1, 1), (-1, 1), (-1, -1), (1, -1))
        ]
        targets += [(sx * half_iw / 2.0, rear_line) for sx in (1, -1)]
        targets.append((0.0, rear_line))
        for target in targets:
            spot = nearest_free_spot(target, conflicts, bounds)
            if spot is not None:
                spots.append(spot)

        wall = self.config.wall_thickness
        spots = drop_close(spots, 2 * g["outer"] + wall)
        self._memo[key] = spots
        return spots

    def columns(self) -> list[Column]:
        """The Deck columns (Tray post + Deck boss), CAD-free."""
        key = "columns"
        if key in self._memo:
            return self._memo[key]
        wall = self.config.wall_thickness
        g = self.column_geometry()
        zp = self.parting_height()
        rule = self.config.merged_boss
        bounds = self.wall_bounds()
        out = []
        for cx, cy in self._column_positions():
            spec = BossSpec(
                hole_diameter=g["counterbore"], outer_diameter=g["outer"],
                height=zp, wall_thickness=wall,
            )
            walls = merged_boss.merge_walls(cx, cy, g["outer"] / 2.0, bounds, wall, rule)
            out.append(Column(
                x=cx, y=cy, spec=spec, bore_diameter=g["bore"],
                counterbore_diameter=g["counterbore"],
                counterbore_depth=g["counterbore_depth"],
                insert_diameter=g["insert"], insert_depth=g["insert_depth"],
                height=zp, deck_boss_height=self.deck_level_at(cy) - zp, walls=walls,
            ))
        self._memo[key] = out
        return out

    # -- Footprints of structural features ---------------------------------------

    def cradle_spec(self, placement):
        """The cradle saddle for a placed battery pack.

        Side-by-side cells' saddles are at least half the cell pitch wide, so
        neighbours meet flush and fuse into one block.
        """
        from geometry import cradle

        battery = placement.component
        xs = sorted({round(cx, 6) for cx, _ in battery._cell_centers()})
        pitch = min((b - a for a, b in zip(xs, xs[1:])), default=0.0)
        return cradle.CradleSpec(
            diameter=battery.cell_diameter, rest_height=placement.z,
            height=battery.cradle_height, width=self.config.wall_thickness * 3,
            min_half_width=pitch / 2.0,
        )

    def cradle_rects(self) -> list[tuple[float, float, float, float]]:
        """XY footprint of every battery cradle saddle (mm)."""
        from components.battery import Battery

        rects = []
        for p in self.assembly.placements:
            if not isinstance(p.component, Battery):
                continue
            battery = p.component
            spec = self.cradle_spec(p)
            end_offset = max(0.0, battery.cell_length / 2.0 - spec.width / 2.0)
            half_x, half_y = spec.block_half_width, spec.width / 2.0
            for cx, cy in battery._cell_centers():
                for cy_end in (cy - end_offset, cy + end_offset):
                    wx, wy, _ = p.world_offset(cx, cy_end, 0.0)
                    rad = math.radians(p.rotation)
                    ex = abs(half_x * math.cos(rad)) + abs(half_y * math.sin(rad))
                    ey = abs(half_x * math.sin(rad)) + abs(half_y * math.cos(rad))
                    rects.append((wx - ex, wx + ex, wy - ey, wy + ey))
        return rects

    def cutout_rects(self) -> list[tuple[float, float, float, float]]:
        """XY footprint of every connector cutout through a wall (mm).

        Includes the lead-in chamfer and one wall's depth to either side of the
        wall's inner face, so a feature there would crowd the port.
        """
        size = self.size()
        wall = self.config.wall_thickness
        chamfer = self.config.corners.cutout_chamfer
        rects = []
        for c in self.cutouts():
            dx, dy = c["direction"][0], c["direction"][1]
            half = c["width"] / 2 + chamfer
            if abs(dy) >= abs(dx):
                face = (size.depth / 2 - wall) * (1 if dy > 0 else -1)
                y0, y1 = sorted((face, face + wall * (1 if dy > 0 else -1)))
                rects.append((c["x"] - half, c["x"] + half, y0 - wall, y1 + wall))
            else:
                face = (size.width / 2 - wall) * (1 if dx > 0 else -1)
                x0, x1 = sorted((face, face + wall * (1 if dx > 0 else -1)))
                rects.append((x0 - wall, x1 + wall, c["y"] - half, c["y"] + half))
        return rects

    def vent_rects(self, positions: tuple[float, ...], slot_width: float) -> list[tuple[float, float, float, float]]:
        """XY footprint of each vent slot through the rear wall (mm)."""
        size = self.size()
        wall = self.config.wall_thickness
        y0 = -size.depth / 2
        return [(p - slot_width / 2, p + slot_width / 2, y0, y0 + wall) for p in positions]

    def column_rect(self, col: Column) -> tuple[float, float, float, float]:
        """XY footprint of a column including its hull to the walls it merges into."""
        r = col.base_diameter / 2.0
        b = self.wall_bounds()
        x0, x1, y0, y1 = col.x - r, col.x + r, col.y - r, col.y + r
        face = {"left": b.x0, "right": b.x1, "rear": b.y0, "front": b.y1}
        for w in col.walls:
            if w == "left":
                x0 = min(x0, face[w])
            elif w == "right":
                x1 = max(x1, face[w])
            elif w == "rear":
                y0 = min(y0, face[w])
            else:
                y1 = max(y1, face[w])
        return (x0, x1, y0, y1)

    # -- Seam lugs --------------------------------------------------------------

    def _lug_spec(self):
        return seam_joint.joint_spec(self.config.seam_pin)

    def tray_lug_sites(self) -> dict[str, list[tuple[float, float, bool]]]:
        """Seam-joint sites per Tray Seam (``"tray:<index>"``), two each.

        Sites clear the components inside, bosses, standoffs, columns,
        cradles and connector cutouts.
        """
        key = "tray_lug_sites"
        if key in self._memo:
            return self._memo[key]
        split = self._split("tray")
        sites: dict[str, list] = {}
        if split is not None:
            spec = self._lug_spec()
            wall = self.config.wall_thickness
            size = self.size()
            top = spec.size + self.config.clearance.shell
            keepouts = list(self.assembly.keepout_rects(0.0, top, self._base_placements()))
            keepouts += [
                (bx - spec_b.base_diameter / 2, bx + spec_b.base_diameter / 2,
                 by - spec_b.base_diameter / 2, by + spec_b.base_diameter / 2)
                for bx, by, spec_b in self.assembly.bosses(self._base_placements())
            ]
            keepouts += [self.column_rect(c) for c in self.columns()]
            keepouts += self.cradle_rects() + self.cutout_rects()
            for i, seam in enumerate(split.seams()):
                sites[f"tray:{i}"] = seam_joint.plan_joints(
                    seam, size.depth, wall, spec, floor_top=0.0,
                    clearance=self.config.clearance.shell, keepouts=keepouts,
                )
        self._memo[key] = sites
        return sites

    def lug_rects(self) -> dict[str, list[tuple[float, float, float, float]]]:
        """XY footprint of each Tray Seam's lugs, keyed by Seam id."""
        spec = self._lug_spec()
        wall = self.config.wall_thickness
        return {
            sid: [seam_joint.lug_footprint(spec, sx, sy, wall, backed) for sx, sy, backed in sites]
            for sid, sites in self.tray_lug_sites().items()
        }

    # -- Ribs and vents ---------------------------------------------------------

    def rib_avoid(self) -> tuple[tuple[float, float], ...]:
        """X ranges the floor ribs must keep out of: Seam bands and lugs.

        Ribs run the full interior depth, so each avoided footprint blocks its
        whole X range.
        """
        wall = self.config.wall_thickness
        ranges = [(r[0], r[1]) for r in self._band_rects()]
        for rects in self.lug_rects().values():
            ranges += [(r[0] - wall, r[1] + wall) for r in rects]
        return tuple(ranges)

    def vent_keepout_ranges(self) -> tuple[tuple[float, float], ...]:
        """X ranges the rear-wall vent slots keep clear of over their whole
        height (mm): Seam bands, and what is fused to the rear wall's inside —
        columns merged into it, the hinge pads and Cable guard, and the Deck Seam lugs."""
        chamfer = self.config.corners.cutout_chamfer
        ranges = [(r[0], r[1]) for r in self._band_rects()]
        for x0, x1, _, _ in self.hinge_rects().values():
            ranges.append((x0 - chamfer, x1 + chamfer))
        for rects in self.deck_lug_rects().values():
            ranges += [(x0 - chamfer, x1 + chamfer) for x0, x1, _, _ in rects]
        for col in self.columns():
            if "rear" in col.walls:
                r = col.base_diameter / 2.0
                ranges.append((col.x - r - chamfer, col.x + r + chamfer))
        return tuple(ranges)

    def vent_raised_ranges(self) -> tuple[tuple[float, float, float], ...]:
        """``(x0, x1, z)`` per rear-wall connector cutout: a vent slot over it
        (or within a wall of its side) starts at ``z``, a wall above the
        cutout's chamfered top, so the two never touch."""
        chamfer = self.config.corners.cutout_chamfer
        wall = self.config.wall_thickness
        out = []
        for c in self.cutouts():
            if c["direction"][1] < 0 and abs(c["direction"][1]) >= abs(c["direction"][0]):
                half = c["width"] / 2 + chamfer + wall
                out.append((c["x"] - half, c["x"] + half, c["z"] + c["height"] / 2 + chamfer + wall))
        return tuple(out)

    # -- Feature list for the Seam clearance check -------------------------------

    def structural_features(self, ribs=(), rib_thickness: float = 0.0, vents=(), vent_width: float = 0.0) -> list[Feature]:
        """Every structural feature the Seams must keep clear of, CAD-free."""
        keyboard = self.keyboard
        features: list[Feature] = []
        b = self.wall_bounds()
        for x in ribs:
            features.append(Feature("rib", f"x={x:.1f}", x - rib_thickness / 2, x + rib_thickness / 2, b.y0, b.y1, part="tray"))
        for bx, by, spec, owner in self.component_boss_specs():
            kind = "standoff" if owner is keyboard else "boss"
            r = spec.base_diameter / 2.0
            features.append(Feature(kind, f"({bx:.1f}, {by:.1f})", bx - r, bx + r, by - r, by + r, part="tray"))
        for col in self.columns():
            x0, x1, y0, y1 = self.column_rect(col)
            features.append(Feature("column", f"({col.x:.1f}, {col.y:.1f})", x0, x1, y0, y1))
        for i, (x0, x1, y0, y1) in enumerate(self.cradle_rects()):
            features.append(Feature("cradle", f"#{i}", x0, x1, y0, y1, part="tray"))
        for name, (x0, x1, y0, y1) in self.hinge_rects().items():
            features.append(Feature("hinge", name, x0, x1, y0, y1, part="deck"))
        for i, (x0, x1, y0, y1) in enumerate(self.vent_rects(vents, vent_width)):
            features.append(Feature("vent", f"#{i}", x0, x1, y0, y1))
        zp = self.parting_height()
        for i, ((x0, x1, y0, y1), c) in enumerate(zip(self.cutout_rects(), self.cutouts())):
            above = c["z"] + c["height"] / 2.0 + self.config.corners.cutout_chamfer > zp
            features.append(Feature("cutout", f"#{i}", x0, x1, y0, y1, part=None if above else "tray"))
        for sid, rects in self.lug_rects().items():
            for x0, x1, y0, y1 in rects:
                features.append(Feature("lug", f"({(x0 + x1) / 2:.1f}, {(y0 + y1) / 2:.1f})", x0, x1, y0, y1, joins=sid, part="tray"))
        for sid, rects in self.deck_lug_rects().items():
            for x0, x1, y0, y1 in rects:
                features.append(Feature("lug", f"({(x0 + x1) / 2:.1f}, {(y0 + y1) / 2:.1f})", x0, x1, y0, y1, joins=sid, part="deck"))
        return features

    def component_boss_specs(self) -> list[tuple[float, float, BossSpec, Any]]:
        """Component mounting bosses ``(x, y, spec, owner)`` (CAD-free).

        The owner is the component the boss holds up: a mounting boss
        legitimately touches the part it supports.
        """
        from geometry.boss import boss_spec

        wall = self.config.wall_thickness
        default_screw = self.config.screws.standoff
        out = []
        for placement in self._base_placements():
            component = placement.component
            screw_size = component.mounting_screw() or default_screw
            for hole in component.mounting_holes():
                spec = boss_spec(
                    wall_thickness=wall, screw_size=screw_size, insert_type=screw_size,
                    hole_diameter=hole.diameter, height=hole.height,
                )
                bx, by, _ = placement.world_offset(hole.x, hole.y, 0.0)
                out.append((bx, by, spec, component))
        return out

    # -- Torque hinges (ADR 0007) ----------------------------------------------

    def hinge_rects(self) -> dict[str, tuple[float, float, float, float]]:
        """XY footprint ``(x0, x1, y0, y1)`` of what the hinge adds to the Deck:
        each Base leaf's pad (``"left"``/``"right"``) and the Cable guard's
        discs and arms (``"cable guard"``)."""
        if self.hinge is None:
            return {}
        rear_y = -self.size().depth / 2.0
        out = {side: self.hinge.pad_rect("base", rear_y, side) for side in ("left", "right")}
        guard = self.hinge.guard
        if guard is not None:
            x0, x1, y0, y1 = guard.arm_rect(self.hinge.setback)
            axis_y = rear_y - self.hinge.setback
            out["cable guard"] = (x0, x1, axis_y + y0, axis_y + y1)
        return out

    # -- Deck Seam lugs ------------------------------------------------------------

    def deck_lug_sites(self) -> dict[str, list[tuple[float, float, bool]]]:
        """Seam-lug sites per Deck Seam (``"deck:<index>"``), two each (front and
        rear skirt), standing on the Parting plane; empty if they don't fit."""
        key = "deck_lug_sites"
        if key in self._memo:
            return self._memo[key]
        split = self._split("deck")
        sites: dict[str, list] = {}
        if split is not None:
            spec = self._lug_spec()
            wall = self.config.wall_thickness
            zp = self.parting_height()
            gap = self.config.clearance.shell
            keepouts = list(self.assembly.keepout_rects(zp, zp + spec.size + gap, self._base_placements()))
            keepouts += [self.column_rect(c) for c in self.columns()]
            keepouts += [rc for rc, c in zip(self.cutout_rects(), self.cutouts())
                         if c["z"] + c["height"] / 2.0 + self.config.corners.cutout_chamfer > zp]
            keepouts += list(self.hinge_rects().values())
            for i, seam in enumerate(split.seams()):
                try:
                    sites[f"deck:{i}"] = seam_joint.plan_joints(
                        seam, self.size().depth, wall, spec, floor_top=zp,
                        clearance=gap, keepouts=keepouts,
                    )
                except ValueError:
                    sites[f"deck:{i}"] = []
        self._memo[key] = sites
        return sites

    def deck_lug_rects(self) -> dict[str, list[tuple[float, float, float, float]]]:
        """XY footprint of each Deck Seam's lug, keyed by Seam id."""
        spec = self._lug_spec()
        wall = self.config.wall_thickness
        return {
            sid: [seam_joint.lug_footprint(spec, sx, sy, wall, backed) for sx, sy, backed in sites]
            for sid, sites in self.deck_lug_sites().items()
        }
