"""Slide subsystem: the slider's travel, guide span and face-height budget.

Pure data — no CAD. The screen lid carries two steel Guide rods on its back
panel's inner face, each held by two printed Rod clamps; the printed Bearing
clamps straddle the back panel through a long slot and are seated in the
Chassis Deck (ADR-0010/0013). The rods sit **under the display**, so they no
longer set the case width; the moving Bearing-clamp head passes under the
panel instead, which is what sets the lid's thickness. A printed FPC grille
plate guards the display's ribbon where that head sweeps it.

The closed face height is the binding constraint, so the budget is derived from
the real keyboard/display/driver sizes and the slide config and checked by the
build.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from routing.cable_routing import CONNECTOR_HDMI, MIN_BEND_RADIUS_MM

from components.keycap_set import CAP_PLATE_GAP
from geometry.base_taper import base_taper, base_taper_angle
from geometry.chassis_joint import chassis_joint as chassis_band_joint
from geometry.joint import lid_joint
from utilities import fasteners

#: Radial clearance of the clamp's bore over the purchased bearing (mm): the
#: bearing is a slip fit, so it can drop into the split bore by hand.
_BEARING_BORE_CLEARANCE = 0.2


@dataclass(frozen=True)
class WelledPlate:
    """The keyboard plate and the Deck's Well (ADR-0014), all mm.

    The Well is a ``ring``-thick ring of Deck walls around a rectangular
    ``cutout``, descending from the Deck's top face to ``plate_top``; the plate
    is a flat sheet one wall wider than the Cutout on every side, so it bears
    on the ring's lower faces from below. Both sizes are derived from the real
    keycap footprint and the wobble allowance -- never chosen.

    ``front_lip``/``rear_lip`` are the solid Deck material outboard of the ring
    (front wall inner face -> ring, and ring -> rear wall inner face); the
    plate's M2 insert bosses are merged to the ring's outer face there, so each
    lip must host one (``boss_lip_required``).

    ``seam`` is the plate's split Seam (the row-jogging path between key
    columns). It rides on the Well because the Well sizes the plate: the Deck's
    insert bosses and the plate's ears are one pattern, so both must read the
    same path from one place.
    """

    keycap_width: float
    keycap_depth: float
    tallest_keycap: float
    wobble: float
    cutout_width: float
    cutout_depth: float
    plate_width: float
    plate_depth: float
    plate_thickness: float
    plate_bottom: float
    plate_top: float
    well_depth: float
    ring: float
    front_lip: float
    rear_lip: float
    boss_lip_required: float
    #: The plate's split Seam (a ``RowSeam``-like path), if the keyboard
    #: component supplied one. The Well is the single source the Deck's bosses
    #: and the plate's ears both derive their stations from.
    seam: Any = None
    #: The Well Cutout's stepped outline (plate-local mm) when the keyboard
    #: could supply one; the Deck opens the Well to this instead of a rectangle.
    cutout_outline: tuple[tuple[float, float], ...] = ()
    #: The plate's plain stepped outline (plate-local mm, no ears/notches), the
    #: shape the Well ring is grown from.
    plate_outline: tuple[tuple[float, float], ...] = ()
    #: The plate's row bands ``(y0, y1, x0, x1)`` (plate-local mm), one per key
    #: row, so each band's lip can be derived from its own extents.
    plate_bands: tuple[tuple[float, float, float, float], ...] = ()

    @property
    def cutout(self) -> tuple[float, float]:
        """The Well Cutout ``(width, depth)`` — keycap + wobble per side."""
        return (self.cutout_width, self.cutout_depth)

    @property
    def plate(self) -> tuple[float, float]:
        """The plate ``(width, depth)`` — Cutout + one wall per side."""
        return (self.plate_width, self.plate_depth)

    @property
    def front_lip_slack(self) -> float:
        """Material left in the front lip beyond what an M2 boss needs (mm)."""
        return self.front_lip - self.boss_lip_required

    def plate_frame(self, placement):
        """The plate's frame in the chassis plan, from the keyboard's placement.

        The Well sizes the plate; the layout places it (rotated, so the
        spacebar faces the user). This is the one call that joins the two, so
        the Deck's bosses and the plate's ears cannot end up in different
        frames (issue #19).
        """
        from geometry.well_mounts import PlateFrame

        return PlateFrame.from_placement(
            placement,
            width=self.plate_width,
            depth=self.plate_depth,
        )

    def seam_in(self, frame):
        """The split Seam converted into the chassis plan through ``frame``.

        ``seam`` is plate-local (the keyboard model's frame), so the world Seam
        is derived here once, with the same frame the mounts use.
        """
        from geometry.well_mounts import SeamPath

        if self.seam is None:
            return None
        return SeamPath.from_seam(self.seam, self.plate_depth).to_world(frame)

    def summary(self) -> str:
        return (
            f"cutout {self.cutout_width:.2f} x {self.cutout_depth:.2f}, "
            f"plate {self.plate_width:.2f} x {self.plate_depth:.2f} x "
            f"{self.plate_thickness:.1f} at z {self.plate_bottom:.2f} "
            f"(top {self.plate_top:.2f}), ring {self.ring:.1f}, "
            f"wobble {self.wobble:.2f}"
        )


@dataclass(frozen=True)
class RodBounds:
    """The three features the guide stance must clear (X, mm).

    ``post`` is the lid's band corner post (the insert plus its boss margin
    outboard of the Rod clamp), ``seat`` the Deck's Bearing-clamp seat against
    the chassis band's corner boss, and ``head`` the moving clamp head under
    the display. The stance is derived from the tightest of them.
    """

    post: float
    seat: float
    head: float

    @property
    def tightest(self) -> float:
        return min(self.post, self.seat, self.head)

    @property
    def tightest_name(self) -> str:
        values = {"post": self.post, "seat": self.seat, "head": self.head}
        return min(values, key=values.get)


@dataclass(frozen=True)
class SlideBudget:
    """Derived slide geometry and the face-height budget (all mm)."""

    travel: float
    keyboard_top: float
    well_front_margin: float
    well: WelledPlate
    rear_band: float
    rear_band_min: float
    rear_band_extension: float
    chassis_height: float
    guide_span: float
    rod_usable: float
    rod_y: float
    rod_clamp_y: tuple[float, float]
    lid_height: float
    closed_face_height: float
    open_face_height: float
    lid_overlap: float
    thickness: float
    width: float
    clamp_width: float
    clamp_body_width: float
    #: The Bearing clamp's screw-pair centre distance across the bore (ADR-0033).
    clamp_span: float
    hardware_width: float
    side_pod: float
    draft_allowance: float
    #: The lid's Y (front/rear) wall draft (degrees): the Tray's base-taper
    #: angle, so the two halves lean at one slope (ADR-0031).
    lid_taper_angle: float
    #: The purchased rod length, or ``None`` for a cut-to-the-budget rod.
    rod_stock: float | None
    usable_half: float
    rod_x: float
    rod_clamp_width: float
    rod_raise: float
    head_crown: float
    display_cavity: float
    #: The lid's back panel thickness and the band's height (mm): with
    #: ``lid_thickness`` they give the height of the lid's drafted walls.
    lid_back: float
    band_height: float
    #: The panel's outline (mm): the content the drafted lid cavity must clear.
    display_width: float
    display_height: float
    lid_thickness: float
    rod_x_bounds: RodBounds
    guard_planform: tuple[float, float, float, float]
    fpc_guard: Any
    lid_joint: Any
    chassis_top: float
    chassis_joint: Any
    base_taper: Any
    bearing_model: str
    bearing_length: float
    bearing_per_rod: int
    rod_clamp_length: float
    bearing_clamp_length: float
    slot_span: float
    slot_needed: float
    clamp_center_y: float
    face_height_limit: float
    chain_bend_radius: float
    cable_min_bend_radius: float

    @property
    def within_face_limit(self) -> bool:
        """The closed face height is a HARD limit."""
        return self.closed_face_height <= self.face_height_limit + 1e-9

    @property
    def plate_z(self) -> float:
        """The plate's bottom face (ADR-0014): the Deck's Well reaches it."""
        return self.well.plate_bottom

    @property
    def parting_below_plate(self) -> bool:
        """``parting_z <= plate_bottom`` is HARD: the Parting never cuts the Well."""
        return self.chassis_joint.parting_z <= self.well.plate_bottom + 1e-9

    @property
    def front_lip_hosts_boss(self) -> bool:
        """The front lip must hold the plate's M2 insert boss (ADR-0014)."""
        return self.well.front_lip_slack >= -1e-9

    @property
    def slot_fits(self) -> bool:
        """The back-panel slot must contain the Bearing clamp at both poses."""
        return self.slot_span >= self.slot_needed - 1e-9

    @property
    def face_flush(self) -> bool:
        """The closed lid and the chassis share the same face depth (mm)."""
        return abs(self.lid_height - self.chassis_height) <= 1e-9

    @property
    def lid_face_taper_height(self) -> float:
        """How tall the lid's drafted walls are: band's top to the face's inner face."""
        return self.lid_thickness - self.lid_back - self.band_height

    @property
    def chain_bend_ok(self) -> bool:
        """The drag chain must not bend the cable tighter than its minimum."""
        return self.chain_bend_radius >= self.cable_min_bend_radius

    @property
    def rod_stock_ok(self) -> bool:
        """A stock rod must fit the closed face without being cut (ADR-0031)."""
        if self.rod_stock is None:
            return True
        return self.lid_height <= self.face_height_limit + 1e-9

    def summary(self) -> str:
        """Human-readable budget, printed by the data pipeline."""
        status = "PASS" if self.within_face_limit else "FAIL"
        lines = [
            f"closed face height: {self.closed_face_height:.2f} mm "
            f"(limit {self.face_height_limit:.1f}, {status})",
            f"  travel: {self.travel:.2f} mm "
            f"(keyboard top {self.keyboard_top:.2f} + clearance)",
            f"  well: {self.well.summary()}",
            f"  front margin: {self.well_front_margin:.2f} mm "
            f"(lip {self.well.front_lip:.2f} for a "
            f"{self.well.boss_lip_required:.2f} boss)",
            f"  chassis: {self.chassis_height:.2f} mm "
            f"(rear band {self.rear_band:.2f}, of which "
            f"{self.rear_band_extension:.2f} is the lid-driven extension)",
            f"  guide span: {self.guide_span:.2f} mm "
            f"({self.bearing_per_rod}x {self.bearing_model} "
            f"{self.bearing_length:.1f} mm, usable {self.rod_usable:.2f})",
            f"  rod clamps: {self.rod_clamp_length:.1f} mm each end, "
            f"slot {self.slot_span:.2f} / {self.slot_needed:.2f} mm needed",
            f"  lid: {self.lid_height:.2f} mm, overlap in the open pose "
            f"{self.lid_overlap:.2f} mm, front/rear taper "
            f"{self.lid_taper_angle:.2f} deg (face depth "
            f"{self.lid_height - 2.0 * math.tan(math.radians(self.lid_taper_angle)) * self.lid_face_taper_height:.2f})",
            f"  rod: {self.rod_usable:.2f} mm usable"
            + (
                f", stock {self.rod_stock:.2f} mm (not cut)"
                if self.rod_stock is not None
                else ""
            ),
            f"  chassis joint: {self.chassis_joint.station_count} stations, "
            f"band {self.chassis_joint.band:.1f} mm at z "
            f"{self.chassis_joint.parting_z:.2f}, "
            f"{self.chassis_joint.screw.size}x{self.chassis_joint.screw.length} "
            f"(tightest boss {self.chassis_joint.smallest_boss():.2f} mm)",
            f"open face height: {self.open_face_height:.2f} mm",
            f"thickness: {self.thickness:.2f} mm (lid {self.lid_thickness:.2f}, "
            f"display cavity {self.display_cavity:.2f}), width: {self.width:.2f} mm "
            f"(side pod {self.side_pod:.2f} incl. draft {self.draft_allowance:.2f})",
            f"guides: rod x +/-{self.rod_x:.2f} "
            f"(bounds post {self.rod_x_bounds.post:.2f}, "
            f"seat {self.rod_x_bounds.seat:.2f}, head {self.rod_x_bounds.head:.2f}), "
            f"FPC guard {self.fpc_guard.total:.2f} mm over x "
            f"{self.guard_planform[0]:.2f}..{self.guard_planform[2]:.2f}, "
            f"y +/-{self.guard_planform[3]:.2f}",
            f"drag chain: bend radius {self.chain_bend_radius:.1f} mm "
            f"(cable minimum {self.cable_min_bend_radius:.1f})",
        ]
        return "\n".join(lines)


def _size(components: dict[str, Any], role: str) -> Any:
    component = components.get(role)
    if component is None:
        raise ValueError(f"slide budget needs the {role!r} component")
    return component.size()


def _plate_seam(keyboard_component: Any) -> Any:
    """The plate's split Seam, if the keyboard component can supply it.

    The keyboard assembly exposes its plate model (``plate_model()``), which is
    pure data; a component without one simply carries no Seam and the Well
    leaves it ``None``.
    """
    plate_model = getattr(keyboard_component, "plate_model", None)
    if plate_model is None:
        return None
    return getattr(plate_model(), "seam", None)


def _plate_outlines(
    keyboard_component: Any,
) -> tuple[tuple, tuple, tuple]:
    """The plate's stepped outlines and row bands, if it can supply them.

    Returns ``(cutout_outline, plate_outline, plate_bands)``: the keyboard
    adapter's :meth:`~components.keyboard_plate.KeyboardPlate.cutout_outline`
    and :meth:`~components.keyboard_plate.KeyboardPlate.plate_base_outline`
    polygons plus its per-row bands. A component that predates the stepped
    outline returns three empty tuples, and the Well falls back to its
    rectangle.
    """
    cutout = getattr(keyboard_component, "cutout_outline", None)
    plate = getattr(keyboard_component, "plate_base_outline", None)
    bands = getattr(keyboard_component, "plate_bands", None)
    return (
        tuple(cutout()) if callable(cutout) else (),
        tuple(plate()) if callable(plate) else (),
        tuple(bands()) if callable(bands) else (),
    )


def bearing_clamp_screw_span(
    bearing_outer: float,
    insert: str,
    edge_chamfer: float,
    minimum_feature: float,
) -> float:
    """The clamp's screw-pair centre distance across the bore (mm, ADR-0033).

    Each screw sits beside the bearing at ``x = +/-span/2``.  The heat-set
    insert's printed hole must clear the bore's *chamfered* split edge by one
    printable minimum, so the span is the closed-form sum below -- derived, so
    a wider insert, a bigger break or a finicky material all move it together.
    """
    bore_radius = (bearing_outer + _BEARING_BORE_CLEARANCE) / 2.0
    spec = fasteners.heat_insert(insert)
    return 2.0 * (
        bore_radius + edge_chamfer + minimum_feature + spec.printed_hole_diameter / 2.0
    )


def bearing_clamp_width(span: float, insert: str, minimum_feature: float) -> float:
    """The clamp body's width across the bore for ``span`` (mm, ADR-0033).

    The insert's ring is **two** printable minimums wide: it now carries the
    joint's whole preload through its seat, so it gets twice the minimum wall
    rather than the bare one.
    """
    spec = fasteners.heat_insert(insert)
    return span + 2.0 * (spec.outside_diameter / 2.0 + 2.0 * minimum_feature)


def compute_slide_budget(config: Any, components: dict[str, Any]) -> SlideBudget:
    """Derive the travel, guide span and envelope from config + components.

    The formulas are the spec's face-height budget (ADR-0009/0010/0013) and the
    Well's sizing chain (ADR-0014):

    * the **Cutout** is the keycap footprint plus the wobble allowance per
      side; the **plate** is the Cutout plus one wall per side, so it bears on
      the Well walls' lower faces.
    * ``plate_z = chassis_top - tallest_keycap - CAP_PLATE_GAP -
      plate_thickness``: the plate sits one cap stack below the Deck's top, so
      the Well is exactly as deep as the keycaps need. ``parting_z`` must stay
      below it (HARD).
    * the **front margin** is the face-height budget's remainder:
      ``face_height_limit - lid stack - plate.depth``, floored by the front lip
      that has to host the plate's M2 insert boss (ADR-0014).
    * ``travel = well_front_margin + plate.depth + travel_clearance`` (the
      lid's lower edge must pass the keyboard's *upper* edge).
    * the Bearing clamp's seat sits at the rear end of the bearing's travel
      envelope; the rear band is the larger of that run and the SBC depth.
    * ``rod_usable = travel + bearings + 2 * (Rod clamp + clearance)``: the
      bearing must not run under the end clamps at either pose.
    * ``guide_span = rod_usable + 2 * end supports``; the lid is the guide
      span plus its top bezel.
    * the lid's guide span is fixed by the mechanism and is the larger half,
      so the chassis grows to the lid's closed face: the two halves are flush
      at the rear and the lid never overhangs the chassis.
    """
    slide = config.slide
    bearing = slide.bearing
    rod = slide.rod
    wall = config.wall_thickness
    shell = config.clearance.shell

    keyboard_component = components.get("keyboard")
    if keyboard_component is None:
        raise ValueError("slide budget needs the 'keyboard' component")
    keyboard = keyboard_component.size()
    display = _size(components, "display")
    # Required: the FPC guard's planform is anchored to its FPC connector.
    _size(components, "driver")
    sbc = _size(components, "sbc")
    controller = _size(components, "controller")

    # -- The Well's Cutout and the plate (ADR-0014) -----------------------
    # The Cutout is the real keycap footprint plus the wobble allowance; the
    # plate is one wall wider on each side so it reaches under the Well walls
    # and bears on their lower faces.
    keycap_width, keycap_depth, tallest_keycap = keyboard_component.keycap_envelope()
    wobble = config.keyboard.plate_wobble
    cutout_width = keycap_width + 2.0 * wobble
    cutout_depth = keycap_depth + 2.0 * wobble
    plate_width = cutout_width + 2.0 * wall
    plate_depth = cutout_depth + 2.0 * wall
    plate_thickness = config.keyboard.plate_thickness

    # The chassis' Z stack: the keyboard is the tallest content unless a buried
    # part is. The Deck's top is the keycap stack above the plate.
    chassis_thickness = max(
        keyboard.height,
        wall + sbc.height,
        wall + controller.height,
    )
    # Slaved to the tallest keycap: the Well always reaches the plate's top.
    plate_z = (
        chassis_thickness - tallest_keycap - CAP_PLATE_GAP - plate_thickness
    )

    bearing_stack = (
        bearing.per_rod * bearing.length
        + (bearing.per_rod - 1) * slide.clamp_wall
    )
    # The rod must be long enough for the bearing's full travel envelope plus
    # a Rod clamp and a clearance gap at each end.
    rod_clamp_allowance = slide.rod_clamp.length + slide.rod_clamp.clearance

    # -- The face-height budget derives the front margin (ADR-0014) -------
    # Everything between the keyboard's top and the closed face: the travel's
    # clearance, the bearing, the two Rod clamps and their gaps, the lid's end
    # supports and its top bezel. The margin is what the HARD limit leaves
    # after the plate.
    lid_stack = (
        slide.travel_clearance
        + bearing_stack
        + 2.0 * rod_clamp_allowance
        + 2.0 * rod.end_support
        + slide.top_bezel
    )
    # The floor: the front lip is the Deck material between the front wall's
    # inner face and the Well ring. An M2 insert boss merged to the ring's
    # outer face needs the bore's merged-boss margin, the insert hole and the
    # boss margin around it.
    plate_screw = fasteners.heat_insert(
        str((config.keyboard.mounting or {}).get("screw", "M2"))
    )
    boss_widen = float(
        (config.keyboard.mounting or {}).get("boss_widen", 1.0)
    )
    boss_lip_required = (
        config.merged_boss.bore_margin
        + plate_screw.printed_hole_diameter
        + config.chassis_joint.boss_margin
        + boss_widen / 2.0
    )
    front_margin_floor = wall + boss_lip_required
    # The face-height limit is derived from the content, not configured: a
    # deeper plate needs a longer face, and the configured 140 mm is a FLOOR
    # (the product target for a 40% board), not a ceiling. The margin is the
    # floor the front lip needs; anything the configured limit left over and
    # above that is dead space in front of the keyboard, so the limit is the
    # floor plus the lid stack plus the plate -- which is exactly the closed
    # face the content requires. A 40% board's content lands on 140.00, so the
    # shipped face is unchanged; a 60% board's deeper plate grows it.
    face_height_limit = max(
        slide.face_height_limit,
        front_margin_floor + lid_stack + plate_depth,
    )
    well_front_margin = face_height_limit - lid_stack - plate_depth
    keyboard_top = well_front_margin + plate_depth
    travel = keyboard_top + slide.travel_clearance

    rod_usable = travel + bearing_stack + 2.0 * rod_clamp_allowance
    rear_band_clamp = slide.rear_band_clamp
    rear_band_contents = sbc.depth + 2 * shell
    rear_band_min = max(rear_band_clamp, rear_band_contents)
    chassis_height_min = keyboard_top + rear_band_min + wall

    # The guide span: what the lid has to carry. The hardware (travel, bearing,
    # rod clamps and their gaps) sets the **minimum**; a stock rod (ADR-0031)
    # may be longer, and the extra length becomes the lid material beyond each
    # clamp, exactly as without one. A stock rod is never cut, so the lid is
    # as long as the rod plus `top_bezel` -- and `slide-stock-rod` (HARD) fails
    # when that is longer than the 140 mm face allows.
    guide_min = rod_usable + 2.0 * rod.end_support
    stock = rod.stock_length
    if stock is not None:
        stock_span = stock + 2.0 * rod.end_support
        guide_span = max(guide_min, stock_span)
        lid_height = guide_span + slide.top_bezel
    else:
        guide_span = guide_min
        lid_height = guide_span + slide.top_bezel
    # The lid is the larger half: its guide span is fixed by the purchased
    # bearing and the end clamps, so the chassis grows to meet it instead of
    # the lid overhanging the chassis at the rear. The lid defines the
    # footprint; the chassis rear wall must end flush with it.
    closed_face = max(chassis_height_min, lid_height)
    chassis_height = closed_face
    rear_band = chassis_height - keyboard_top - wall
    rear_band_extension = max(0.0, chassis_height - chassis_height_min)
    open_face = max(chassis_height, lid_height + travel)
    # How much of the lid still overlaps the chassis (and so its clamp) when
    # open: the lid's own overhang and the top bezel must not inflate it.
    lid_overlap = min(lid_height, chassis_height) - travel

    # -- The Well and the plate, sized from the numbers above --------------
    cutout_outline, plate_outline, plate_bands = _plate_outlines(
        keyboard_component
    )
    well = WelledPlate(
        keycap_width=keycap_width,
        keycap_depth=keycap_depth,
        tallest_keycap=tallest_keycap,
        wobble=wobble,
        cutout_width=cutout_width,
        cutout_depth=cutout_depth,
        plate_width=plate_width,
        plate_depth=plate_depth,
        plate_thickness=plate_thickness,
        plate_bottom=plate_z,
        plate_top=plate_z + plate_thickness,
        well_depth=chassis_thickness - (plate_z + plate_thickness),
        ring=wall,
        front_lip=well_front_margin - wall,
        rear_lip=rear_band,
        boss_lip_required=boss_lip_required,
        # The plate's Seam rides on the Well: the Deck's insert bosses and the
        # plate's ears are one pattern (the face-height budget above already
        # read the keyboard component, so the path costs nothing extra here).
        seam=_plate_seam(keyboard_component),
        cutout_outline=cutout_outline,
        plate_outline=plate_outline,
        plate_bands=plate_bands,
    )

    # -- The moving head has to pass under the display --------------------
    # The rod sits half-sunk in the back panel: its lowest point is the panel's
    # mid-thickness, so the inverted tray's cavity above it stays as deep as
    # possible. Derived, never tuned.
    rod_raise = rod.diameter / 2.0 - slide.lid_back / 2.0
    if rod_raise <= 0.0:
        raise ValueError(
            "slide.lid_back is too thick for the guide rod: it would swallow the "
            f"rod (lid_back {slide.lid_back} > rod diameter {rod.diameter})"
        )

    # The clamp carries one screw each side of the bearing (ADR-0033).  The span
    # and the body width are a closed-form derivation from the bore, the split
    # chamfer, the printable minimum and the heat-set insert -- never tuned: the
    # insert must keep a wall to the bore's chamfered edge and to the clamp's
    # outer face.
    clamp_span = bearing_clamp_screw_span(
        bearing.outer_diameter,
        slide.bearing_clamp.insert,
        slide.bearing_clamp.edge_chamfer,
        config.material.minimum_feature,
    )
    clamp_width = bearing_clamp_width(
        clamp_span, slide.bearing_clamp.insert, config.material.minimum_feature
    )
    clamp_body_width = clamp_width
    hardware_width = clamp_width + 2.0 * slide.slot_clearance
    # The moving clamp's budgeted crown keeps the old 2.0 mm wall: the printed
    # clamp is lower (its `crown_wall` is 1.5), but shrinking the display
    # cavity would narrow the case through the lid draft and perturb the Well
    # mounts.  The extra clearance is spare, not a collision.
    head_crown = rod_raise + bearing.outer_diameter / 2.0 + slide.clamp_wall
    guard = slide.fpc_guard
    # The display's back must clear the head's crown by the component gap and
    # the documented sag allowance, plus the guard plate bonded to it.
    display_cavity = (
        head_crown + slide.component_gap + guard.sag_allowance + guard.total
    )
    lid_thickness = (
        slide.lid_back
        + display_cavity
        + display.height
        + slide.lid_front
        + shell
        - config.bezel.recess
    )
    thickness = chassis_thickness + slide.lid_clearance + lid_thickness

    # -- Width: the content plus the lid's drafted side wall (ADR-0031) ----
    # The guide hardware is inboard now, so nothing but the content sets the
    # width. The lid's X walls lean with its Y walls (one slope, ADR-0031), so
    # the side pod is the wall, the shell clearance and the draft inset over
    # the display's height. The keyboard plate bears on the Well ring and is
    # sized there (ADR-0014): beside it the pod's draft allowance is spare, so
    # the plate's half-width plus the wall is the narrower of the two bounds.
    display_top = display_cavity + display.height
    cavity_z1 = lid_thickness - slide.lid_front  # the front panel's inner face
    taper_height = max(0.0, min(display_top, cavity_z1) - slide.joint.band)
    draft_allowance = math.tan(math.radians(config.draft.lid)) * taper_height
    side_pod = wall + shell + draft_allowance
    content_width = max(plate_width, display.width)
    width = content_width + 2 * side_pod
    # The Tray <-> Deck band joint (ADR-0012): the Parting plane and the ten
    # fastener stations, sized from the chassis plan at that plane.
    chassis_band = chassis_band_joint(
        width=width,
        depth=chassis_height,
        chassis_top=chassis_thickness,
        content_y1=-chassis_height / 2.0 + keyboard_top,
        minimum_feature=config.material.minimum_feature,
        chamfer=config.corners.chamfer,
        wall=wall,
        parting=config.parting,
        joint=config.chassis_joint,
        head_fit=config.clearance.head,
    )
    # `parting_z <= plate_bottom` is HARD (ADR-0014): the Tray/Deck Parting
    # must never cut through the Well, or the plate's bearing ring is split.
    if chassis_band.parting_z > plate_z + 1e-9:
        raise ValueError(
            "the chassis Parting plane cuts the keyboard Well: parting_z "
            f"{chassis_band.parting_z:.2f} > plate_bottom {plate_z:.2f} "
            "(ADR-0014 requires the Parting below the plate)"
        )
    # The base taper on the Tray's vertical end walls (ADR-0019): sized from
    # the band joint's head recesses, which it has to step around.
    taper = base_taper(config, chassis_band)
    # `usable_half` is the inner wall at the content's plane: what the layout
    # may fill before the shell clearance runs out. The plate is sized from the
    # Cutout and the mounts (ADR-0014), not from this bound.
    usable_half = width / 2.0 - side_pod

    # -- Guide stance: bounded by the three features it must clear --------
    insert_hole = fasteners.heat_insert(slide.joint.screw).printed_hole_diameter
    post_bound = (
        width / 2.0
        - wall
        - slide.joint.corner_clearance
        - slide.rod_clamp.width / 2.0
        - (insert_hole + 2.0 * slide.joint.boss_margin)
    )
    seat_half = (
        clamp_width / 2.0
        + slide.bearing_clamp.seat_fit
        + slide.bearing_clamp.seat_wall
    )
    seat_bound = (
        width / 2.0
        - config.chassis_joint.station_inset
        - config.chassis_joint.boss / 2.0
        - config.material.minimum_feature
        - seat_half
    )
    head_bound = display.width / 2.0 - clamp_width / 2.0
    rod_bounds = RodBounds(post=post_bound, seat=seat_bound, head=head_bound)
    rod_x = rod_bounds.tightest - rod.side_margin

    joint = lid_joint(
        width=width,
        lid_height=lid_height,
        lid_back=slide.lid_back,
        rod_x=rod_x,
        rod_clamp_width=slide.rod_clamp.width,
        joint=slide.joint,
        wall=wall,
        chamfer=config.corners.chamfer,
        minimum_feature=config.material.minimum_feature,
        head_fit=config.clearance.head,
    )

    rod_clamp_length = slide.rod_clamp.length
    bearing_clamp_length = slide.bearing_clamp.length
    # The rod is inset by one end support from the chassis front, so the lid's
    # end wall stays solid; both Rod clamps sit at its ends.
    rod_y = -chassis_height / 2.0 + rod.end_support + rod_usable / 2.0
    rod_clamp_y = (
        rod_y - rod_usable / 2.0 + rod_clamp_length / 2.0,
        rod_y + rod_usable / 2.0 - rod_clamp_length / 2.0,
    )
    slot_span = rod_usable - 2.0 * rod_clamp_length
    slot_needed = travel + bearing_clamp_length + 2.0 * slide.slot_clearance
    # The Bearing clamp's seat sits at the middle of its travel envelope.
    clamp_center_y = rod_y + travel / 2.0

    # -- The FPC guard's planform, in the display's own frame -------------
    # Bonded to the display's back: it starts at the driver's FPC connector
    # (the ribbon enters there) and spans the head's sweeps with margin, over
    # the ribbon's full width. It stays inside the lid's drafted wall (the
    # case's inner face), NOT the display's shadow: a board wider than the
    # display pushes the rod stance past the display's edge, and the guard is
    # a separate printed part bonded to the display's back, so it may overhang
    # the shadow as long as it never pierces the shell. The lid's inner face
    # is the binding bound; the display's shadow is a soft preference.
    flex = config.display.flex
    ribbon_half = flex.width / 2.0 if flex is not None else 0.0
    driver_component = components["driver"]
    guard_x0 = (
        driver_component.offset_x
        + driver_component.width / 2.0
        + guard.fit
    )
    guard_x1 = min(
        usable_half,
        rod_x + hardware_width / 2.0 + guard.margin,
    )
    guard_planform = (
        guard_x0,
        -(ribbon_half + guard.margin),
        guard_x1,
        ribbon_half + guard.margin,
    )

    return SlideBudget(
        travel=travel,
        keyboard_top=keyboard_top,
        well_front_margin=well_front_margin,
        well=well,
        rear_band=rear_band,
        rear_band_min=rear_band_min,
        rear_band_extension=rear_band_extension,
        chassis_height=chassis_height,
        guide_span=guide_span,
        rod_usable=rod_usable,
        rod_y=rod_y,
        rod_clamp_y=rod_clamp_y,
        lid_height=lid_height,
        closed_face_height=closed_face,
        open_face_height=open_face,
        lid_overlap=lid_overlap,
        thickness=thickness,
        width=width,
        clamp_width=clamp_width,
        clamp_body_width=clamp_body_width,
        clamp_span=clamp_span,
        hardware_width=hardware_width,
        side_pod=side_pod,
        draft_allowance=draft_allowance,
        lid_taper_angle=base_taper_angle(config, chassis_thickness),
        rod_stock=rod.stock_length,
        usable_half=usable_half,
        rod_x=rod_x,
        rod_clamp_width=slide.rod_clamp.width,
        rod_raise=rod_raise,
        head_crown=head_crown,
        display_cavity=display_cavity,
        lid_back=slide.lid_back,
        band_height=joint.band,
        display_width=display.width,
        display_height=display.height,
        lid_thickness=lid_thickness,
        rod_x_bounds=rod_bounds,
        guard_planform=guard_planform,
        fpc_guard=guard,
        lid_joint=joint,
        chassis_top=chassis_thickness,
        chassis_joint=chassis_band,
        base_taper=taper,
        bearing_model=bearing.model,
        bearing_length=bearing.length,
        bearing_per_rod=bearing.per_rod,
        rod_clamp_length=rod_clamp_length,
        bearing_clamp_length=bearing_clamp_length,
        slot_span=slot_span,
        slot_needed=slot_needed,
        clamp_center_y=clamp_center_y,
        face_height_limit=face_height_limit,
        chain_bend_radius=slide.chain.bend_radius,
        cable_min_bend_radius=MIN_BEND_RADIUS_MM[CONNECTOR_HDMI],
    )


def build_guide_rod(diameter: float, length: float):
    """A steel guide rod as a cylinder along Y, centered on the origin."""
    from utilities import cad_helpers as ch

    ch.require_cad()
    return ch.rotate_x(ch.cylinder_centered(diameter, length), 90.0)


def build_linear_bearing(outer_diameter: float, bore: float, length: float):
    """An LM...LUU bushing as a hollow cylinder along Y, centered on the origin."""
    from utilities import cad_helpers as ch

    ch.require_cad()
    outer = build_guide_rod(outer_diameter, length)
    hole = ch.rotate_x(ch.cylinder_centered(bore, length + 2.0), 90.0)
    return ch.cut(outer, hole)


def build_rod_clamp(
    rod_diameter: float,
    rod_raise: float,
    length: float,
    height: float,
    width: float,
    screw: str,
    screw_span: float,
    set_screw: str,
    bottom_edge_chamfer: float = 1.0,
    general_chamfer: float = 0.5,
    top_edge_chamfer: float = 1.0,
):
    """A printed clamp holding one rod end to the lid back panel.

    Local origin: the back panel's inner face, centred on the rod. The rod
    passes along Y at ``z = rod_raise``; the clamp's two screws drop through it
    into heat-set inserts in the panel, and a set screw from the top locks the
    rod axially.

    Edge treatment (chamfers) is applied to convex edges after all cuts:
    - ``bottom_edge_chamfer``: the two sharp bottom edges where the rod bore
      meets the bottom face (Z=0)
    - ``general_chamfer``: all other convex edges, including circular edges
      around the bore at various heights
    - ``top_edge_chamfer``: the front/back top edges (along Y at Z=height)
    - Screw holes (mounting clearance holes, counterbores, set screw hole) are
      excluded from all chamfers.
    """
    from utilities import cad_helpers as ch
    from utilities.fasteners import head as head_spec
    from utilities.fasteners import screw as screw_spec

    ch.require_cad()
    spec = screw_spec(screw)
    spec_head = head_spec(screw, "cap")
    set_spec = screw_spec(set_screw)
    block = ch.box_centered(width, length, height)
    block = ch.translate(block, 0.0, 0.0, height / 2.0)
    bore = ch.rotate_x(
        ch.cylinder_centered(rod_diameter + 0.2, length + 2.0), 90.0
    )
    bore = ch.translate(bore, 0.0, 0.0, rod_raise)
    part = ch.cut(block, bore)
    for side in (-1, 1):
        x = side * screw_span / 2.0
        hole = ch.translate(
            ch.cylinder_centered(spec.clearance, height + 2.0), x, 0.0, height / 2.0
        )
        head = ch.translate(
            ch.cylinder_centered(spec_head.diameter, spec_head.depth),
            x,
            0.0,
            height - spec_head.depth / 2.0,
        )
        part = ch.cut(part, hole, head)
    rod_top = rod_raise + rod_diameter / 2.0
    set_hole = ch.translate(
        ch.cylinder_centered(set_spec.pilot_hole, height - rod_top),
        0.0,
        0.0,
        (height + rod_top) / 2.0,
    )
    part = ch.cut(part, set_hole)

    # Edge treatment: chamfer convex edges selectively. All three groups are
    # classified from the *same* solid and chamfered in one pass: treating them
    # one size after the other leaves the next group's edge keys stale (a
    # treated neighbour shortens them), and a stale key is silently not found.
    if bottom_edge_chamfer > 0.0 or general_chamfer > 0.0 or top_edge_chamfer > 0.0:
        all_convex = ch.convex_edges(part)

        # Screw hole regions to exclude from chamfering
        screw_x_positions = [screw_span / 2.0, -screw_span / 2.0]
        set_screw_x = 0.0
        # Tolerance around screw holes: cover the counterbore radius (largest diameter)
        # Counterbore radius = spec_head.diameter / 2, add small margin
        screw_x_tolerance = spec_head.diameter / 2.0 + 0.5
        # Set screw hole: pilot hole radius + small margin
        set_screw_x_tolerance = set_spec.clearance / 2.0 + 0.5

        # The bore's two straight bottom edges sit at X = +/-sqrt(r^2 - raise^2),
        # where r is the bore radius; match them exactly so a chamfered
        # neighbour's new bevel edge is never mistaken for one.
        bore_radius = rod_diameter / 2.0 + 0.1
        bore_bottom_x = math.sqrt(max(bore_radius**2 - rod_raise**2, 0.0))
        half_length = length / 2.0

        pairs = []
        for edge in all_convex:
            x, y, z = edge.midpoint

            # Skip edges belonging to mounting screw holes (clearance + counterbore)
            # Screw holes are at X=±screw_span/2, Y=0. Only exclude edges near both X and Y.
            if any(abs(x - sx) < screw_x_tolerance and abs(y) < screw_x_tolerance for sx in screw_x_positions):
                continue
            # Skip edges belonging to set screw hole (at X=0, Y=0)
            if abs(x - set_screw_x) < set_screw_x_tolerance and abs(y) < set_screw_x_tolerance:
                continue

            if (
                bottom_edge_chamfer > 0.0
                and abs(z) < 0.1
                and edge.curve_type == "line"
                and abs(abs(x) - bore_bottom_x) < 0.15
            ):
                # The two sharp edges where the rod bore cuts the bottom face.
                pairs.append((edge, bottom_edge_chamfer))
            elif (
                top_edge_chamfer > 0.0
                and abs(z - height) < 0.1
                and edge.curve_type == "line"
                and abs(abs(y) - half_length) < 0.15
            ):
                # The front/back top edges (Y = +/-length/2), running along X.
                pairs.append((edge, top_edge_chamfer))
            elif general_chamfer > 0.0:
                pairs.append((edge, general_chamfer))

        if pairs:
            part = ch.chamfer_edges_variable(part, pairs)

    return ch.clean(part)


def _bearing_clamp_edge_pairs(
    half,
    split_z: float,
    bed_z: float,
    bed_normal: tuple[float, float, float],
    length: float,
    edge_chamfer: float,
    bed_chamfer: float,
) -> list[tuple[Any, float]]:
    """The chamfer pairs for one clamp half: the print-layer edges (mm).

    Three families, all applied in one variable pass so OCC can build the
    corner blends where they meet:

    * the **split line** -- every straight edge on the split plane (the outer
      perimeter and the bore's two long edges).  Breaking it turns the joint
      into a deliberate V-groove instead of a hairline;
    * the **bore's end rims** -- the half-circle arcs on the two end faces, so
      the bearing drops into the bore instead of catching the print's top
      edge;
    * the **bed perimeter** -- the first-layer edge of the foot's bottom (lower
      half) or the crown's top (upper half).
    """
    from utilities import cad_helpers as ch

    pairs: list[tuple[Any, float]] = []
    if edge_chamfer > 0.0:
        for edge in ch.convex_edges(half):
            if abs(edge.midpoint[2] - split_z) < 1e-4 and edge.curve_type == "line":
                pairs.append((edge, edge_chamfer))
            elif (
                edge.curve_type == "circle"
                and abs(abs(edge.midpoint[1]) - length / 2.0) < 1e-4
            ):
                pairs.append((edge, edge_chamfer))
    if bed_chamfer > 0.0:
        for edge in ch.bed_boundary_edges(half, bed_normal):
            pairs.append((edge, bed_chamfer))
    return pairs


def build_bearing_clamp_halves(
    bearing_outer: float,
    clamp_width: float,
    rod_raise: float,
    length: float,
    foot_thickness: float,
    foot_top: float,
    crown_wall: float,
    screw: str,
    insert_name: str,
    screw_span: float,
    screw_length: float,
    seat_floor: float,
    minimum_feature: float,
    edge_chamfer: float = 0.0,
    bed_chamfer: float = 0.0,
    corner_chamfer: float = 0.0,
):
    """The bearing clamp's lower and upper halves, in the assembled frame.

    The clamp is split on the bearing's axis (ADR-0033).  The **lower half**
    runs from the foot's bottom to the axis: it carries the foot and the bore's
    belly, and it prints **foot-down**.  The **upper half** runs from the axis
    to the crown (the bearing's outer top plus ``crown_wall``): it carries the
    bore's roof, and it prints **crown-down**.  Both split faces are flat, so
    the halves meet in one plane and each one prints with its layers parallel to
    that face -- the bore is never a bridge.

    ``screw`` (M3 pan head) does both jobs.  Each screw sits **beside** the
    bearing at ``x = +/-screw_span/2`` and is driven **up from inside the
    chassis**: its head bears on the Deck seat's underside (one ``seat_floor``
    below the foot), its shank passes the seat floor and the lower half with
    clearance, and it threads into a heat-set insert in the upper half.  The
    head stays in the chassis cavity, so no recess is cut and the seat floor
    keeps its whole thickness.  ``screw_length`` is the purchased length and is
    checked against the stack: head -> the insert's seat, and never through the
    crown.

    ``insert_name`` is the heat-set insert (the library's ``M3-long``): it is
    pressed into the upper half from the crown, **flush** with it, and lands on
    a **seat** -- the hole is the insert's diameter down to that plane and only
    the screw's clearance below, so the insert's skirt bears on the step and
    the joint's preload travels in compression into the upper half instead of
    hanging on the knurling.
    """
    from utilities import cad_helpers as ch

    ch.require_cad()
    foot_bottom = foot_top - foot_thickness
    split_z = rod_raise
    lower_h = split_z - foot_bottom
    upper_h = bearing_outer / 2.0 + crown_wall
    crown_z = split_z + upper_h
    # The head's bearing face: the Deck seat's underside, one `seat_floor`
    # below the pocket floor the foot rests on.
    head_z = foot_bottom - seat_floor

    spec = fasteners.screw(screw)
    insert = fasteners.heat_insert(insert_name)
    # The insert is pressed in from the crown, flush with it, and bottoms on
    # the seat: the hole is `insert` wide from the crown down to the seat and
    # only the screw's passage below it.  That step is what carries the joint's
    # preload into the upper half.
    seat_z = crown_z - insert.depth
    tip_z = head_z + screw_length
    engagement = tip_z - seat_z
    if engagement < 0.5 * insert.depth - 1e-9:
        raise ValueError(
            "slide.bearing_clamp.screw_length is too short to engage the "
            f"insert ({screw_length:.2f} mm tip at {tip_z:.2f}, only "
            f"{engagement:.2f} mm above its seat at {seat_z:.2f})"
        )
    if tip_z > crown_z - minimum_feature + 1e-9:
        raise ValueError(
            "slide.bearing_clamp.screw_length breaks through the clamp's "
            f"crown ({screw_length:.2f} mm tip at {tip_z:.2f} > "
            f"{crown_z - minimum_feature:.2f} mm)"
        )

    bore = ch.translate(
        ch.rotate_x(
            ch.cylinder_centered(bearing_outer + _BEARING_BORE_CLEARANCE, length),
            90.0,
        ),
        0.0,
        0.0,
        split_z,
    )

    lower = ch.box_centered(clamp_width, length, lower_h)
    lower = ch.translate(lower, 0.0, 0.0, foot_bottom + lower_h / 2.0)
    if corner_chamfer > 0.0:
        lower = ch.chamfer_vertical_edges(lower, corner_chamfer)
    lower = ch.cut(lower, bore)

    upper = ch.box_centered(clamp_width, length, upper_h)
    upper = ch.translate(upper, 0.0, 0.0, split_z + upper_h / 2.0)
    if corner_chamfer > 0.0:
        upper = ch.chamfer_vertical_edges(upper, corner_chamfer)
    upper = ch.cut(upper, bore)

    for side in (-1.0, 1.0):
        x = side * screw_span / 2.0
        # Clearance through the seat floor is cut by the Deck; through the
        # lower half it is this hole, 2 mm over the full height so the cut
        # breaks through cleanly at both ends.
        through = ch.translate(
            ch.cylinder_centered(spec.clearance, lower_h + 2.0),
            x,
            0.0,
            foot_bottom + lower_h / 2.0,
        )
        lower = ch.cut(lower, through)
        # The insert's hole: `insert` wide from the crown down to the seat (open
        # at the crown, so the insert goes in flush and bottoms on the step).
        insert_hole = ch.translate(
            ch.cylinder_centered(
                insert.printed_hole_diameter, crown_z - seat_z + 2.0
            ),
            x,
            0.0,
            (seat_z + crown_z) / 2.0 + 1.0,
        )
        upper = ch.cut(upper, insert_hole)
        # Below the seat, only the screw's passage -- this is what leaves the
        # insert's skirt a shoulder to bear on.
        passage = ch.translate(
            ch.cylinder_centered(spec.clearance, seat_z - split_z + 1.0),
            x,
            0.0,
            (split_z - 1.0 + seat_z) / 2.0,
        )
        upper = ch.cut(upper, passage)

    # ADR-0033: break the print-layer edges of each half (the split line, the
    # bore's end rims and the bed perimeter) in one pass per half, so the layer
    # seam is a deliberate groove and the bore has a lead-in.
    lower = ch.chamfer_edges_variable(
        lower,
        _bearing_clamp_edge_pairs(
            lower,
            split_z,
            foot_bottom,
            (0.0, 0.0, -1.0),
            length,
            edge_chamfer,
            bed_chamfer,
        ),
    )
    upper = ch.chamfer_edges_variable(
        upper,
        _bearing_clamp_edge_pairs(
            upper,
            split_z,
            crown_z,
            (0.0, 0.0, 1.0),
            length,
            edge_chamfer,
            bed_chamfer,
        ),
    )
    return ch.clean(lower), ch.clean(upper)


def build_bearing_clamp(
    bearing_outer: float,
    clamp_width: float,
    rod_raise: float,
    length: float,
    foot_thickness: float,
    foot_top: float,
    crown_wall: float,
    screw: str,
    insert_name: str,
    screw_span: float,
    screw_length: float,
    seat_floor: float,
    minimum_feature: float,
    edge_chamfer: float = 0.0,
    bed_chamfer: float = 0.0,
    corner_chamfer: float = 0.0,
):
    """The assembled bearing clamp: the two halves as one compound (ADR-0033).

    The halves are built separately by :func:`build_bearing_clamp_halves`; this
    wrapper places them in the assembled frame so the assembly and the exports
    show the clamp as it sits in the case.  Print the halves separately.
    """
    from utilities import cad_helpers as ch

    lower, upper = build_bearing_clamp_halves(
        bearing_outer,
        clamp_width,
        rod_raise,
        length,
        foot_thickness,
        foot_top,
        crown_wall,
        screw,
        insert_name,
        screw_span,
        screw_length,
        seat_floor,
        minimum_feature,
        edge_chamfer,
        bed_chamfer,
        corner_chamfer,
    )
    return ch.make_compound([lower, upper])


__all__ = [
    "SlideBudget",
    "WelledPlate",
    "bearing_clamp_screw_span",
    "bearing_clamp_width",
    "build_bearing_clamp",
    "build_bearing_clamp_halves",
    "build_guide_rod",
    "build_linear_bearing",
    "build_rod_clamp",
    "compute_slide_budget",
]
