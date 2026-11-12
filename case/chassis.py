"""Slider chassis: a Tray and a Deck joined at the Parting plane (ADR-0012).

The chassis splits at the Parting plane (ADR 0003). The ``band`` is split
evenly around the plane: the Tray is drafted from its base up to ``band_z0``
and prismatic from there to the plane; the Deck is prismatic all the way to
the closed face. Only the lower half of the silhouette tapers, so the base
width and the closed face follow from that.

* The **Tray** is the lower bowl: tapered outer walls up to the joint band,
  then a prismatic band to the Parting plane, a wall-thick floor, and a
  frustum column at each of the ten fastener stations. An M3 screw is driven
  from below through a countersink in the floor, up the column, and across the
  plane into a heat-set insert in the Deck.
* The **Deck** is purely prismatic from the Parting plane to the closed face:
  the keyboard Well (a wall-thick ring around the keycap Cutout, descending to
  the plate's top face, with the plate's eight M2 insert bosses merged into its
  front/rear lips), the two bearing-clamp seats and their pockets, and one
  insert boss per band station standing out of the band's cavity.

Both halves carry a shallow scallop at every station, straddling the seam.

The bearing clamps are separate printed parts. Each has a foot that drops
through a pocket in the Deck; the Deck carries a small raised/merged seat with
a pocket floor, so the clamp is located and bolted from inside the chassis.
"""

from __future__ import annotations

from typing import Any

from case.slider_frame import SliderFrame


