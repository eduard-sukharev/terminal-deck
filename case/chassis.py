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

Each band column's disc crosses a front/rear cavity wall face and leaves two
reentrant chords there; both halves fillet them into the wall
(``edge_treatment.merge_column_walls``, ADR-0024), so the band reads as one
smooth ridge. The Deck's Well ring is continuous over the plate's notches
(ADR-0024): the sheet below gives way at a front-wall station, the ring above
does not.

The bearing clamps are separate printed parts. Each is split on the bearing's
axis (ADR-0033); its lower half's foot drops through a pocket in the Deck, and
the Deck carries a small raised/merged seat with a pocket floor, so the clamp
is located and bolted from inside the chassis. The foot is the clamp's own
length, so the seat is a short block.
"""

from __future__ import annotations

from typing import Any

from case.slider_frame import SliderFrame
from geometry.printability import BED_DOWN, FACE_DOWN


def _treat(treatment, shape, *args, **kwargs):
    """Run an edge treatment, printing its SOFT warnings, and return the solid."""
    from utilities.validation import ValidationReport

    report = ValidationReport()
    result = treatment(shape, *args, report, **kwargs)
    for warning in report.warnings:
        print(f"[pipeline] warn: {warning}")
    return result


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

        # The base taper on the vertical front/rear walls (ADR-0019, ADR-0022,
        # ADR-0027) is a draft from the table up to the band's bottom -- the
        # cavity follows, so the wall keeps its thickness -- and its face at
        # the table passes through the long-wall stations' axes. Both of its
        # solids (the cavity-side fill and the outer wedge) come after the
        # station columns: the slice then passes through the long-wall bosses
        # instead of leaving them proud of the sloped face, and the merge
        # fillets see the plain cavity face.

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

        # A column at every station, from the floor up to the plane: a frustum
        # below the access cone's neck, a strict cylinder above it (ADR-0021).
        body = ch.union(body, *[self._column(station) for station in joint.stations])

        # ADR-0024/0025: ease each column's whole junction -- the chords along
        # the front/rear cavity walls, then the ring at its floor base -- while
        # the face still runs the column's full height. The taper fill below
        # narrows the cavity and would hide the chords, and the cones slice the
        # fillet at the floor, so the merge comes first. The Tray prints as
        # modelled: a column stands on its base, so the cove opens away from
        # the bed.
        body = self._treat_wall_columns(body, f.wall, 1.0, BED_DOWN)

        # ADR-0029: a corner column would still clip the inner corner chamfer
        # (its disc reaches 2.95 mm from the station, past the 2.83 mm relief),
        # leaving a 30-40 degree crease the merge fillet cannot roll. A web from
        # the column's axis into the X wall fills that corner, so the column
        # merges into both walls; the web's own chord and base are then eased.
        # The web comes after the wall-merge fillets: its step in the front wall
        # face sits close to the corner column's inboard chord, and OCC needs
        # that chord's fillet to run on the unbroken face first. Its radius is
        # the column's widest (base) radius so the frustum never pokes through
        # the web's inboard face below the access cone's neck.
        corner_radius = joint.corner_stations[0].base_boss / 2.0
        webs = self._corner_webs(corner_radius)
        body = ch.union(body, *self._corner_web_solids(webs, 0.0, z1, outer))
        body = self._treat_corner_webs(body, webs, f.wall, 1.0, BED_DOWN)


        # The taper's fill, now that the columns (and their merge fillets) are
        # in: the cavity-side wedge is backfilled under the sloped outer face.
        body = ch.union(body, taper_fill(f.base_taper))

        # The taper's wedge, now that the columns are in: through the wall and
        # the long-wall bosses, stopping at the corner pads' arcs.
        body = ch.cut(body, taper_cutter(f.base_taper))

        # The screw: a clearance hole through the column, its ordinary button
        # head buried at the top of a deep conical access cavity (ADR-0021).
        # The seat sits one wall below the Parting plane and the cone widens to
        # the floor face, so the driver enters straight along the axis. Cut
        # last so every cavity is exact.
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
            cavity = head_recess.build_deep_cutter(
                recess,
                mouth_radius=station.mouth_radius,
                x=station.x,
                y=station.y,
            )
            holes.extend((through, cavity))
        body = ch.cut(body, *holes)

        # Ease the access cones' own outside edges (ADR-0025, ADR-0027): the
        # mouth rims where a cone or a column frustum leaves the floor face,
        # and the lips where the taper flares a through-station's cone open.
        # Both are convex, so both take the 45 degree chamfer -- never a fillet
        # -- and the long edges where the walls meet the floor stay sharp (the
        # selector never picks them). A failing edge is skipped with a SOFT
        # warning, never blocking the build. The bed face is re-trimmed to
        # z = 0 afterwards for an exact printed bed.
        from geometry import edge_treatment
        from utilities.validation import ValidationReport

        size = self.config.edges.bed_chamfer
        treatment = ValidationReport()
        body = edge_treatment.chamfer_cone_cut(
            body, f.base_taper.angle, 0.0, size, treatment
        )
        for warning in treatment.warnings:
            print(f"[pipeline] warn: {warning}")
        body = ch.cut(body, ch.half_space((0.0, 0.0, 0.0), (0.0, 0.0, -1.0), size=300.0))

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
        # ADR-0030: break each printed Section's bed edge. The Tray prints
        # floor down, so its bed face is the floor; after the split that edge
        # runs along the bent Seam too, leaving the joined halves a V-groove.
        body = self._chamfer_sections(
            body, "chassis_tray", BED_DOWN, f.depth, self._cone_mouth_discs()
        )
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
        # cavity, so it is unioned back onto the shell. Both the plate border
        # and the Cutout follow the keyboard's per-row outline, so a stepped
        # layout (a narrow spacebar row) keeps the ring one wall wide band by
        # band; a rectangular layout's polygons are plain rectangles.
        if mounts.plate_polygon and mounts.cutout_polygon:
            ring = ch.extrude_polygon(
                list(mounts.plate_polygon),
                ring_height,
                z=plate_top + ring_height / 2.0,
            )
            opening = ch.extrude_polygon(
                list(mounts.cutout_polygon),
                ring_height + 2.0,
                z=plate_top + ring_height / 2.0,
            )
            ring = ch.cut(ring, opening)
        else:  # legacy caller with no stepped outline: the old rectangle
            ring = ch.box_centered(plate.width, plate.depth, ring_height)
            ring = ch.translate(
                ring, plate.cx, plate.cy, plate_top + ring_height / 2.0
            )
            opening = ch.box_centered(cut.width, cut.depth, ring_height + 2.0)
            opening = ch.translate(
                opening, cut.cx, cut.cy, plate_top + ring_height / 2.0
            )
            ring = ch.cut(ring, opening)
        # ADR-0024: the ring is continuous. Where a chassis band column reaches
        # into the plate's border the plate below is still notched (the sheet
        # gives way, the column is Deck material), but the ring above fills the
        # same plan area and fuses to the band boss; the Well's outer face reads
        # as one unbroken wall instead of five stray cutouts.
        body = ch.union(body, ring)

        # The Cutout is open through the top slab: the keycaps pass through it
        # and the ring surrounds it. It is sized by the keycaps plus wobble,
        # never by `clearance.shell`.
        if mounts.cutout_polygon:
            well = ch.extrude_polygon(
                list(mounts.cutout_polygon), 3.0 * wall, z=top
            )
        else:
            well = ch.box_centered(cut.width, cut.depth, 3.0 * wall)
            well = ch.translate(well, cut.cx, cut.cy, top)
        body = ch.cut(body, well)

        # One M2 insert boss per plate station, merged to the ring's outer face
        # inside the front/rear lip. It stands on the plate's top face (the
        # plate's ear is below it), so no boss can enter the Cutout, and runs
        # up to the Deck's inner ceiling: the Deck prints face down, so a boss
        # that stopped at the insert would be an unsupported overhang. A boss
        # in a lip only a sliver wider than itself (the front one) is grown
        # outboard into the facing wall as a rectangle (ADR-0026): the boss
        # then merges with both walls instead of leaving an unprintable sliver.
        well_bosses, bridged, plain = self._well_boss_solids(mounts)
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

        # ADR-0024/0025/0026: each boss's wall chords and base ring are eased
        # together where they meet, in the order the crowded geometry allows.
        # A chord and its base ring meet at a vertex, so treating them one set
        # after the other leaves the second edge on the first fillet's surface,
        # which OCC cannot roll off. The band bosses are unioned first so their
        # chords run the face's full height.
        body = self._treat_deck_junctions(
            body, mounts, bridged, plain, cavity_top
        )

        # ADR-0029: the same web as the Tray's, so a corner boss merges into
        # both the front/rear and the X wall and the corner chop is filled
        # automatically. The Deck's boss is one diameter over its whole height,
        # so the web uses the boss radius. It goes after the junction fillets
        # for the same reason as the Tray's (the step it leaves in the front
        # wall face crowds the corner boss's inboard chord).
        webs = self._corner_webs(joint.boss / 2.0)
        body = ch.union(body, *self._corner_web_solids(webs, z0, cavity_top, outer))
        body = self._treat_corner_webs(body, webs, cavity_top, -1.0, FACE_DOWN)

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
        # ADR-0030: the Deck prints closed face down, so its bed face is the
        # top: the break runs round the closed face, the Well's mouth and the
        # straight Seam (the seat pockets keep their own `top_chamfer`).
        body = self._chamfer_sections(body, "chassis_deck", FACE_DOWN, f.depth)
        return ch.clean(body)

    def _cone_mouth_discs(self):
        """Discs over the access cone mouths the Tray's bed chamfer must skip.

        The cones already took their own bed chamfer (``chamfer_cone_cut``);
        the through-stations' mouths that open onto the floor's outer wire sit
        at ``mouth_radius + bed_chamfer`` from the axis, so a second pass would
        eat the corner pads' ring.
        """
        size = self.config.edges.bed_chamfer
        return [
            (station.x, station.y, station.mouth_radius + size)
            for station in self.frame.chassis_joint.stations
        ]

    def _chamfer_sections(self, body, name, orientation, depth, exclude=()):
        """Split a half on its Seam, break each Section's bed edge, rejoin.

        ``bed_chamfer`` is applied per Section, so the Seam is part of that
        Section's bed face boundary and gets the same 45 degree bevel: the
        joined halves read as a V-groove along the Seam rather than a raw
        hairline (ADR-0030). The whole half is the union of the treated
        Sections, so the reference export and the assembly show the printed
        edges. ``exclude`` names the discs ``bed_chamfer`` must leave alone.
        """
        from geometry import edge_treatment
        from utilities.validation import ValidationReport

        report = ValidationReport()
        whole = edge_treatment.chamfer_sections(
            body,
            self.config.slide.split[name],
            depth,
            self.frame.wall,
            orientation,
            self.config.edges.bed_chamfer,
            report,
            exclude,
        )
        for warning in report.warnings:
            print(f"[pipeline] warn: {warning}")
        return whole

    def _add_seam_pins(self, body, name: str, depth: float):
        """Grow the Seam's glued-filament pins into a half, before the split."""
        from geometry.seam_joint import add_pins

        f = self.frame
        substrate, upward = f.seam_pin_planes[name]
        seam = self.config.slide.split[name].seams(depth, f.wall)[0]
        sites = self._seam_pin_sites(name)
        return add_pins(
            body,
            seam,
            self.config.seam_pin,
            sites,
            substrate,
            upward,
        )

    def _seam_pin_sites(self, name: str) -> tuple[float, ...]:
        """The Seam's pin sites, derived where the keyboard's depth decides.

        The Deck's rear band sits behind the keyboard, so its Seam pins must
        clear the keyboard's rear edge -- a 60% board's plate is deeper than a
        40%'s and reaches the configured sites. ``config.slide.seam_pin_sites``
        stays the source; a ``chassis_deck`` site that falls inside the
        keyboard's footprint is walked back into the free rear band (the
        keyboard's rear edge plus the pocket's half-width and the printable
        minimum), so the pin never lands under the keycaps.
        """
        sites = tuple(self.config.slide.seam_pin_sites.get(name, ()))
        if name != "chassis_deck" or not sites:
            return sites
        frame = getattr(self.frame, "plate_frame", None)
        if frame is None:
            return sites
        pin = self.config.seam_pin
        # The keyboard's rear edge in the chassis plan: the plate's rear face.
        keyboard_rear = frame.y1
        clear = keyboard_rear + pin.pocket_width / 2.0 + self.config.material.minimum_feature
        return tuple(site if site >= clear else clear for site in sites)

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
    def _corner_webs(self, radius):
        """The corner columns' webs into the X walls (ADR-0029)."""
        from geometry.corner_web import corner_webs

        f = self.frame
        webs = corner_webs(
            f.chassis_joint, f.wall, self.config.corners.chamfer, radius
        )
        if not webs.ok:
            raise ValueError(
                "the corner webs are invalid: " + "; ".join(webs.failures)
            )
        return webs

    def _corner_web_solids(self, webs, z0, z1, outer):
        """One clipped prism per corner web, from ``z0`` to ``z1``."""
        from utilities import cad_helpers as ch

        solids = []
        for web in webs.webs:
            x0, x1, y0, y1 = web.plan()
            prism = ch.box_centered(x1 - x0, y1 - y0, z1 - z0)
            prism = ch.translate(
                prism, (x0 + x1) / 2.0, (y0 + y1) / 2.0, (z0 + z1) / 2.0
            )
            solids.append(ch.intersect(prism, outer))
        return solids

    def _treat_corner_webs(self, body, webs, plane_z, axis, orientation):
        """Ease each web's X-wall chord and its base in one variable pass."""
        from geometry import edge_treatment
        from utilities.validation import ValidationReport

        joint = self.config.chassis_joint
        report = ValidationReport()
        chords = edge_treatment.web_junction_edges(body, webs.webs, orientation)
        bases = edge_treatment.web_base_edges(
            body, webs.webs, plane_z, axis, orientation
        )
        body = edge_treatment.fillet_junctions(
            body, chords, bases, joint.column_fillet, joint.boss_base_fillet,
            report,
        )
        # The corner blend at the wall end of the base edge can leave a short
        # sharp stub behind (the two fillet surfaces need a transition there).
        # A second, base-only pass takes it: it no longer shares a vertex with
        # a fresh chord fillet, so it can roll on its own.
        leftover = edge_treatment.web_base_edges(
            body, webs.webs, plane_z, axis, orientation
        )
        if leftover:
            body = edge_treatment.web_base_residual(
                body, webs.webs, plane_z, axis, joint.boss_base_fillet,
                report, orientation,
            )
        for warning in report.warnings:
            print(f"[pipeline] warn: {warning}")
        return body

    def _band_columns(self):
        """The twelve band stations as ``(x, y, r_min, r_max)`` column discs."""
        return [
            (
                station.x,
                station.y,
                min(station.strict_boss, station.base_boss) / 2.0,
                max(station.strict_boss, station.base_boss) / 2.0,
            )
            for station in self.frame.chassis_joint.stations
        ]

    def _treat_boss_junctions(
        self, body, columns, faces_y, plane_z, axis, orientation, *,
        chords=True, bases=True,
    ):
        """Ease a boss's whole junction: its wall chords and/or its base ring.

        ADR-0024 eases the vertical chords where a column's disc crosses a
        front/rear wall face; ADR-0025 rounds the ring where it springs from
        its floor or ceiling. The chords go first: the base round's endpoints
        land on the merge they leave, so the two cannot share one pass (OCC
        cannot roll a fillet off another fillet's surface). The base round then
        takes the largest radius that stays clear of the merge, ``boss_base_fillet``.
        ``axis`` is the direction along Z the boss grows from ``plane_z``;
        ``orientation`` is the part's print orientation, which decides whether
        the base round opens away from the bed. A failing edge is skipped with
        a SOFT warning, never blocking the build.

        ``chords`` and ``bases`` split the two passes so a part with several
        boss families can run every chord merge before any base round: a base
        round beside a neighbouring family's chord would otherwise block it.
        """
        from geometry import edge_treatment

        joint = self.config.chassis_joint
        if chords:
            body = _treat(
                edge_treatment.merge_column_walls,
                body, columns, faces_y, joint.column_fillet,
            )
        if bases:
            body = _treat(
                edge_treatment.fillet_boss_bases,
                body, columns, plane_z, axis, joint.boss_base_fillet,
                orientation=orientation,
            )
        return body

    def _treat_wall_columns(
        self, body, plane_z, axis, orientation, *, chords=True, bases=True
    ):
        """Treat the band columns' cavity-wall chords and/or their bases."""
        f = self.frame
        return self._treat_boss_junctions(
            body, self._band_columns(), f.depth / 2.0 - f.wall,
            plane_z, axis, orientation, chords=chords, bases=bases,
        )

    def _treat_deck_junctions(self, body, mounts, bridged, plain, plane_z):
        """Fillet every Deck boss's wall chords and base edges, boss by boss.

        The Well's M2 bosses, the rectangles bridged into the facing wall and
        the band columns all stand on the Deck's inner ceiling. A boss's
        vertical chord and its base edge meet at a vertex, so they are eased in
        one variable pass: treating them one set after the other leaves the
        second edge on the first fillet's surface, which OCC cannot roll off.
        ``plane_z`` is the ceiling the bosses stand on; the Deck prints face
        down, so the base cove opens away from the bed.

        The order is what the crowded geometry allows. Each bridged rectangle's
        ring-side chord goes first, then the band columns run the cavity wall's
        full height, then each rectangle's wall-side chord and base edges, then
        the plain Well bosses and the band bases. A crowded edge that OCC
        cannot roll is skipped with a SOFT warning.
        """
        from geometry import edge_treatment
        from utilities.validation import ValidationReport

        joint = self.config.chassis_joint
        plate = mounts.frame.rect
        well_faces = (abs(plate.y0), abs(plate.y1))
        band_faces = self.frame.depth / 2.0 - self.frame.wall
        report = ValidationReport()

        def treat(chords, bases, chord_radius):
            return edge_treatment.fillet_junctions(
                body, chords, bases, chord_radius, joint.boss_base_fillet,
                report,
            )

        # The band columns' cavity-wall chords are the HARD joint; easing them
        # first also lets their beads bury the bridged rectangles' wall-side
        # chords where the two crowd one wall face.
        body = self._treat_wall_columns(
            body, plane_z, -1.0, FACE_DOWN, bases=False
        )
        for rect in bridged:
            body = treat(
                edge_treatment.rect_junction_edges(
                    body, [rect], well_faces, FACE_DOWN
                )
                + edge_treatment.rect_junction_edges(
                    body, [rect], band_faces, FACE_DOWN
                ),
                edge_treatment.rect_base_edges(
                    body, [rect], plane_z, -1.0, FACE_DOWN
                ),
                joint.boss_base_fillet,
            )
        for column in plain:
            body = treat(
                edge_treatment.column_junction_edges(
                    body, [column], well_faces, FACE_DOWN
                ),
                edge_treatment.boss_base_edges(
                    body, [column], plane_z, -1.0, FACE_DOWN
                ),
                joint.column_fillet,
            )
        body = self._treat_wall_columns(
            body, plane_z, -1.0, FACE_DOWN, chords=False
        )

        for warning in report.warnings:
            print(f"[pipeline] warn: {warning}")
        return body

    def _well_boss_solids(self, mounts):
        """The plate's M2 bosses, a tight-lip boss bridged as a rectangle.

        A boss in a lip only a sliver wider than itself (the front lip is
        5.65 mm for a 5.50 mm boss) leaves an unprintable gap to the facing
        cavity wall while merging into the ring on the other side. ADR-0026
        grows such a boss outboard as a rectangle: the inboard end sits
        ``minimum_feature`` inside the ring, the outboard end
        ``minimum_feature`` inside the facing wall, and its flat sides carry
        the wall fillets. A boss whose lip is deeper than one wall stays a
        plain cylinder. Returns the solids, the bridged bosses' plan rectangles
        ``(cx, y_in, y_out, half_width)`` and the plain bosses' column discs.
        """
        from utilities import cad_helpers as ch

        f = self.frame
        wall = f.wall
        wall_face = f.depth / 2.0 - wall
        embed = self.config.material.minimum_feature
        plate = mounts.frame.rect
        solids = []
        bridged = []
        plain = []
        for m in mounts.mounts:
            radius = m.boss_diameter / 2.0
            height = m.boss_z1 - m.boss_z0
            sign = 1.0 if m.y > 0.0 else -1.0
            # The sliver the boss would otherwise leave to the facing wall.
            gap = wall_face - abs(m.y) - radius
            if gap < wall:
                ring_face = plate.y0 if sign < 0 else plate.y1
                y_in = ring_face - sign * embed
                y_out = sign * (wall_face + embed)
                solids.append(
                    ch.rect_prism(radius, y_in, y_out, height, x=m.x, z=m.boss_z0)
                )
                bridged.append((m.x, y_in, y_out, radius))
            else:
                solids.append(
                    ch.translate(
                        ch.cylinder_centered(m.boss_diameter, height),
                        m.x,
                        m.y,
                        (m.boss_z0 + m.boss_z1) / 2.0,
                    )
                )
                plain.append((m.x, m.y, radius, radius))
        return solids, bridged, plain

    def _column(self, station: Any):
        """One Tray column: conical below the cone's neck, strict above.

        Below the access cone's neck (ADR-0021) the column is a frustum from
        its floor footprint down to the strict diameter, its outer wall running
        conical beside the cavity; from the neck to the Parting plane it is a
        plain cylinder with strict dimensions around the head pocket and the
        screw hole.
        """
        from utilities import cad_helpers as ch

        f = self.frame
        height = f.parting_z
        z_neck = f.chassis_joint.recess.z_neck
        cone = ch.frustum_centered(
            station.base_boss, station.strict_boss, z_neck
        )
        cone = ch.translate(cone, station.x, station.y, z_neck / 2.0)
        strict = ch.cylinder_centered(
            station.strict_boss, height - z_neck
        )
        strict = ch.translate(
            strict, station.x, station.y, z_neck + (height - z_neck) / 2.0
        )
        return ch.union(cone, strict)

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
        """The square pocket the printed washer puck drops into.

        The pocket's ceiling is not flat: it is a 45 degree ramp over the
        pocket's whole depth (``RailStation.pocket_ramp``), because a flat
        ceiling at the pocket's top would hang over the pocket for the pad's
        depth when the Tray prints floor down. The ramp climbs from the
        nominal ceiling plane at the pocket's floor up to the pad's cavity
        face and leaves ``pocket_lip`` of pad above the mouth. The cutter is a
        profile rather than a chamfered box so the bevel is exact and OCC
        never has to relieve the thin lip or the pier behind the pocket.
        """
        from utilities import cad_helpers as ch

        over = 0.2
        z0 = station.z - station.pocket_side / 2.0
        z1 = z0 + station.pocket_side
        xa = station.x_pad_in - over / 2.0
        xb = station.pocket_floor + over / 2.0
        # The 45 degree ramp passes through the nominal ceiling corner
        # (pocket_floor, z1) and meets the pad's face at z1 + pocket_ramp, so
        # the pier's 0.1 over-cut stops that far below the ceiling and the
        # ramp closes it: no horizontal face is left anywhere over the pocket.
        profile = [
            (xa, z0),
            (xb, z0),
            (xb, z1 - over / 2.0),
            (station.x_pad_in, z1 + station.pocket_ramp),
            (xa, z1 + station.pocket_ramp),
        ]
        prism = ch.extrude_profile_y(
            [(station.side * x, z) for x, z in profile], station.pocket_side
        )
        return ch.translate(prism, 0.0, station.y, 0.0)

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
        """A bearing-clamp seat block merged into the Deck and side wall.

        The block's top is the Deck's top face; the pocket is cut down into that
        top face to exactly the foot's thickness. The lower half's foot fills
        the seat's height (ADR-0033), so the pocket's floor is one `seat_floor`
        above the seat's own floor: the foot rests on a solid 2 mm floor. The
        clamp screws come up from inside the chassis and compress that floor
        against the foot; the seat stays solid under them and the foot's top
        face is flush with the Deck top and the back-panel slot meets it
        exactly.
        """
        from utilities import cad_helpers as ch

        f = self.frame
        if f.seat_height - f.pocket_depth < self.config.material.minimum_feature - 1e-9:
            raise ValueError(
                "the Bearing-clamp seat has no floor under its pocket "
                f"(seat {f.seat_height:.2f} - pocket {f.pocket_depth:.2f} < "
                f"min feature): the screw head would have nothing to bear on"
            )
        block = ch.box_centered(f.seat_width, f.seat_length, f.seat_height)
        block = ch.translate(
            block,
            side * f.rod_x,
            f.clamp_center_y,
            f.chassis_top - f.seat_height / 2.0,
        )
        return block

    def _seat_pocket(self, side: int):
        """The pocket that receives the Bearing clamp foot.

        It is cut down from the Deck's top face exactly as deep as the foot is
        thick, so the foot's underside rests on the seat's own floor (the
        Deck's inner ceiling). The one extra millimetre sits *above* the Deck
        top, outside the solid, so the cut breaks through cleanly without
        leaving a skin.
        """
        from utilities import cad_helpers as ch

        f = self.frame
        pocket = ch.box_centered(
            f.pocket_width, f.pocket_length, f.pocket_depth + 1.0
        )
        corner = self.config.slide.bearing_clamp.corner_chamfer
        if corner > 0.0:
            # Match the clamp foot's vertical corner relief (the foot and the
            # body share one silhouette, so a plain box would clash at the
            # corners).
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
        rim = []
        for edge in ch.convex_edges(body):
            if abs(edge.midpoint[2] - f.chassis_top) >= 1e-6:
                continue
            dx = min(
                abs(edge.midpoint[0] - side * f.rod_x) for side in (-1, 1)
            )
            dy = abs(edge.midpoint[1] - f.clamp_center_y)
            # Only the rim's four straight sides: the corner-chamfer edges
            # sit about 1 mm inboard of both nominal boundaries and OCC crashes
            # when they are chamfered in the same pass as the straight sides.
            # The short side lands ~3e-4 mm off its nominal half-width after
            # the pocket's corner cut, so the match uses a small tolerance but
            # stays far from the corner edges.
            if (
                abs(dx - f.pocket_width / 2.0) <= 1e-3
                or abs(dy - f.pocket_length / 2.0) <= 1e-3
            ):
                rim.append(edge)
        return ch.chamfer_edges(body, rim, amount)

    def _seat_hole(self, side: int):
        """Two clearance bores through the seat floor for the clamp screws.

        The clamp screws are driven **up from inside the chassis** (ADR-0033):
        each head sits in the Deck's cavity under the seat and compresses the
        seat floor against the lower half's foot, then passes the foot and the
        belly and threads into the upper half's heat-set insert.  So the Deck
        cuts a plain clearance bore -- the seat floor keeps its full thickness
        (it is the screw head's bearing face) and nothing self-taps here.  The
        bore is a separate cut from the pocket: the pocket's corner chamfer and
        the seat's rim are already treated, and one pass over both would break
        the deck's own edge network.
        """
        from utilities import cad_helpers as ch
        from utilities.fasteners import screw as screw_spec

        f = self.frame
        spec = screw_spec(self.config.slide.bearing_clamp.screw)
        # The screws sit beside the bore, one each side of the rod; the span is
        # the budget's derived pair distance (ADR-0033).
        span = f.clamp_span
        holes = []
        for screw_side in (-1, 1):
            hole = ch.cylinder_centered(spec.clearance, f.seat_height + 2.0)
            hole = ch.translate(
                hole,
                side * f.rod_x + screw_side * span / 2.0,
                f.clamp_center_y,
                f.chassis_top - f.seat_height / 2.0,
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
