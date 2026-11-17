"""Slider chassis: a Tray and a Deck joined at the Parting plane (ADR-0012).

The chassis splits at the Parting plane (ADR 0003). The ``band`` is split
evenly around the plane: the Tray is prismatic from its base to the plane
(ADR-0019 removed its X draft so the accessory rail can bolt to a flat face)
and the Deck is prismatic all the way to the closed face, so the base width and
the closed face are one number. The Tray's vertical end walls leave the table
with a base taper that runs up to the band's bottom -- a draft, so the cavity
follows the outer face -- and dies into a pad at every station
(:mod:`geometry.base_taper`).

* The **Tray** is the lower bowl: vertical X walls to the Parting plane, a
  wall-thick floor, and a straight column at each of the twelve fastener
  stations. An M3 screw is driven from below through a countersink in the
  floor, up the column, and across the plane into a heat-set insert in the
  Deck.
* The **Deck** is purely prismatic from the Parting plane to the closed face:
  the keyboard Well (a wall-thick ring around the keycap Cutout, descending to
  the plate's top face, with the plate's eight M2 insert bosses merged into its
  front/rear lips), the two bearing-clamp seats and their pockets, and one
  insert boss per band station standing out of the band's cavity.

Both shells' outer vertical corners are chamfered, and their cavities are
chopped to match (``cad_helpers.inner_corner_chamfer``): a square cavity corner
would sit flush with the outer chamfer at the default 4 mm / 2 mm wall and print
as a knife edge.

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
        """The lower bowl: vertical walls, floor, station columns, screws."""
        from geometry import head_recess
        from geometry.base_taper import build_cutter as taper_cutter
        from geometry.base_taper import build_fill as taper_fill
        from utilities import cad_helpers as ch
        from utilities.fasteners import screw as screw_spec

        ch.require_cad()
        f = self.frame
        joint = f.chassis_joint
        wall = f.wall
        chamfer = self.config.corners.chamfer
        z1 = f.parting_z
        band_w = f.chassis_band_width

        # ADR-0019: the Tray is prismatic from its base to the Parting plane.
        # Its X walls are vertical because the accessory rail bolts to a flat,
        # square face; the silhouette does not taper. The end walls still read
        # as a taper, cut below as a base draft that steps around the station
        # pads.
        outer = ch.translate(
            ch.chamfer_vertical_edges(
                ch.box_centered(band_w, f.depth, z1), chamfer
            ),
            0.0,
            0.0,
            z1 / 2.0,
        )
        # The cavity is the outer skin offset by one wall. It starts one wall
        # above the table (the floor) and runs prismatic to the plane. Its
        # corners carry the inner chamfer so the corner wall stays one `wall`
        # thick behind the outer chop.
        cavity_chamfer = ch.inner_corner_chamfer(chamfer, wall)
        cavity = ch.translate(
            ch.chamfer_vertical_edges(
                ch.box_centered(band_w - 2.0 * wall, f.depth - 2.0 * wall, z1 - wall),
                cavity_chamfer,
            ),
            0.0,
            0.0,
            (z1 + wall) / 2.0,
        )
        body = ch.cut(outer, cavity)

        # The base taper on the vertical front/rear walls (ADR-0019): a wedge
        # from the table up to the band's bottom, suppressed inside a pad around
        # every station. It is a draft, not a chamfer on the floor's edge -- the
        # same wedge goes back inside the cavity, so the wall keeps its
        # thickness instead of thinning toward the table.
        body = ch.cut(body, taper_cutter(f.base_taper))
        body = ch.union(body, taper_fill(f.base_taper))

        # The accessory rail's stations (ADR-0020): a pad at each M4 station on
        # the X walls, braced into the floor by two 45 degree gussets. The pad
        # carries the square pocket the printed washer puck drops into; the
        # screw comes through the rail, the wall and the pad into the nut the
        # puck captures.
        rail = self._rail_mounts()
        body = ch.union(
            body,
            *[self._rail_pad(station) for station in rail.stations],
            *[
                self._rail_gusset(station, direction)
                for station in rail.stations
                for direction in (-1, 1)
            ],
        )

        # A column at every station, from the floor up to the plane. The
        # frustum tapers from what the floor skin allows to the insert boss
        # diameter at the plane.
        body = ch.union(body, *[self._column(station) for station in joint.stations])

        # The screw: a clearance hole through the column, its ordinary button
        # head seated in a keyhole recess cut into the floor, ramp pointing
        # away from the nearest wall (ADR-0018).
        spec = screw_spec(joint.screw.size)
        recess = joint.recess
        holes = []
        for station in joint.stations:
            through = ch.translate(
                ch.cylinder_centered(spec.clearance, z1 + 2.0),
                station.x,
                station.y,
                z1 / 2.0,
            )
            keyhole = head_recess.build_cutter(
                recess,
                normal=station.normal,
                mouth=station.mouth_chamfer,
                x=station.x,
                y=station.y,
                z0=0.0,
            )
            holes.extend((through, keyhole))
        body = ch.cut(body, *holes)

        # The rail's own holes: the pocket the washer puck sits in and the M4
        # clearance bore behind it, through the pad and the wall.
        body = ch.cut(
            body,
            *[
                shape
                for station in rail.stations
                for shape in (
                    self._rail_pocket(station),
                    self._rail_hole(station),
                )
            ],
        )

        # ADR-0006: the Seam's glued-filament pins, grown into the half before
        # the split so each Section prints its own share of every fin.
        body = self._add_seam_pins(body, "chassis_tray", f.depth)
        return ch.clean(body)

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
        # plate. Its corners carry the inner chamfer so the corner wall stays
        # one `wall` thick behind the outer chop.
        cavity = ch.tapered_box(
            band_w - 2.0 * wall,
            f.depth - 2.0 * wall,
            band_w - 2.0 * wall,
            f.depth - 2.0 * wall,
            z0,
            cavity_top,
            chamfer=ch.inner_corner_chamfer(chamfer, wall),
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
        # plate's ear is below it), so no boss can enter the Cutout, and runs
        # up to the Deck's inner ceiling: the Deck prints face down, so a boss
        # that stopped at the insert would be an unsupported overhang.
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

        # One insert boss per chassis band station. The M3 insert is 4 mm deep
        # and needs a boss margin above it, but the column runs all the way to
        # the inner ceiling for the same print reason as the Well bosses: on
        # the face-down print a short boss would hang off the band's wall.
        boss_height = cavity_top - z0
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

        body = self._add_seam_pins(body, "chassis_deck", f.depth)
        return ch.clean(body)

    def _add_seam_pins(self, body, name: str, depth: float):
        """Grow the Seam's glued-filament pins into a half, before the split."""
        from geometry.seam_joint import add_pins

        f = self.frame
        substrate, upward = f.seam_pin_planes[name]
        seam = self.config.slide.split[name].seams(depth, f.wall)[0]
        return add_pins(
            body,
            seam,
            self.config.seam_pin,
            self.config.slide.seam_pin_sites.get(name, ()),
            substrate,
            upward,
        )

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
        """One Tray column: a straight boss from the floor to the plane.

        Every Tray wall is vertical now (ADR-0019), so the floor skin is the
        band's skin and the column no longer has to taper: it is the station's
        boss diameter top to bottom. The frustum path stays for a station
        whose floor margin is tighter than its band margin.
        """
        from utilities import cad_helpers as ch

        f = self.frame
        height = f.parting_z
        if station.base_boss >= station.boss - 1e-9:
            column = ch.cylinder_centered(station.boss, height)
        else:
            column = ch.frustum_centered(station.base_boss, station.boss, height)
        return ch.translate(column, station.x, station.y, height / 2.0)

    # -- accessory rail ---------------------------------------------------
    def _rail_mounts(self):
        """The rail's station pattern (ADR-0020), from the band joint."""
        from geometry.rail_mounts import rail_mounts

        mounts = rail_mounts(self.config, self.frame.chassis_joint)
        if not mounts.ok:
            raise ValueError(
                "the accessory rail's stations are invalid: "
                + "; ".join(mounts.failures)
            )
        return mounts

    def _rail_pad(self, station: Any):
        """One station's pad: a full-height column on the wall's cavity face."""
        from utilities import cad_helpers as ch

        f = self.frame
        height = f.parting_z - f.wall
        pad = ch.box_centered(station.pad_depth, station.pad_width, height)
        return ch.translate(
            pad,
            station.side * (station.x_inner - station.pad_depth / 2.0),
            station.y,
            f.wall + height / 2.0,
        )

    def _rail_gusset(self, station: Any, direction: int):
        """One 45 degree gusset from the pad's face down to the floor.

        The run is the station's shared, obstacle-derived value; the rib's tip
        is truncated one minimum feature before the floor, so it lands on a
        small vertical face instead of a knife edge.
        """
        from utilities import cad_helpers as ch

        f = self.frame
        floor = f.wall
        run = station.gusset_run
        tip = self.config.material.minimum_feature
        edge = station.y + direction * station.pad_width / 2.0
        profile = [
            (edge, floor),
            (edge, floor + run),
            (edge + direction * (run - tip), floor + tip),
            (edge + direction * (run - tip), floor),
        ]
        prism = ch.extrude_profile_x(profile, station.pad_depth)
        return ch.translate(
            prism, station.side * (station.x_inner - station.pad_depth / 2.0), 0.0, 0.0
        )

    def _rail_pocket(self, station: Any):
        """The square pocket the printed washer puck drops into."""
        from utilities import cad_helpers as ch

        over = 0.2
        depth = station.pocket_depth + over
        pocket = ch.box_centered(depth, station.pocket_side, station.pocket_side)
        return ch.translate(
            pocket,
            station.side * (station.x_pad_in - over / 2.0 + depth / 2.0),
            station.y,
            station.z,
        )

    def _rail_hole(self, station: Any):
        """The M4 clearance bore behind the pocket, through the wall."""
        from utilities import cad_helpers as ch

        over = 0.2
        length = station.x_outer - station.pocket_floor + 2.0 * over
        hole = ch.rotate_y(ch.cylinder_centered(station.clearance_hole, length), 90.0)
        return ch.translate(
            hole,
            station.side * (station.pocket_floor + length / 2.0 - over),
            station.y,
            station.z,
        )

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
    def tray_sections(self):
        """Split the Tray on its configured Seam (ADR-0015)."""
        from geometry.split import split_part

        return split_part(
            self.build_tray(),
            self.config.slide.split["chassis_tray"],
            self.frame.depth,
            self.frame.wall,
        )

    def deck_sections(self):
        """Split the Deck on its configured Seam (ADR-0015)."""
        from geometry.split import split_part

        return split_part(
            self.build_deck(),
            self.config.slide.split["chassis_deck"],
            self.frame.depth,
            self.frame.wall,
        )


__all__ = ["Chassis"]