class Chassis:
    """The lower half of the slider: a Tray, a Deck with the Well and seats."""

    def __init__(self, config: Any, frame: SliderFrame) -> None:
        self.config = config
        self.frame = frame

    # -- parts -----------------------------------------------------------
    def build(self):
        """Return the assembled chassis as a two-part compound (Tray + Deck)."""
        from utilities import cad_helpers as ch

        ch.require_cad()
        return ch.make_compound([self.build_tray(), self.build_deck()])

    def build_tray(self):
        """The lower bowl: drafted walls, floor, station columns, screws."""
        from utilities import cad_helpers as ch
        from utilities.fasteners import screw as screw_spec

        ch.require_cad()
        f = self.frame
        joint = f.chassis_joint
        wall = f.wall
        chamfer = self.config.corners.chamfer
        z_band = f.chassis_band_z0
        z1 = f.parting_z
        base_w = f.chassis_base_width
        band_w = f.chassis_band_width

        # Tapered skin from the base up to the band, then prismatic to the
        # Parting plane where it meets the Deck at the same width.
        outer = ch.tapered_box(
            base_w, f.depth, band_w, f.depth, 0.0, z_band, chamfer=chamfer
        )
        outer = ch.union(
            outer,
            ch.tapered_box(
                band_w, f.depth, band_w, f.depth, z_band, z1, chamfer=chamfer
            ),
        )
        # The cavity is the outer skin offset by one wall. It starts one wall
        # above the table (the floor), follows the draft up to the band and is
        # prismatic with it to the plane.
        bottom_inset = ch.draft_inset(f.draft_angle, wall)
        cavity = ch.tapered_box(
            base_w + 2.0 * bottom_inset - 2.0 * wall,
            f.depth - 2.0 * wall,
            band_w - 2.0 * wall,
            f.depth - 2.0 * wall,
            wall,
            z_band,
        )
        cavity = ch.union(
            cavity,
            ch.tapered_box(
                band_w - 2.0 * wall,
                f.depth - 2.0 * wall,
                band_w - 2.0 * wall,
                f.depth - 2.0 * wall,
                z_band,
                z1,
            ),
        )
        body = ch.cut(outer, cavity)

        # A column at every station, from the floor up to the plane. The
        # frustum tapers from what the floor skin allows to the insert boss
        # diameter at the plane.
        body = ch.union(body, *[self._column(station) for station in joint.stations])

        # The screw: clearance through the column, countersunk from below.
        spec = screw_spec(joint.screw.size)
        csk = joint.countersink
        holes = []
        for station in joint.stations:
            through = ch.translate(
                ch.cylinder_centered(spec.clearance, z1 + 2.0),
                station.x,
                station.y,
                z1 / 2.0,
            )
            cone = ch.translate(
                ch.frustum_centered(csk.diameter, spec.clearance, csk.depth),
                station.x,
                station.y,
                csk.depth / 2.0,
            )
            holes.extend((through, cone))
        body = ch.cut(body, *holes)

        # Scallops: the lower half of every station's relief, cut into the
        # prismatic band.
        scallops = [
            self._scallop(
                station,
                z0=z_band,
                distance=station.surface,
                shift=0.0,
            )
            for station in joint.stations
        ]
        return ch.clean(ch.cut(body, *scallops))

    def build_deck(self):
        """The upper shell: a prismatic body with the Well ring and seats."""
        from utilities import cad_helpers as ch

        ch.require_cad()
        f = self.frame
        joint = f.chassis_joint
        wall = f.wall
        chamfer = self.config.corners.chamfer
        z0, top = f.parting_z, f.chassis_top
        band_w = f.chassis_band_width
        cavity_top = top - wall

        # The plate's mounting pattern (ADR-0014) is the single source for the
        # Well: its rectangular frame is the plate, its Cutout is the opening
        # the ring surrounds, and its stations are the insert bosses.
        mounts = self._well_mounts()
        cut = mounts.cutout_rect
        plate = mounts.frame.rect
        plate_top = mounts.plate_top
        # The Well ring and the notches are cut as world-axis-aligned boxes, so
        # the plate frame may only be the layout's 0/180 deg turn.
        if mounts.frame.rotation not in (0.0, 180.0):
            raise ValueError(
                "the Deck builds the Well and its notches as world-axis-aligned "
                f"boxes; the plate frame is {mounts.frame.rotation:g} deg"
            )
        ring_height = top - plate_top
        if ring_height <= 0.0:
            raise ValueError(
                "the Well has no depth: the plate's top face is at or above the "
                f"Deck's top ({plate_top:.2f} vs {top:.2f} mm)"
            )

        # The whole Deck is prismatic at the closed-face width: no flare above
        # the band, so the upper silhouette stays straight to the face.
        outer = ch.tapered_box(
            band_w, f.depth, band_w, f.depth, z0, top, chamfer=chamfer
        )
        # Open cavity: straight through the whole Deck, with a wall-thick top
        # plate.
        cavity = ch.tapered_box(
            band_w - 2.0 * wall,
            f.depth - 2.0 * wall,
            band_w - 2.0 * wall,
            f.depth - 2.0 * wall,
            z0,
            cavity_top,
        )
        body = ch.cut(outer, cavity)

        # The keyboard Well: a ring of Deck walls around the Cutout, from the
        # Deck's top face down to the plate. Its lower faces are the plate's
        # continuous bearing -- no ledge and no floor. It stands inside the
        # cavity, so it is unioned back onto the shell.
        ring = ch.box_centered(plate.width, plate.depth, ring_height)
        ring = ch.translate(ring, plate.cx, plate.cy, plate_top + ring_height / 2.0)
        opening = ch.box_centered(cut.width, cut.depth, ring_height + 2.0)
        opening = ch.translate(opening, cut.cx, cut.cy, plate_top + ring_height / 2.0)
        ring = ch.cut(ring, opening)
        # Where a chassis band column reaches into the plate's border, the
        # plate is notched; the ring's outer reach is interrupted there too so
        # the column does not share volume with the Well wall. Only the outer
        # sliver goes: the Well stays sealed along its inner face.
        notches = []
        for notch in mounts.notches:
            centre = mounts.frame.to_plan(notch.rect.cx, notch.rect.cy)
            notches.append(
                ch.translate(
                    ch.box_centered(
                        notch.rect.width, notch.rect.depth, ring_height + 2.0
                    ),
                    centre[0],
                    centre[1],
                    plate_top + ring_height / 2.0,
                )
            )
        if notches:
            ring = ch.cut(ring, *notches)
        body = ch.union(body, ring)

        # The Cutout is open through the top slab: the keycaps pass through it
        # and the ring surrounds it. It is sized by the keycaps plus wobble,
        # never by `clearance.shell`.
        well = ch.box_centered(cut.width, cut.depth, 3.0 * wall)
        well = ch.translate(well, cut.cx, cut.cy, top)
        body = ch.cut(body, well)

        # One M2 insert boss per plate station, merged to the ring's outer face
        # inside the front/rear lip. It stands on the plate's top face (the
        # plate's ear is below it), so no boss can enter the Cutout.
        well_bosses = [
            ch.translate(
                ch.cylinder_centered(m.boss_diameter, m.boss_z1 - m.boss_z0),
                m.x,
                m.y,
                (m.boss_z0 + m.boss_z1) / 2.0,
            )
            for m in mounts.mounts
        ]
        body = ch.union(body, *well_bosses)

        # One insert boss per chassis band station, standing out of the band's
        # cavity. The boss is taller than the Deck's half-band: the M3 heat-set
        # insert is 4 mm deep and still needs a boss margin of material above it.
        boss_height = joint.boss_height
        band_bosses = [
            ch.translate(
                ch.cylinder_centered(station.boss, boss_height),
                station.x,
                station.y,
                z0 + boss_height / 2.0,
            )
            for station in joint.stations
        ]
        body = ch.union(body, *band_bosses)

        body = ch.union(body, self._seat(-1), self._seat(1))
        body = ch.cut(body, self._seat_pocket(-1), self._seat_pocket(1))
        body = self._pocket_mouth_chamfer(body)
        body = ch.cut(body, self._seat_hole(-1), self._seat_hole(1))

        # Heat-set insert holes, drilled up from the band's underside.
        hole_depth = joint.insert_depth + 0.2
        holes = [
            ch.translate(
                ch.cylinder_centered(joint.insert_hole, hole_depth + 1.0),
                station.x,
                station.y,
                z0 + hole_depth / 2.0 - 0.5,
            )
            for station in joint.stations
        ]
        body = ch.cut(body, *holes)

        # The plate's own M2 insert holes, drilled up from the plate's top
        # face into the well bosses (ADR-0014).
        plate_holes = [
            ch.translate(
                ch.cylinder_centered(
                    m.insert_hole_diameter, m.insert_depth + 1.0
                ),
                m.x,
                m.y,
                m.boss_z0 + m.insert_depth / 2.0 - 0.5,
            )
            for m in mounts.mounts
        ]
        body = ch.cut(body, *plate_holes)

        # Scallops: the upper half of every station's relief. Inside the band
        # the wall is prismatic, so no shear. A station whose relief would
        # reach the Well ring or one of its bosses is left uncut rather than
        # breaking the Well.
        avoid = [plate] + [m.plan_rect for m in mounts.mounts]
        scallops = [
            cutter
            for cutter in (
                self._scallop(
                    station,
                    z0=z0,
                    distance=station.surface,
                    shift=0.0,
                    avoid=[(r.x0, r.y0, r.x1, r.y1) for r in avoid],
                )
                for station in joint.stations
            )
            if cutter is not None
        ]
        return ch.clean(ch.cut(body, *scallops))

    def _well_mounts(self):
        """The plate's mounting pattern, from the frame's derived dimensions.

        ``well_mounts`` is duck-typed on the slide budget; the frame carries
        the same derived numbers, so the adapter only renames them. This keeps
        the Deck and the plate on one source without the chassis knowing the
        whole budget.
        """
        from types import SimpleNamespace

        from geometry.well_mounts import well_mounts

        f = self.frame
        budget = SimpleNamespace(
            well=f.well,
            chassis_joint=f.chassis_joint,
            chassis_height=f.depth,
            chassis_top=f.chassis_top,
            clamp_width=f.clamp_width,
            rod_x=f.rod_x,
            clamp_center_y=f.clamp_center_y,
        )
        mounts = well_mounts(self.config, budget, frame=f.plate_frame)
        if not mounts.ok:
            raise ValueError(
                "the plate's Well mounts are invalid: "
                + "; ".join(mounts.failures)
            )
        return mounts


    # -- joint features --------------------------------------------------
    def _column(self, station: Any):
        """One Tray column: frustum from the floor skin to the plane boss."""
        from utilities import cad_helpers as ch

        f = self.frame
        height = f.parting_z
        column = ch.frustum_centered(station.base_boss, station.boss, height)
        return ch.translate(column, station.x, station.y, height / 2.0)

    def _scallop(
        self,
        station: Any,
        *,
        z0: float,
        distance: float,
        shift: float,
        avoid=(),
    ):
        """A shallow relief at one station, its floor following the wall.

        ``distance`` is the station-to-outer-face distance at ``z0`` and
        ``shift`` how far that face recedes outward over the scallop height
        (zero where the wall is prismatic). The cutter is a sheared prism: the
        top outline is the bottom one shifted outward, so the cut stays a
        constant ``scallop_depth`` deep.

        ``avoid`` lists plan rectangles (``x0, y0, x1, y1``) the relief may not
        reach -- the Well ring and its insert bosses. A relief that would cut
        one is skipped (``None``): the relief is cosmetic, the Well is not.
        """
        from utilities import cad_helpers as ch

        f = self.frame
        joint = f.chassis_joint
        width = joint.scallop_width
        depth = joint.scallop_depth
        height = joint.scallop_height
        nx, ny = station.normal
        # Tangent along the wall (the normal rotated +90 degrees).
        tx, ty = -ny, nx

        inner = distance - depth
        outer = distance + shift + 2.0 * f.wall + 2.0

        def point(r: float, s: float) -> tuple[float, float]:
            return (
                station.x + nx * r + tx * s,
                station.y + ny * r + ty * s,
            )

        half = width / 2.0
        bottom = [
            point(inner, -half),
            point(outer, -half),
            point(outer, half),
            point(inner, half),
        ]
        top = [
            point(inner + shift, -half),
            point(outer + shift, -half),
            point(outer + shift, half),
            point(inner + shift, half),
        ]
        if avoid:
            xs = [p[0] for p in bottom + top]
            ys = [p[1] for p in bottom + top]
            x0, x1 = min(xs), max(xs)
            y0, y1 = min(ys), max(ys)
            for ax0, ay0, ax1, ay1 in avoid:
                if x0 < ax1 and ax0 < x1 and y0 < ay1 and ay0 < y1:
                    return None
        return ch.loft_between(bottom, top, height, z=z0)

    # -- Deck features ---------------------------------------------------
    def _seat(self, side: int):
        """A bearing-clamp seat block merged into the Deck and side wall."""
        from utilities import cad_helpers as ch

        f = self.frame
        block = ch.box_centered(f.seat_width, f.seat_length, f.seat_height)
        block = ch.translate(
            block,
            side * f.rod_x,
            f.clamp_center_y,
            f.chassis_top - f.seat_height / 2.0,
        )
        return block

    def _seat_pocket(self, side: int):
        """The pocket that receives the Bearing clamp foot."""
        from utilities import cad_helpers as ch

        f = self.frame
        pocket = ch.box_centered(
            f.pocket_width, f.pocket_length, f.pocket_depth + 1.0
        )
        corner = self.config.slide.bearing_clamp.corner_chamfer
        if corner > 0.0:
            # Match the clamp foot's vertical corner relief (the foot is
            # longer than the pocket's straight sides are wide, so a plain
            # box would clash at the corners).
            pocket = ch.chamfer_vertical_edges(pocket, corner)
        pocket = ch.translate(
            pocket,
            side * f.rod_x,
            f.clamp_center_y,
            f.chassis_top - f.pocket_depth / 2.0 + 0.5,
        )
        return pocket

    def _pocket_mouth_chamfer(self, body):
        """Break the top rim of each bearing-clamp pocket.

        The pocket is cut into the Deck, so its mouth is the only set of
        convex edges on the Deck top plane inside the pocket footprint; the
        seat's outer top edges are further out and stay sharp.
        """
        from utilities import cad_helpers as ch

        f = self.frame
        amount = self.config.slide.bearing_clamp.top_chamfer
        if amount <= 0.0:
            return body
        rim = [
            edge
            for edge in ch.convex_edges(body)
            if abs(edge.midpoint[2] - f.chassis_top) < 1e-6
            and abs(edge.midpoint[1] - f.clamp_center_y)
            <= f.pocket_length / 2.0 + 1e-6
            and min(
                abs(edge.midpoint[0] - side * f.rod_x) for side in (-1, 1)
            )
            <= f.pocket_width / 2.0 + 1e-6
        ]
        return ch.chamfer_edges(body, rim, amount)

    def _seat_hole(self, side: int):
        """Two through-holes in the seat floor for the Bearing clamp screws."""
        from utilities import cad_helpers as ch
        from utilities.fasteners import screw as screw_spec

        f = self.frame
        spec = screw_spec(self.config.slide.bearing_clamp.screw)
        floor = self.config.slide.bearing_clamp.seat_floor
        span = self.config.slide.bearing_clamp.screw_span_y
        holes = []
        for screw_side in (-1, 1):
            hole = ch.cylinder_centered(spec.clearance, floor + 2.0)
            hole = ch.translate(
                hole,
                side * f.rod_x,
                f.clamp_center_y + screw_side * span / 2.0,
                f.chassis_top - f.pocket_depth - floor / 2.0,
            )
            holes.append(hole)
        return ch.make_compound(holes)

    # -- printing --------------------------------------------------------
    def sections(self) -> tuple[Any, Any]:
        """Split the assembled chassis into its left and right Sections."""
        from utilities import cad_helpers as ch

        return ch.split_x(self.build())

    def tray_sections(self) -> tuple[Any, Any]:
        from utilities import cad_helpers as ch

        return ch.split_x(self.build_tray())

    def deck_sections(self) -> tuple[Any, Any]:
        from utilities import cad_helpers as ch

        return ch.split_x(self.build_deck())


__all__ = ["Chassis"]
