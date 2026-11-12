"""40% keyboard assembly: switch plate + keycaps.

The physical keyboard is the Cherry-MX-compatible switch plate driven by a
Waveshare RP2040-Zero running QMK/Vial. Plate geometry comes from the
:mod:`keyboard` package (KLE layout → geometry model); this component is the
cyberdeck adapter that produces the solid.

The controller is **not** part of this component: it is placed separately on
the case floor (``components/rp2040_zero.py``, role ``controller`` in the
layout), because it has to sit under the raised keyboard plate rather
than hang from the tilted plate. See :attr:`switch_bottom_protrusion` for why
it cannot live directly under the plate.

The plate stands on standoffs high enough to keep the switch bodies clear of
whatever is beneath them: the bare floor by default, or a board buried under
the plate (the SBC) when the layout calls :meth:`set_plate_raise` with
:meth:`plate_raise_for_buried`.
"""

from __future__ import annotations

import math
from typing import Any

from components.base import BoundingBox, Component, Hole
from components.keyboard_plate import KeyboardPlate


class Rp2040Keyboard(Component):
    """40% keyboard: switch plate + XDA keycaps.

    Switch housings are not rendered — only the plate cutouts and keycaps
    are visible.  Keycaps are lofted from an 18.5 mm square base to a
    15.0 mm stadium (rounded-rectangle) top, 9.0 mm tall (XDA profile).
    """

    name = "40% Keyboard (RP2040)"

    #: Simplified switch geometry (mm). The body is a cube passing up through
    #: the plate cutout into the keycap, with a pin stub below it. These are
    #: the single source for both :meth:`build` and
    #: :attr:`switch_bottom_protrusion` — they used to be build-local literals
    #: while the property returned a stale, smaller number, which understated
    #: how much room the switches need under the plate by half.
    switch_body_size = 13.0
    switch_pin_diameter = 4.0
    switch_pin_height = 3.5
    #: Cube bottom, measured below the plate's TOP surface.
    switch_cube_bottom_offset = 5.0

    def __init__(self, keyboard: dict[str, Any] | None = None) -> None:
        data = keyboard or {}
        self._plate = KeyboardPlate(data)
        self._switch_family = str(data.get("switch_family", "mx_alps"))
        self._stab_family = str(data.get("stabilizer_family", "cherry"))
        plate_cfg = data.get("plate", {}) or {}
        self._plate_thickness = float(plate_cfg.get("thickness", 1.5))
        self._plate_inset = float(plate_cfg.get("edge_margin", 6.0))
        self._pitch = float(data.get("pitch", 19.05))

        # Default standoff: just enough to keep the switch bodies off the
        # bare floor. The layout raises it further (set_plate_raise) when a
        # board is buried underneath.
        self._floor_gap = float(plate_cfg.get("floor_gap", 1.0))
        self._plate_raise = self.switch_bottom_protrusion + self._floor_gap

        keycap_cfg = data.get("keycap", {}) or {}
        self._keycap_profile = str(keycap_cfg.get("profile", "xda"))
        self._keycap_enabled = bool(keycap_cfg.get("enabled", True))

    def set_plate_raise(self, height: float) -> None:
        """Override the plate standoff height (mm).

        The layout calls this when something buried under the raised plate
        needs more clearance than the switch bodies alone.
        """
        self._plate_raise = height

    def plate_raise_for_buried(
        self,
        part_height: float,
        gap: float,
    ) -> float:
        """Plate standoff (mm) needed to bury a floor-mounted part under the plate.

        The plate is flat, so the only requirement is the buried part's top
        plus the required gap under the switch bodies. Note this is clearance
        under the **switch bodies**, which hang
        :attr:`switch_bottom_protrusion` below the plate: that protrusion,
        not the plate itself, is what the buried part actually has to miss.

        Parameters
        ----------
        part_height : float
            Top of the buried part above the case floor (mm) — including any
            standoff/boss raise, not just the part's own thickness.
        gap : float
            Required clearance between the part's top and the switch bodies.

        Returns
        -------
        float
            The standoff height, never less than the plain
            switch-clearance-plus-floor-gap value.
        """
        needed = part_height + gap
        return max(
            self.switch_bottom_protrusion + self._floor_gap,
            self.switch_bottom_protrusion + needed,
        )

    @property
    def switch_bottom_protrusion(self) -> float:
        """Deepest point of the switch bodies below the plate bottom (mm).

        Derived from the same constants :meth:`build` uses: the switch cube
        starts ``switch_cube_bottom_offset`` below the plate top, and the pin
        stub hangs ``switch_pin_height`` below the cube. For the stock 1.5 mm
        plate that is 7.0 mm, which is why nothing (the controller included)
        fits between the plate and the floor.
        """
        cube_bottom = self._plate_thickness - self.switch_cube_bottom_offset
        return -(cube_bottom - self.switch_pin_height)

    @property
    def switch_top_height(self) -> float:
        """Switch tops above the plate's top surface (mm): where keycaps start."""
        from components.keycap_set import CAP_PLATE_GAP
        return CAP_PLATE_GAP

    def size(self) -> BoundingBox:
        box = self._plate.size()
        from components.keycap_set import CAP_PLATE_GAP
        from keyboard.registry import get_keycap
        profile = get_keycap(self._keycap_profile)()
        cap_height = profile.height()
        height = self._plate_raise + self._plate_thickness + CAP_PLATE_GAP + cap_height
        return BoundingBox(box.width, box.depth, height)

    def keycap_envelope(self) -> tuple[float, float, float]:
        """The keycap set's ``(width, depth, tallest)`` footprint (mm, local).

        ADR-0014 sizes the Deck's Well from the real caps, so the Cutout is
        this footprint plus the wobble allowance per side — measured from the
        same geometry the caps are built from, never a pinned number. The
        footprint is the union of each cap's base rectangle (rotated about its
        own centre, as the keys are); ``tallest`` is the profile's cap height,
        which is how far the Well has to descend.
        """
        from keyboard.geometry.keycaps import keycap_specs
        from keyboard.registry import get_keycap

        self._plate._ensure_model()
        layout = self._plate._layout
        specs = keycap_specs(
            list(layout.keys),
            get_keycap(self._keycap_profile)(),
            pitch=self._pitch,
            layout_centroid=layout._centroid(),
        )
        xs: list[float] = []
        ys: list[float] = []
        for (cx, cy), spec in zip(self.switch_grid, specs):
            half_w = float(spec["base_w"]) / 2.0
            half_d = float(spec["base_d"]) / 2.0
            rad = math.radians(float(spec["rotation"]))
            cos_r, sin_r = math.cos(rad), math.sin(rad)
            for dx, dy in (
                (half_w, half_d),
                (-half_w, half_d),
                (-half_w, -half_d),
                (half_w, -half_d),
            ):
                xs.append(cx + dx * cos_r - dy * sin_r)
                ys.append(cy + dx * sin_r + dy * cos_r)
        tallest = max(float(spec["height"]) for spec in specs)
        return (max(xs) - min(xs), max(ys) - min(ys), tallest)

    #: Y-slices the plate's occupied volume is reported in. Collision/
    #: clearance checks widen each sub-volume's Z-span by up to half its own
    #: depth times sin(tilt) to bound a tilted box — one box spanning the
    #: whole plate would report that swing (front-edge low point to
    #: rear-edge high point) at *every* Y, phantom-colliding with something
    #: correctly tucked under the plate's high (rear) end only, nowhere near
    #: the low end. More slices means each one's own depth — and so its own
    #: swing — shrinks toward the true local clearance at that Y.
    _occupied_volume_slices = 8

    def switch_grid_extent(self) -> tuple[float, float, float, float]:
        """Bounding ``(x0, y0, x1, y1)`` of the switch bodies (mm, local).

        The switch cubes are centered on the grid positions, so the occupied
        footprint is the grid extent grown by half a cube on every side. This
        is narrower than the plate: the plate's edge margin carries no
        switches, and that margin is the only place a tall part can sit
        directly under the plate.
        """
        grid = self.switch_grid
        half = self.switch_body_size / 2.0
        xs = [x for x, _ in grid]
        ys = [y for _, y in grid]
        return (min(xs) - half, min(ys) - half, max(xs) + half, max(ys) + half)

    def _sliced(
        self, x0: float, y0: float, x1: float, y1: float, z: float, height: float
    ) -> list[tuple[float, float, float, BoundingBox]]:
        """Slice an axis-aligned block into ``_occupied_volume_slices`` Y-bands."""
        n = self._occupied_volume_slices
        depth = (y1 - y0) / n
        return [
            (
                (x0 + x1) / 2.0,
                y0 + (i + 0.5) * depth,
                z,
                BoundingBox(x1 - x0, depth, height),
            )
            for i in range(n)
        ]

    def occupied_volumes(self) -> list[tuple[float, float, float, BoundingBox]]:
        """Solid sub-volumes: two boxes per switch, plus the plate above them.

        The switch volume is split into the same two bodies :meth:`build`
        actually generates, not one box spanning both: a ``switch_body_size``
        (13 mm) square for the cube, and a narrower ``switch_pin_diameter``
        (4 mm) square for the pin stub below it. An earlier version used the
        cube's wider footprint for the *entire* protrusion height, including
        the lower band where only the narrow pin exists — a real, measured
        source of false-positive collisions: a clearance check compared
        against a real boolean intersection of the built solids (no overlap,
        1.5+ mm to spare) still failed by over a millimetre with the
        single-wide-box model, purely from crediting the pin's own clearance
        to the wider cube footprint it doesn't actually have there.
        Before that, an even coarser version reported one full-width slab
        per Y-slice, as if every switch merged into a continuous wall the
        entire width of the grid — a part sitting in the real gap *between*
        two switch columns still tripped the collision check, because the
        slab covered X positions no switch actually occupies.
        Reporting only the plate, before either of those, hid the switch
        band entirely: a board could be placed straight through the switch
        pins with every clearance check still passing.

        Both remaining sources of conservatism versus a true boolean check
        are inherent to axis-aligned box comparison, not further-fixable
        bugs: a square bounding a round pin/cell reaches slightly past the
        true curved surface, and the per-axis separating-axis test (X, Y, Z
        only) can't find a shorter true diagonal separation the real curved
        surfaces achieve. That residual margin is intentional safety
        margin, not error.

        The plate itself and everything above it (cutouts, keycaps) is
        still sliced along Y (see :attr:`_occupied_volume_slices`) for the
        tilt-swing reasons documented there; individual switch boxes are
        small enough relative to the tilt that one box per switch/segment is
        already an accurate bound without further slicing.

        The space below the switch boxes is hollow, so parts tucked under
        the keyboard clear it — provided they clear both boxes, and clear
        them in X too, which per-switch (rather than per-row-slab) boxes
        correctly allow for between columns.
        """
        plate_box = self._plate.size()
        plate_height = self.size().height - self._plate_raise
        cube_z = self._plate_raise - self.switch_cube_bottom_offset + (
            self._plate_thickness
        )
        cube_height = self.switch_cube_bottom_offset - self._plate_thickness
        pin_z = cube_z - self.switch_pin_height
        switch_boxes = []
        for x, y in self.switch_grid:
            switch_boxes.append(
                (x, y, cube_z, BoundingBox(self.switch_body_size, self.switch_body_size, cube_height))
            )
            switch_boxes.append(
                (x, y, pin_z, BoundingBox(
                    self.switch_pin_diameter, self.switch_pin_diameter, self.switch_pin_height
                ))
            )
        return (
            switch_boxes
            + self._sliced(
                -plate_box.width / 2.0, -plate_box.depth / 2.0,
                plate_box.width / 2.0, plate_box.depth / 2.0,
                self._plate_raise, plate_height,
            )
        )

    def mounting_holes(self) -> list[Hole]:
        # The plate mounts on four standoff bosses (height = plate raise).
        return [
            Hole(h.x, h.y, h.diameter, height=self._plate_raise)
            for h in self._plate.mounting_holes()
        ]

    def mounting_screw(self) -> str:
        """The plate's standoff screw size (from keyboard.mounting.screw)."""
        return self._plate.mounting_screw()

    @property
    def switch_grid(self) -> list[tuple[float, float]]:
        return self._plate.switch_positions

    def plate_model(self):
        """The plate's geometry model (cutouts, outline), for Seam planning."""
        self._plate._ensure_model()
        return self._plate._model

    def build_plate(self):
        """The bare switch plate solid (no switches, keycaps or standoff raise)."""
        return self._plate.build()

    def validate(self) -> tuple[int, list[str]]:
        """Run the keyboard plate geometry validation checks.

        Returns
        -------
        tuple[int, list[str]]
            ``(checks_run, errors)`` — number of checks executed and any error
            messages. An empty ``errors`` list means the plate model is valid.
        """
        return self._plate.validate()

    def build(self):
        """Generate the keyboard solid: raised plate, switch bodies, keycaps.

        The plate sits on standoffs at ``_plate_raise`` with simplified switch
        bodies protruding through the cutouts and keycaps lofted above them.
        """
        from components.keycap_set import KeycapSet
        from utilities import cad_helpers

        cad_helpers.require_cad()

        plate = self._plate.build()

        # Simplified switch body at each grid position (local coords).
        # Cube (13 mm) has its **bottom** 5 mm below the plate top surface,
        # so it passes up through the plate cutout and pokes into the keycap.
        # A 4 mm diameter cylinder pokes 3.5 mm below the cube bottom.
        switch_body_size = self.switch_body_size
        switch_pin_diameter = self.switch_pin_diameter
        switch_pin_height = self.switch_pin_height
        cube_bottom_offset = self.switch_cube_bottom_offset
        cube_center_z = self._plate_thickness - cube_bottom_offset + switch_body_size / 2.0
        pin_center_z = self._plate_thickness - cube_bottom_offset - switch_pin_height / 2.0
        switch_shapes: list[Any] = []
        for x, y in self.switch_grid:
            cube = cad_helpers.box_centered(switch_body_size, switch_body_size, switch_body_size)
            cube = cad_helpers.translate(cube, x, y, cube_center_z)
            switch_shapes.append(cube)
            pin = cad_helpers.cylinder_centered(switch_pin_diameter, switch_pin_height)
            pin = cad_helpers.translate(pin, x, y, pin_center_z)
            switch_shapes.append(pin)
        body = cad_helpers.union(plate, cad_helpers.make_compound(switch_shapes))

        # Raise the plate assembly onto its standoffs.
        body = cad_helpers.translate(body, 0.0, 0.0, self._plate_raise)

        # Keycaps lofted above the plate (compound, fused in one op).
        self._plate._ensure_model()
        keys = list(self._plate._layout.keys)
        centroid = self._plate._layout._centroid()
        caps = KeycapSet(
            self.switch_grid, keys,
            profile_name=self._keycap_profile,
            plate_raise=self._plate_raise,
            plate_thickness=self._plate_thickness,
            pitch=self._pitch,
            layout_centroid=centroid,
            enabled=self._keycap_enabled,
        )
        return cad_helpers.union(body, caps.build())
