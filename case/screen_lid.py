"""Slider screen lid: a Bezel carrying the display, closed by a Back plate.

The lid splits at the Back panel's inner face (ADR-0011). The Back is a flat
4 mm plate: it faces the keyboard, carries the two Guide rods (two printed Rod
clamps each) and the two long through-slots the Bearing clamps slide in. The
Bezel is the inverted tray: the glass opening, the display cavity, the
prismatic fastening band at its bottom and the eight band posts the Back's
countersunk screws thread into.

The rods/bearings/clamps are separate printed/purchased parts (the ``slide``
target). The FPC guard is a separate printed plate built by this module
(``build_fpc_guard``): it is bonded to the display's back, not part of the lid
shell, so it is exported and printed on its own.
"""

from __future__ import annotations

from typing import Any

from case.slider_frame import SliderFrame


class ScreenLid:
    """The upper half of the slider: Bezel tray, Back plate, rod hardware."""

    def __init__(self, config: Any, frame: SliderFrame) -> None:
        self.config = config
        self.frame = frame

    # -- parts -----------------------------------------------------------
    def build(self):
        """Return the assembled lid as a two-part compound (Bezel + Back)."""
        from utilities import cad_helpers as ch

        ch.require_cad()
        return ch.make_compound([self.build_bezel(), self.build_back()])

    def build_back(self):
        """The flat back panel: rod slots and grooves, clamp and joint holes."""
        from geometry import head_recess
        from utilities import cad_helpers as ch
        from utilities.fasteners import heat_insert, screw as screw_spec

        ch.require_cad()
        f = self.frame
        joint = f.lid_joint

        body = ch.box_centered(f.width, f.lid_height, f.lid_back)
        body = ch.translate(
            body, 0.0, f.lid_y_center, (f.panel_outer_z + f.panel_inner_z) / 2.0
        )
        body = ch.chamfer_vertical_edges(body, self.config.corners.chamfer)

        insert = heat_insert(self.config.slide.rod_clamp.screw)
        insert_hole = insert.printed_hole_diameter
        insert_depth = min(insert.depth, f.lid_back - 0.5)

        for side in (-1, 1):
            # Long through-slot between the rod clamps: the Bearing clamp
            # neck passes through it and travels along it.
            slot = ch.box_centered(f.slot_width, f.slot_len, f.lid_back + 2.0)
            slot = ch.translate(
                slot,
                side * f.rod_x,
                (f.slot_y0 + f.slot_y1) / 2.0,
                (f.panel_outer_z + f.panel_inner_z) / 2.0,
            )
            body = ch.cut(body, slot)

            for center_y in f.rod_clamp_y:
                # Shallow groove under each Rod clamp: the bearing stops
                # short of the clamp, so the rod is pinched between this floor
                # and the clamp's half-bore.
                groove = ch.box_centered(
                    f.rod_groove_width, f.rod_clamp_len, f.rod_groove_depth
                )
                groove = ch.translate(
                    groove,
                    side * f.rod_x,
                    center_y,
                    f.panel_inner_z - f.rod_groove_depth / 2.0,
                )
                body = ch.cut(body, groove)

                # Heat-set insert holes for the Rod clamps, from the inner face.
                for screw_side in (-1, 1):
                    hole = ch.translate(
                        ch.cylinder_centered(insert_hole, insert_depth + 1.0),
                        side * f.rod_x + screw_side * f.rod_clamp_screw_span / 2.0,
                        center_y,
                        f.panel_inner_z - insert_depth / 2.0 + 0.5,
                    )
                    body = ch.cut(body, hole)

        # The band joint: a button-head screw at every station, from the outer
        # face, through the plate into the Bezel's insert. The head seats in a
        # keyhole recess in the plate's outer face, ramp pointing inboard
        # (ADR-0018).
        spec = screw_spec(joint.screw.size)
        recess = joint.recess
        holes = []
        for station in joint.stations:
            through = ch.translate(
                ch.cylinder_centered(spec.clearance, f.lid_back + 2.0),
                station.x,
                station.y,
                (f.panel_outer_z + f.panel_inner_z) / 2.0,
            )
            keyhole = head_recess.build_cutter(
                recess,
                normal=station.normal,
                mouth=station.mouth_chamfer,
                x=station.x,
                y=station.y,
                z0=f.panel_outer_z,
            )
            holes.extend((through, keyhole))
        body = ch.cut(body, *holes)
        # ADR-0006: the Seam's pins stand on the plate's inner face.
        body = self._add_seam_pins(body, "screen_lid_back")
        return ch.clean(body)

    def _outer_shell(self):
        """The Bezel's outside: the prismatic band plus the drafted face tray.

        Every feature of the Bezel has to stay inside this solid; it is what
        the wall thickness and the outer chamfers are measured from.
        """
        from utilities import cad_helpers as ch

        f = self.frame
        chamfer = self.config.corners.chamfer
        z0, z1, top = f.band_z0, f.band_z1, f.lid_top

        band = ch.box_centered(f.width, f.lid_height, z1 - z0)
        band = ch.translate(band, 0.0, f.lid_y_center, (z0 + z1) / 2.0)
        outer = ch.chamfer_vertical_edges(band, chamfer)
        if top > z1:
            outer = ch.union(
                outer,
                ch.tapered_box(
                    f.width,
                    f.lid_height,
                    f.lid_face_width,
                    f.lid_height,
                    z1,
                    top,
                    chamfer=chamfer,
                    y=f.lid_y_center,
                ),
            )
        return outer

    def build_bezel(self):
        """The display tray: prismatic band, tapered walls, window, posts."""
        from utilities import cad_helpers as ch

        ch.require_cad()
        f = self.frame
        joint = f.lid_joint
        wall = f.wall
        z0, z1, top = f.band_z0, f.band_z1, f.lid_top
        chamfer = self.config.corners.chamfer
        outer = self._outer_shell()

        # Open cavity: the band's inside is straight, the rest follows the
        # drafted side walls, keeping the wall thickness constant. Its vertical
        # corners carry the inner chamfer, so the corner stays one `wall` thick
        # behind the outer chop instead of meeting it in a knife edge.
        cavity_chamfer = ch.inner_corner_chamfer(chamfer, wall)
        cavity_z1 = top - f.lid_front
        cavity = ch.tapered_box(
            f.width - 2.0 * wall,
            f.lid_height - 2.0 * wall,
            f.width - 2.0 * wall,
            f.lid_height - 2.0 * wall,
            z0,
            z1,
            chamfer=cavity_chamfer,
            y=f.lid_y_center,
        )
        if cavity_z1 > z1:
            top_width = (
                f.lid_face_width
                + 2.0 * ch.draft_inset(f.draft_angle, f.lid_front)
                - 2.0 * wall
            )
            cavity = ch.union(
                cavity,
                ch.tapered_box(
                    f.width - 2.0 * wall,
                    f.lid_height - 2.0 * wall,
                    top_width,
                    f.lid_height - 2.0 * wall,
                    z1,
                    cavity_z1,
                    chamfer=cavity_chamfer,
                    y=f.lid_y_center,
                ),
            )
        body = ch.cut(outer, cavity)

        # Band posts: the four corners (outboard of the Rod clamps) and a square
        # pad at each long-side station, both merged into the perimeter wall.
        # They keep their full depth over the band, where the insert sits, and
        # are capped at the band's top by the 45 degree support their face-down
        # print needs (see `_band_post`).
        posts = []
        for sx in (-1, 1):
            for sy in (-1, 1):
                x0, x1 = joint.post_x
                y0, y1 = joint.post_y
                if sx < 0:
                    x0, x1 = -x1, -x0
                if sy < 0:
                    y0, y1 = -y1, -y0
                posts.append(
                    self._band_post(
                        x0,
                        x1,
                        y0,
                        y1,
                        free_x=(sx > 0, sx < 0),
                        free_y=(sy > 0, sy < 0),
                    )
                )
        for station in joint.edge_stations:
            # `station_inset` puts the pad's outer half inside the wall, so the
            # pad and the perimeter wall merge into one solid post.
            half = joint.boss / 2.0
            posts.append(
                self._band_post(
                    station.x - half,
                    station.x + half,
                    station.y - half,
                    station.y + half,
                    free_x=(True, True),
                    free_y=(station.y > 0, station.y < 0),
                )
            )
        body = ch.union(body, *posts)

        # Heat-set inserts for the Back's countersunk screws, from the band's
        # underside.
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

        # Glass opening plus the display-frame pocket in the front panel's
        # inner face (the remaining lip retains the frame).
        inset = self.config.bezel.inset
        recess = f.bezel_recess
        window = ch.box_centered(
            f.display_w - 2.0 * inset,
            f.display_d - 2.0 * inset,
            f.lid_front + 2.0,
        )
        window = ch.translate(window, 0.0, f.display_y, top - f.lid_front / 2.0)
        pocket = ch.box_centered(
            f.display_w + 2.0 * f.clearance,
            f.display_d + 2.0 * f.clearance,
            recess + 1.0,
        )
        pocket = ch.translate(
            pocket,
            0.0,
            f.display_y,
            top - f.lid_front + (recess - 1.0) / 2.0,
        )
        body = ch.cut(body, window, pocket)
        # ADR-0006: the Seam's pins hang from the front panel's inner face.
        body = self._add_seam_pins(body, "screen_lid_bezel")
        return ch.clean(body)

    def _band_post(self, x0, x1, y0, y1, free_x, free_y):
        """One band post: the screw's block plus its 45 degree support cap.

        The Bezel prints face down, its front panel on the bed, so the band is
        the *last* thing printed. A post that simply stopped at the band's top
        would print its flat top as a bare ledge hanging off the wall. The cap
        carries that ledge at 45 degrees into the wall the post is merged into
        (`free_x`/`free_y` name the cavity-facing sides); the post below it
        keeps its full footprint, so the insert stays buried in the same block
        of material.

        The cap is trimmed to the shell: the Bezel's outside is not prismatic
        above the band, it draws in toward the face panel, so a cap that grew
        straight out of the post would poke through the drafted wall (and past
        the outer chamfer) at the corners.
        """
        from utilities import cad_helpers as ch

        f = self.frame
        z0, z1 = f.band_z0, f.band_z1
        post = ch.box_centered(x1 - x0, y1 - y0, z1 - z0)
        post = ch.translate(
            post, (x0 + x1) / 2.0, (y0 + y1) / 2.0, (z0 + z1) / 2.0
        )
        cap = ch.support_cap((x0, x1, y0, y1), z1, free_x=free_x, free_y=free_y)
        return ch.intersect(ch.union(post, cap), self._outer_shell())

    def _add_seam_pins(self, body, name: str):
        """Grow the Seam's glued-filament pins into a half, before the split."""
        from geometry.seam_joint import add_pins

        f = self.frame
        substrate, upward = f.seam_pin_planes[name]
        seam = self.config.slide.split[name].seams(f.lid_height, f.wall)[0]
        return add_pins(
            body,
            seam,
            self.config.seam_pin,
            self.config.slide.seam_pin_sites.get(name, ()),
            substrate,
            upward,
        )

    # -- the FPC guard ---------------------------------------------------
    def build_fpc_guard(self):
        """The printed grille plate that guards the display's FPC ribbon.

        Local origin: the display's back face, on the display's centre. The
        plate spans ``z = -total..0``: the ribbon channel is recessed from the
        display-facing side (``recess`` deep, open at both ends so the ribbon
        can leave toward the driver) and the blind grille slots are cut from
        the underside, leaving ``minimum_feature`` of grille floor under the
        channel. Bonded to the display's back with tape; the moving
        Bearing-clamp head can only ever reach the plate's underside.
        """
        from utilities import cad_helpers as ch

        ch.require_cad()
        f = self.frame
        guard = f.fpc_guard
        gx0, gy0, gx1, gy1 = f.guard_planform
        x0, x1 = gx0 - f.display_x, gx1 - f.display_x
        y0, y1 = gy0 - f.display_y, gy1 - f.display_y
        cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0

        body = ch.box_centered(x1 - x0, y1 - y0, guard.total)
        body = ch.translate(body, cx, cy, -guard.total / 2.0)

        # The ribbon channel, cut from the display-facing side. Open at both X
        # ends by running the cutter past them.
        channel = ch.box_centered(
            (x1 - x0) + 2.0, f.guard_channel_width, guard.recess + 1.0
        )
        channel = ch.translate(channel, cx, cy, -guard.recess / 2.0 + 0.5)
        body = ch.cut(body, channel)

        # Blind grille slots from the underside: along X (the ribbon's run),
        # one border of minimum feature all round, struts between them.
        border = self.config.material.minimum_feature
        slot = guard.grille_slot
        inset = border + slot / 2.0
        slots = []
        y = y0 + inset
        while y <= y1 - inset + 1e-9:
            cutter = ch.box_centered(
                (x1 - x0) - 2.0 * border,
                slot,
                f.guard_slot_depth + 1.0,
            )
            slots.append(
                ch.translate(
                    cutter, cx, y, -guard.total + f.guard_slot_depth / 2.0 - 0.5
                )
            )
            y += f.guard_slot_pitch
        return ch.clean(ch.cut(body, *slots))

    # -- printing --------------------------------------------------------
    def bezel_sections(self):
        """Split the Bezel on its configured Seam (ADR-0015)."""
        from geometry.split import split_part

        return split_part(
            self.build_bezel(),
            self.config.slide.split["screen_lid_bezel"],
            self.frame.lid_height,
            self.frame.wall,
        )

    def back_sections(self):
        """Split the Back plate on its configured Seam (ADR-0015)."""
        from geometry.split import split_part

        return split_part(
            self.build_back(),
            self.config.slide.split["screen_lid_back"],
            self.frame.lid_height,
            self.frame.wall,
        )


__all__ = ["ScreenLid"]
