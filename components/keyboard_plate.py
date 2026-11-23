"""Keyboard switch plate — cyberdeck adapter for the keyboard geometry model.

This is the cyberdeck-side adapter that converts the pure-data
:class:`~keyboard.metadata.KeyboardGeometryModel` into a solid
via :mod:`utilities.cad_helpers`.

The plate is **derived** from the Well (ADR-0014): the keyboard package sizes
it as the Well Cutout plus one wall thickness of border on each side, so it
bears on the Well walls' lower faces. There is no margin to tune. The enclosure
also injects its Well-mount pattern (:meth:`set_well_mounts`): the plate merges
that pattern's filleted **ears** into its outline, cuts its **notches** out of
it, and drills the eight M2 **clearance holes** through plate and ear. The
keyboard package stays CAD-free and enclosure-free -- it only receives
rectangles.

The plate is independent of the enclosure — it can be cut on FR4 or printed
alone.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from components.base import BoundingBox, Component, Hole
from keyboard import generate, parse_layout
from keyboard.geometry.outline import PlateTab
from keyboard.metadata import MountingHole
from utilities import fasteners


#: Geometry tolerance for the injected-pattern checks (mm).
_EPS = 1e-9


def _rects_overlap(
    a: tuple[float, float, float, float],
    b: tuple[float, float, float, float],
) -> bool:
    """True when two axis-aligned plan rectangles share area (mm)."""
    return (
        a[0] < b[2] - _EPS
        and b[0] < a[2] - _EPS
        and a[1] < b[3] - _EPS
        and b[1] < a[3] - _EPS
    )


def _circle_inside_rect(
    x: float,
    y: float,
    radius: float,
    rect: tuple[float, float, float, float],
    margin: float,
) -> bool:
    """True when the circle lies inside ``rect`` leaving ``margin`` all round."""
    return (
        x - radius - margin >= rect[0] - _EPS
        and x + radius + margin <= rect[2] + _EPS
        and y - radius - margin >= rect[1] - _EPS
        and y + radius + margin <= rect[3] + _EPS
    )


def _circle_hits_rect(
    x: float,
    y: float,
    radius: float,
    rect: tuple[float, float, float, float],
) -> bool:
    """True when the circle shares area with the rectangle."""
    dx = max(rect[0] - x, 0.0, x - rect[2])
    dy = max(rect[1] - y, 0.0, y - rect[3])
    return dx * dx + dy * dy < (radius - _EPS) ** 2


class KeyboardPlate(Component):
    """Cherry-MX switch plate for the 40% layout.

    Reads a KLE layout file, the plate configuration, the Well wall thickness
    and the keycap profile, generates the geometry model, and builds the solid
    via cad_helpers.

    The plate's size, Cutout and switch-free border are derived by
    :func:`keyboard.generate` — ``keyboard.plate.edge_margin`` no longer exists.
    The Well-mount pattern (ears, notches and M2 clearance holes) is injected
    by the constraint system via :meth:`set_well_mounts`; with none injected
    the plate is a bare sheet.
    """

    name = "Keyboard Plate"

    def __init__(
        self,
        keyboard: dict[str, Any] | None = None,
        seam_pin_sites: tuple[float, ...] = (),
        seam_pin: Any = None,
    ) -> None:
        data = keyboard or {}
        self._layout_source = str(data.get("layout_source", ""))
        self._switch_family = str(data.get("switch_family", "mx_alps"))
        self._stab_family = str(data.get("stabilizer_family", "cherry"))
        plate = data.get("plate", {}) or {}
        self._plate_thickness = float(plate.get("thickness", 1.5))
        if "wobble" not in plate:
            raise ValueError(
                "KeyboardPlate needs 'plate.wobble' (ADR-0014): the Well Cutout "
                "is the keycap footprint plus the wobble allowance per side, "
                "and keyboard.plate.wobble is its single source"
            )
        self._wobble = float(plate["wobble"])
        self._corner_radius = float(plate.get("corner_radius", 2.0))
        if "wall_thickness" not in data:
            raise ValueError(
                "KeyboardPlate needs 'wall_thickness' (the Well ring / plate "
                "border per side, config.wall.thickness) to size the plate"
            )
        self._wall = float(data["wall_thickness"])
        self._keycap_profile = str((data.get("keycap", {}) or {}).get("profile", "xda"))
        mounting = data.get("mounting", {}) or {}
        self._screw_size = str(mounting.get("screw", "M2"))
        self._screw_diameter = fasteners.screw(self._screw_size).clearance
        self._pitch = float(data.get("pitch", 19.05))

        self._seam_pin_sites = tuple(seam_pin_sites or ())
        self._seam_pin = seam_pin

        self._model = None
        self._layout = None
        self._mounting_holes: list[MountingHole] = []
        self._well_mounts = None
        self._ears: list[PlateTab] = []
        self._notches: list[tuple[float, float, float, float]] = []

    def _ensure_model(self):
        if self._model is not None:
            return
        if not (self._layout_source and Path(self._layout_source).is_file()):
            raise ValueError(
                f"Keyboard layout file not found: {self._layout_source!r} — "
                "set keyboard.layout_source in the config to a KLE JSON file"
            )
        if self._layout is None:
            with open(self._layout_source, "r", encoding="utf-8") as handle:
                raw = json.load(handle)
            self._layout = parse_layout(raw, self._pitch)
        model = generate(
            self._layout,
            switch_family=self._switch_family,
            stabilizer_family=self._stab_family,
            plate_thickness=self._plate_thickness,
            wall=self._wall,
            keycap_profile=self._keycap_profile,
            wobble=self._wobble,
            corner_radius=self._corner_radius,
            mounting_holes=self._mounting_holes,
            ears=self._ears,
            notches=self._notches,
        )
        self._check_well_mounts(model)
        self._model = model

    def validate(self) -> tuple[int, list[str]]:
        """Run the keyboard geometry validation checks.

        Returns
        -------
        tuple[int, list[str]]
            ``(checks_run, errors)`` — number of checks executed and any error
            messages. An empty ``errors`` list means the plate model is valid.
        """
        from keyboard import validate as validate_keyboard

        self._ensure_model()
        return validate_keyboard(
            self._layout,
            self._model,
            self._switch_family,
            self._stab_family,
        )

    def size(self) -> BoundingBox:
        self._ensure_model()
        m = self._model.metadata
        return BoundingBox(m.width, m.height, m.plate_thickness)

    @property
    def cutout(self) -> tuple[float, float, float, float]:
        """The Well Cutout ``(x0, y0, x1, y1)`` the plate is derived from (mm)."""
        self._ensure_model()
        return self._model.metadata.cutout

    @property
    def seam(self):
        """The plate Seam: the row-jogging path between key columns (ADR-0014)."""
        self._ensure_model()
        return self._model.seam

    @property
    def seam_depth(self) -> float:
        """The plate's extent in Y (mm) — what the Seam's bands span."""
        self._ensure_model()
        return self._model.metadata.height

    @property
    def section_outlines(self) -> list[list[tuple[float, float]]]:
        """The two Section outlines ``[left, right]`` (plate-local mm)."""
        self._ensure_model()
        return [list(poly) for poly in self._model.section_outlines]

    @property
    def plate_outline(self) -> list[tuple[float, float]]:
        """The plate outline polygon (mm, plate-local)."""
        self._ensure_model()
        return list(self._model.plate_outline)

    @property
    def edge_margins(self) -> tuple[float, float, float, float]:
        """The derived switch-free border per side ``(left, right, bottom, top)``."""
        self._ensure_model()
        return self._model.metadata.edge_margins

    def set_mounting_holes(self, holes: list[tuple[float, float, float]]) -> None:
        """Set the mounting holes the plate carries (low-level, plate-local mm).

        Prefer :meth:`set_well_mounts` when the holes come from the Well: it
        also merges the ears and cuts the notches the holes need, and checks
        that no hole misses its ear. This setter stays for callers that only
        want bare holes.

        Parameters
        ----------
        holes : list[tuple[float, float, float]]
            List of ``(x, y, diameter)`` tuples in mm (plate-local frame).
        """
        self._mounting_holes = [
            MountingHole(float(x), float(y), float(d)) for x, y, d in holes
        ]
        self._model = None  # regenerate with the new holes

    def set_well_mounts(self, mounts: Any) -> None:
        """Inject the Well-mount pattern (ADR-0014): ears, notches and holes.

        The plate is the Well's bearer, so its mounting pattern is the Well's,
        never the plate's own: the enclosure derives it with
        :func:`geometry.well_mounts.well_mounts` and hands it over. This method
        is the only place the keyboard model and the enclosure meet, and it
        passes plain rectangles (the keyboard package stays enclosure-free).

        Everything injected is **plate-local** -- ``plate_xy``, ``ear.rect`` and
        ``notch.rect`` are the pattern converted through the plate's own frame,
        the same centred frame this model builds in. The plate never composes
        the keyboard's placement turn: the frame did that once.

        Parameters
        ----------
        mounts : WellMounts-like
            Anything with ``frame`` (its size must be this plate's), ``mounts``
            (each carrying ``plate_xy``, ``clearance_hole_diameter`` and an
            ``ear``) and ``notches`` (each with a ``rect``);
            ``geometry.well_mounts.WellMounts`` is the real implementation. The
            object is kept for :meth:`well_mounts`.
        """
        self._well_mounts = mounts
        self._ears = [
            PlateTab(
                rect=(
                    float(mount.ear.rect.x0),
                    float(mount.ear.rect.y0),
                    float(mount.ear.rect.x1),
                    float(mount.ear.rect.y1),
                ),
                fillet=float(mount.ear.fillet or 0.0),
            )
            for mount in mounts.mounts
            if mount.ear is not None
        ]
        self._notches = [
            (
                float(notch.rect.x0),
                float(notch.rect.y0),
                float(notch.rect.x1),
                float(notch.rect.y1),
            )
            for notch in mounts.notches
        ]
        self._mounting_holes = [
            MountingHole(
                float(mount.plate_xy[0]),
                float(mount.plate_xy[1]),
                float(mount.clearance_hole_diameter),
            )
            for mount in mounts.mounts
        ]
        self._model = None  # regenerate with the injected pattern

    @property
    def well_mounts(self):
        """The injected Well-mount pattern, or ``None`` (ADR-0014)."""
        return self._well_mounts

    def footprint_cutouts(self) -> list[tuple[float, float, float, float]]:
        """The plan rectangles the chassis forces the plate to give up (mm).

        Plate-local ``(x0, y0, x1, y1)``: the plate's *notched* footprint, so a
        plan check can test the real sheet instead of its bounding box (the
        front band columns bite into the border). Empty before the Well-mount
        pattern is injected.
        """
        self._ensure_model()
        return list(self._notches)

    def footprint_outline(self) -> list[tuple[float, float]]:
        """The plate's notched, eared plan polygon (plate-local mm)."""
        self._ensure_model()
        return list(self._model.plate_outline)

    def _check_well_mounts(self, model) -> None:
        """Fail HARD if the injected pattern does not fit the real plate.

        The enclosure's own derivation checks the pattern too, but this is the
        last place before solid geometry: a hole that misses its ear or a tab
        that lands in a switch cutout would otherwise be modelled silently.
        """
        mounts = self._well_mounts
        if mounts is None:
            return
        problems: list[str] = list(mounts.failures)
        margin = float(getattr(mounts, "boss_margin", 0.0))
        # The pattern is plate-local, so its frame must be *this* plate: a
        # pattern derived for another plate size would drill the holes in the
        # wrong place while every rectangle still looked plausible (issue #19).
        frame = getattr(mounts, "frame", None)
        if frame is not None:
            meta = model.metadata
            if (
                abs(frame.width - meta.width) > _EPS + 1e-6
                or abs(frame.depth - meta.height) > _EPS + 1e-6
            ):
                problems.append(
                    f"frame: the Well-mount pattern is {frame.width:.2f} x "
                    f"{frame.depth:.2f} mm, this plate is {meta.width:.2f} x "
                    f"{meta.height:.2f} mm"
                )
        cutouts = list(model.switch_cutouts) + list(model.stabilizer_cutouts)
        boxes = []
        for cut in cutouts:
            xs = [cut.x + vx for vx, _ in cut.vertices]
            ys = [cut.y + vy for _, vy in cut.vertices]
            boxes.append((min(xs), min(ys), max(xs), max(ys)))
        ears: list[tuple[str, tuple[float, float, float, float]]] = []
        for mount in mounts.mounts:
            if mount.ear is None:
                problems.append(f"{mount.name}: no ear for its clearance hole")
                continue
            rect = (
                float(mount.ear.rect.x0),
                float(mount.ear.rect.y0),
                float(mount.ear.rect.x1),
                float(mount.ear.rect.y1),
            )
            ears.append((mount.name, rect))
            for index, box in enumerate(boxes):
                if _rects_overlap(rect, box):
                    problems.append(
                        f"{mount.name}: its ear overlaps cutout-{index}"
                    )
            x, y = mount.plate_xy
            radius = mount.clearance_hole_diameter / 2.0
            if not _circle_inside_rect(x, y, radius, rect, margin):
                problems.append(
                    f"{mount.name}: its Ø{mount.clearance_hole_diameter:.2f} "
                    f"clearance hole at ({x:.2f}, {y:.2f}) does not sit in its "
                    f"ear with the {margin:.2f} mm edge margin"
                )
            for index, box in enumerate(boxes):
                if _circle_hits_rect(x, y, radius, box):
                    problems.append(
                        f"{mount.name}: its clearance hole overlaps cutout-{index}"
                    )
        for index, (name, rect) in enumerate(ears):
            for other_name, other in ears[index + 1 :]:
                if _rects_overlap(rect, other):
                    problems.append(f"{name}: its ear overlaps {other_name}'s")
        if problems:
            raise ValueError(
                "the plate's Well-mount pattern does not fit the plate: "
                + "; ".join(problems)
            )

    def _get_mounting_holes(self) -> list[tuple[float, float, float]]:
        """Return ``(x, y, diameter)`` tuples the plate is cut with."""
        self._ensure_model()
        return [(h.x, h.y, h.diameter) for h in self._model.mounting_holes]

    def mounting_holes(self) -> list[Hole]:
        return [
            Hole(x, y, d, height=self._plate_thickness)
            for x, y, d in self._get_mounting_holes()
        ]

    @property
    def switch_positions(self) -> list[tuple[float, float]]:
        self._ensure_model()
        return list(self._model.metadata.switch_centers)

    def mounting_screw(self) -> str:
        """Screw library key for the plate mounting holes (from config)."""
        return self._screw_size

    def build(self):
        """Build the plate solid from the geometry model."""
        from utilities import cad_helpers
        from geometry.seam_joint import add_pins

        cad_helpers.require_cad()
        self._ensure_model()

        plate = cad_helpers.extrude_polygon(
            self._model.plate_outline,
            self._plate_thickness,
            z=self._plate_thickness / 2.0,
        )

        for cut in self._model.switch_cutouts:
            solid = cad_helpers.extrude_polygon(
                cut.vertices, self._plate_thickness + 1.0, cut.x, cut.y,
                z=self._plate_thickness / 2.0,
            )
            plate = cad_helpers.cut(plate, solid)

        for cut in self._model.stabilizer_cutouts:
            solid = cad_helpers.extrude_polygon(
                cut.vertices, self._plate_thickness + 1.0, cut.x, cut.y,
                z=self._plate_thickness / 2.0,
            )
            plate = cad_helpers.cut(plate, solid)

        # ADR-0006: add glued filament pins to the seam between keyboard halves.
        # Fins grow from the plate's lower face (local z = 0, the face that
        # faces the switch well / downward) downward into the lower side,
        # straddling the row-jogging Seam before the split halves them.
        if self._seam_pin_sites:
            plate = add_pins(
                plate, self.seam, self._seam_pin, self._seam_pin_sites,
                substrate=0.0, upward=False, chamfer=False, follow_step=True,
            )

        for x, y, d in self._get_mounting_holes():
            bore = cad_helpers.cylinder_centered(d, self._plate_thickness + 1.0)
            bore = cad_helpers.translate(bore, x, y, self._plate_thickness / 2.0)
            plate = cad_helpers.cut(plate, bore)

        return plate

    def plate_sections(self):
        """The plate cut into its two printable Sections along the Seam.

        The Seam is the row-jogging path between key columns
        (:func:`keyboard.geometry.seam.plate_seam`), never the straight
        ``x=0`` cut through switch cutouts (issue #9). The split is a boolean
        partition, so the Sections rejoin the whole losslessly; each must also
        fit the printer's build volume. Either failure raises (HARD).

        Returns
        -------
        list
            ``[left, right]`` solids in the plate's local frame.
        """
        from geometry.split import (
            check_build_volume,
            check_sections,
            split_sections,
        )
        from utilities import cad_helpers

        cad_helpers.require_cad()
        whole = self.build()
        sections = split_sections(whole, [self.seam], self.seam_depth)
        names = ("left", "right")
        problems = check_sections(whole, sections) + check_build_volume(
            dict(zip(names, sections))
        )
        if problems:
            raise ValueError(
                "the keyboard plate Sections are not printable: "
                + "; ".join(problems)
            )
        return sections

