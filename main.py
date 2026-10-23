"""Cyberdeck build CLI and pipeline driver.

Implements the build pipeline from ``docs/design_spec.md``:

    load configuration -> load components -> place layout -> validate
    placement -> generate enclosure -> generate bosses -> generate hinge ->
    generate cutouts -> generate ribs -> export STEP/STL/SVG -> run validation

The data layer (config, components, layout, validation, enclosure sizing,
bosses, cutouts, routing) and the CAD generation pass (assembly solid, base
shell, lid shell, hinge, STEP/STL/SVG export) are implemented. ``--steps``
lets you run only the data layer (e.g. ``--steps data``).
"""

from __future__ import annotations

import argparse
import datetime
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path

from components.battery import Battery
from components.display_88 import Display88
from components.hdmi_driver import HdmiDriver
from components.hdmi_plug import MiniHdmiPlug
from components.orange_pi_zero2w import OrangePiZero2W
from components.rp2040_keyboard import Rp2040Keyboard
from components.rp2040_zero import Rp2040Zero
from components.usb_breakout import UsbBreakout
from components.usb_c_plug import UsbCPlug
from geometry.ribs import rib_height
from layouts import LAYOUTS, make_layout
from layouts.layout_constrained import ConstraintLayout
from utilities.config_loader import Config, load_config
from utilities.file_metadata import apply as apply_fs_metadata
from utilities.validation import ValidationReport, run_all


class BuildPipeline:
    """Drives a complete cyberdeck build from configuration."""

    def __init__(
        self,
        config_path: str | Path = "config/default.yaml",
        layout_name: str = "compact",
        topics: tuple[str, ...] = ("display", "keyboard", "hardware"),
        recipe_path: str | Path | None = None,
    ) -> None:
        self.config_path = Path(config_path)
        self.layout_name = layout_name
        self.topics = topics
        self.recipe_path = Path(recipe_path) if recipe_path else None
        self.config: Config | None = None

    # --- pipeline stages -------------------------------------------------
    def load_config(self) -> Config:
        self.config = load_config(self.config_path, topics=self.topics)
        return self.config

    def load_components(self) -> dict:
        """Instantiate the hardware components from the resolved config."""
        assert self.config is not None, "call load_config() first"
        cfg = self.config
        display_cfg = {
            "width": cfg.display.width,
            "height": cfg.display.height,
            "thickness": cfg.display.thickness,
            "flex": asdict(cfg.display.flex) if cfg.display.flex else {},
            "driver_board": cfg.hardware.get("driver_board", {}),
        }
        keyboard_cfg = {
            "columns": cfg.keyboard.columns,
            "rows": cfg.keyboard.rows,
            "pitch": cfg.keyboard.pitch,
            "layout_source": cfg.keyboard.layout_source,
            "switch_family": cfg.keyboard.switch_family,
            "stabilizer_family": cfg.keyboard.stabilizer_family,
            "plate": cfg.keyboard.plate or {},
            "mounting": cfg.keyboard.mounting or {},
        }
        sbc = OrangePiZero2W(cfg.hardware)
        # Raise the SBC onto its mounting bosses, clear of the base floor's
        # stiffening ribs (geometry.ribs.rib_height); the layout recipe
        # raises the SBC's placement by the same amount.
        sbc.set_floor_raise(rib_height(cfg.wall_thickness))
        # No set_floor_raise call: the real board has no mounting holes (it
        # sits loose in its pocket under the plate, not screwed down), so
        # there are no mounting bosses to size — see components/rp2040_zero.py.
        controller = Rp2040Zero(cfg.keyboard.controller or {})

        # The SBC is buried under the keyboard plate, so the plate has to
        # stand tall enough for its switch bodies to clear the board — not
        # just the bare floor. Derived from the SBC's own height and the deck
        # slope rather than dialled in by hand, so re-measuring the board or
        # changing the slope re-sizes the standoffs with it.
        keyboard = Rp2040Keyboard(keyboard_cfg)
        keyboard.set_plate_raise(
            keyboard.plate_raise_for_buried(
                part_height=rib_height(cfg.wall_thickness) + sbc.size().height,
                part_depth=sbc.size().depth,
                slope=cfg.deck.slope,
                # Targets the sbc<->keyboard clearance the recipe checks
                # (1.5mm); the two numbers differ because the clearance
                # check is a true 3D separating-axis test (worst case over
                # every sub-volume pair, best axis per pair) while this is a
                # single along-Z estimate — 2.5 here reliably clears 1.5
                # there, empirically, not by a matching derivation. 3.3 (was
                # 2.5) pays for the SBC standing 10.3 mm further forward than
                # rear-flush: see the SBC placement in
                # config/layouts/clamshell.yaml.
                gap=3.3,
            )
        )
        driver = HdmiDriver(display_cfg)
        mini_hdmi_cfg = cfg.hardware.get("mini_hdmi_plug", {})
        return {
            "display": Display88(display_cfg),
            "driver": driver,
            "keyboard": keyboard,
            # The controller is its own placed component, not a sub-part of
            # the keyboard: the switch bodies hang 7 mm below the plate, so it
            # cannot fit under there — it sits on the case floor in the wedge
            # the sloped deck opens up beneath the keyboard's raised rear.
            "controller": controller,
            "sbc": sbc,
            # The cable plugged into the SBC is a solid obstruction in its
            # own right; which port it occupies is config, not geometry.
            "sbc_plug": UsbCPlug(cfg.hardware.get("usb_c_plug", {}), host=sbc),
            # The mini-HDMI ribbon between the SBC and the driver board is a
            # real cable, with a real connector shell at each end — modelled
            # the same way as the USB-C plug above, one instance per host so
            # each gets its own placement.
            "hdmi_plug_sbc": MiniHdmiPlug(mini_hdmi_cfg, host=sbc, label="SBC"),
            "hdmi_plug_driver": MiniHdmiPlug(
                mini_hdmi_cfg, host=driver, label="Driver"
            ),
            "battery": Battery(cfg.hardware),
            "usb_breakout": UsbBreakout(cfg.hardware),
        }

    def place_layout(self, components: dict):
        layout = make_layout(
            self.layout_name, components,
            config=self.config, recipe_path=self.recipe_path,
        )
        return layout

    def validate(self, placements, shell_depths=None, openings=None) -> str:
        """Run the placement validation suite and return its summary."""
        assert self.config is not None
        max_height = max(
            (p.z_bounds()[1] for p in placements), default=0.0
        )
        report = run_all(
            placements,
            self.config,
            shell_depths=shell_depths or {},
            shell_opening=openings or [],
            max_component_height=max_height,
            lid_interior_height=max_height,
        )
        return report.summary()

    def _provenance(self) -> dict:
        """Build provenance metadata describing this build.

        Layout, config path, git revision (best-effort), and build timestamp.
        Missing/unknown values are omitted rather than left empty.
        """
        prov = {"layout": self.layout_name}
        if self.config_path is not None:
            prov["config"] = str(self.config_path)
        rev = _git_rev()
        if rev:
            prov["rev"] = rev
        prov["built"] = datetime.datetime.now().astimezone().isoformat(timespec="seconds")
        return prov

    @staticmethod
    def _lid_interior(placements, components):
        """The placements that sit inside the Lid shell: panel, driver, plug."""
        from assemblies.assembly import select_placements

        return select_placements(
            placements,
            {components["display"], components["driver"], components["hdmi_plug_driver"]},
        )

    def _fastening_validation(self, config, components, placements, assembly, base, size):
        """Section, Seam and fastening checks (HARD), CAD-free.

        Seam stagger and clearance, the Parting plane and Deck screws, the
        keyboard plate's Seam screws.
        """
        import math

        from utilities.validation import (
            check_plate_seam_screws, check_seams,
        )

        report = ValidationReport()
        plate_world = None
        keyboard = components.get("keyboard")
        kb_placement = next((p for p in placements if p.component is keyboard), None)
        plate_local = None
        if keyboard is not None and kb_placement is not None:
            from keyboard.geometry.seam import plate_seam

            plate_local = plate_seam(keyboard.plate_model())
            tilt = math.cos(math.radians(kb_placement.tilt_x))
            depth = keyboard.plate_model().metadata.height
            plate_world = [
                (kb_placement.y + y0 * tilt, kb_placement.y + y1 * tilt, kb_placement.x + x)
                for y0, y1, x in plate_local.segments(depth)
            ]
        check_seams(config, size.width, report, plate_seam=plate_world, case_depth=size.depth)
        base.fastening_report(report)
        from case.lid import Lid

        display = next(p for p in placements if p.component is components["display"])
        lid = Lid(
            components["display"], config, hinge=base.hinge, world_z=display.z,
            footprint=(size.width, size.depth), visor=base.visor_profile(),
            assembly=assembly, interior_placements=self._lid_interior(placements, components),
        )
        lid.fastening_report(report)
        self._data_lid = lid
        if plate_local is not None:
            depth = keyboard.plate_model().metadata.height
            check_plate_seam_screws(
                [(h.x, h.y) for h in keyboard.mounting_holes()],
                plate_local.segments(depth), config.keyboard.pitch, report,
                expected_total=8,
            )
        return report

    def run(
        self,
        steps: str = "all",
        targets: str = "all",
        ignore_validation: bool = False,
        metrics_path: str | None = None,
    ) -> None:
        """Execute the pipeline up to ``steps``.

        Parameters
        ----------
        steps : str
            ``"all"`` runs every stage including CAD generation and export;
            ``"data"`` stops before CAD generation.
        targets : str
            Comma-separated build targets (default ``"all"``).  Buckets:
            ``all``, ``assembly``, ``base``, ``lid``, ``hinge``, ``display``,
            ``components``.  Per-component: ``comp:<role>``.
        ignore_validation : bool
            Normally a hard constraint violation aborts the build before any
            CAD is generated — the layout already knows the geometry is
            wrong, so exporting it would just ship that mistake as a file.
            Set this to build anyway: useful for inspecting *how* a rejected
            layout is wrong (a section view, a render) while iterating on a
            fix, not for shipping the result. The violation is still printed
            and still fails ``placement validation``/``constraint
            resolution`` above — this only skips the ``SystemExit``.
        metrics_path : str, optional
            If set, write a JSON dump of ``utilities.metrics.shape_metrics``
            for every built target (and, when the ``components`` bucket is
            selected, every component solid) to this path. Used to record or
            check a golden-master geometry baseline across refactors; has no
            effect on the exported files themselves.
        """
        config = self.load_config()
        print(f"[pipeline] config: {self.config_path} ({self.topics})")
        print(f"           layout: {self.layout_name}")
        print(f"           wall_thickness: {config.wall_thickness} mm")

        components = self.load_components()
        print(f"[pipeline] components: {', '.join(components)}")

        layout = self.place_layout(components)
        placements = layout.placements()
        print(f"[pipeline] placements: {len(placements)}")

        # Pre-enclosure assumptions: mounted components sit on the base floor
        # (wall thickness deep) and every externally-accessible connector needs
        # a shell opening. Internal connectors (driver/display FPC, cabled
        # driver power+HDMI) mate inside the case and are excluded.
        shell_depths = {
            p.component.name: config.wall_thickness
            for p in placements
            if p.component.mounting_holes()
        }
        openings = sorted(
            {
                c.type
                for p in placements
                for c in p.component.connectors()
                if not c.internal
            }
        )
        summary = self.validate(placements, shell_depths, openings)
        print("[pipeline] placement validation:")
        print(summary)

        if isinstance(layout, ConstraintLayout):
            creport = layout.constraint_report()
            if creport is not None:
                print("[pipeline] constraint resolution:")
                print(creport.summary())
                if not creport.passed:
                    # HARD is defined as "violation stops the build"; carrying
                    # on would export geometry the layout already knows is
                    # wrong — unless the caller explicitly asked to see that
                    # geometry anyway (--ignore-validation).
                    if not ignore_validation:
                        raise SystemExit(
                            "[pipeline] aborted: "
                            f"{len(creport.hard_violations)} hard constraint "
                            "violation(s) above"
                        )
                    print(
                        "[pipeline] WARNING: "
                        f"{len(creport.hard_violations)} hard constraint "
                        "violation(s) above — continuing anyway "
                        "(--ignore-validation)"
                    )

        for comp_name, component in components.items():
            if not hasattr(component, "validate"):
                continue
            comp_checks, comp_errors = component.validate()
            print(
                f"[pipeline] {comp_name} validation: "
                f"{comp_checks} check(s): "
                f"{'PASS' if not comp_errors else 'FAIL'}"
            )
            for error in comp_errors:
                print(f"  [x ] {error}")

        from assemblies.assembly import Assembly
        from case.base import Base
        from components.hinge import Hinge as HingePart

        assembly = Assembly(placements, config)
        size = assembly.enclosure_size()
        print(
            f"[pipeline] enclosure: {size.width:.1f} x {size.depth:.1f} x "
            f"{size.height:.1f} mm"
        )
        hinge = HingePart(asdict(config.hinge), wall_thickness=config.wall_thickness)
        base = Base(
            assembly, config, keyboard=components.get("keyboard"), hinge=hinge,
        )
        fastening_report = self._fastening_validation(
            config, components, placements, assembly, base, size
        )
        print("[pipeline] Section and fastening validation:")
        print(fastening_report.summary())
        if not fastening_report.passed and not ignore_validation:
            raise SystemExit(
                "[pipeline] aborted: Section/fastening validation failed "
                "(pass --ignore-validation to build anyway)"
            )

        if steps == "data":
            return

        print(f"[pipeline] bosses: {len(assembly.bosses())}")
        print(f"[pipeline] cutouts: {len(assembly.connector_cutouts())}")

        if steps != "all":
            return

        # --- CAD stages ---------------------------------------------------
        from case.lid import Lid
        from exports import EXPORTERS
        from utilities import cad_helpers
        from utilities.colors import color_for
        from utilities.targets import SECTION_NAMES, requested_sections, resolve_targets

        cad_helpers.require_cad()

        # Resolve build targets.
        target_tokens = [t.strip() for t in targets.split(",") if t.strip()]
        buckets, comp_roles = resolve_targets(target_tokens, set(components))

        # Build requested solids.
        parts: dict[str, object] = {}
        # Per-bucket colored `ColoredAssembly` for glTF export only — a
        # bucket without an entry here falls back to a single-color glTF
        # wrapping its fused `parts[name]` solid (see the export loop below).
        gltf_parts: dict[str, object] = {}
        role_map = {id(c): role for role, c in components.items()}

        if "assembly" in buckets:
            parts["assembly"] = assembly.build()
            gltf_parts["assembly"] = assembly.build_colored(
                placements=placements, role_map=role_map
            )

        # Keyboard placement is needed for base and hinge.
        needs_keyboard_placement = (
            "base" in buckets or "base_bottom" in buckets or "base_top" in buckets
            or "hinge" in buckets or "base_knuckle" in buckets
        )
        keyboard_placement = None
        if needs_keyboard_placement and "keyboard" in components:
            keyboard_placement = next(
                p for p in placements if p.component is components["keyboard"]
            )

        # Base bottom, top, and combined assembly.
        base_obj = None
        needs_lid = "lid" in buckets or "lid_shell" in buckets or "lid_bezel" in buckets
        needs_base = (
            "base" in buckets or "base_bottom" in buckets or "base_top" in buckets
            or "hinge" in buckets or "base_knuckle" in buckets
        )
        if needs_lid or needs_base:
            base_obj = base
        if base_obj is not None and needs_base:
            # Bosses (component mounting bosses and deck-mount standoffs)
            # are case-build-time geometry, never placed components, so the
            # ordinary collision system never sees them — check them here,
            # once the case geometry that generates them exists.
            from utilities.validation import ValidationReport, check_boss_collisions

            boss_report = ValidationReport()
            check_boss_collisions(base_obj.all_bosses(), placements, boss_report)
            print(f"[pipeline] boss validation: {boss_report.summary()}")
            if not boss_report.passed and not ignore_validation:
                raise SystemExit(
                    "[pipeline] aborted: a boss overlaps a component above "
                    "(pass --ignore-validation to build anyway)"
                )

        # Base sub-assembly solid: everything mounted on the base floor
        # (shared between "base" bucket and the combined "base" target). The
        # SBC and RP2040 controller sit tucked under the keyboard plate; the
        # battery sits beside the hub.
        base_subset_solid = None
        subset_placements: list = []
        if "base" in buckets and keyboard_placement is not None:
            from assemblies.assembly import select_placements

            base_subset_roles = {components["keyboard"]}
            for role in (
                "sbc", "sbc_plug", "hdmi_plug_sbc", "controller", "battery",
                "usb_breakout",
            ):
                if role in components:
                    base_subset_roles.add(components[role])
            subset_placements = select_placements(placements, base_subset_roles)
            if subset_placements:
                base_subset_solid = assembly.build_subset(subset_placements)

        if "base_bottom" in buckets and base_obj is not None:
            parts["base_bottom"] = base_obj.build_bottom()

        if "base_top" in buckets and base_obj is not None:
            parts["base_top"] = base_obj.build_top()

        if "keyboard_plate" in buckets and "keyboard" in components:
            parts["keyboard_plate"] = components["keyboard"].build_plate()

        if "base" in buckets and base_obj is not None:
            base_bottom_solid = base_obj.build_bottom()
            base_top_solid = base_obj.build_top()
            base_solid = base_bottom_solid
            if base_subset_solid is not None:
                base_solid = cad_helpers.union(base_solid, base_subset_solid)
            # .clean() (OCC shape healing): the deck's underside is now a
            # crease (sloped in front of the keyboard, flat behind it — see
            # case.base.Base._deck_knee_y), and base_bottom's walls follow
            # the same profile to seat against it. Unioning the two without
            # cleaning up afterward left sliver/degenerate topology right at
            # that seam that STEP/STL export tolerated but the SVG exporter's
            # hidden-line removal did not — it segfaulted the whole process,
            # silently, no Python exception to catch. Reproduced by bisecting
            # against git history: the prior (unkneed, single-plane) deck
            # never needed this.
            base_solid = cad_helpers.clean(cad_helpers.union(base_solid, base_top_solid))
            parts["base"] = base_solid

            if subset_placements:
                gltf_parts["base"] = assembly.build_colored(
                    placements=subset_placements,
                    role_map=role_map,
                    extra_parts=[
                        ("case", cad_helpers.clean(cad_helpers.union(base_bottom_solid, base_top_solid)))
                    ],
                )

        # Display placement is needed for lid and hinge.
        needs_display_placement = (
            "lid" in buckets or "lid_shell" in buckets or "lid_bezel" in buckets
            or "hinge" in buckets or "base_knuckle" in buckets
        )
        if needs_display_placement:
            display = next(p for p in placements if p.component is components["display"])

        # Display sub-assembly solid (shared between "display" bucket and
        # the combined "lid" target).
        display_assembly_solid = None
        if "display" in buckets or "lid" in buckets or "lid_shell" in buckets:
            from assemblies.assembly import select_placements

            display_placements = select_placements(
                placements,
                {
                    components["display"], components["driver"],
                    components["hdmi_plug_driver"],
                }
            )
            if display_placements:
                display_assembly_solid = assembly.build_subset(display_placements)
                if "display" in buckets:
                    parts["display"] = display_assembly_solid

        # Lid base, bezel, and combined lid assembly.
        if "lid_shell" in buckets or "lid_bezel" in buckets or "lid" in buckets:
            lid = Lid(
                display.component,
                config,
                hinge=hinge,
                world_z=display.z,
                footprint=(size.width, size.depth),
                interior=display_assembly_solid,
                visor=base_obj.visor_profile(),
                assembly=assembly,
                interior_placements=self._lid_interior(placements, components),
            )
            from utilities.validation import (
                ValidationReport, check_hinge_clearance, check_hinge_fits,
                check_visor_flush,
            )

            visor_report = ValidationReport()
            visor_profile = lid.visor
            check_visor_flush(
                base_obj.deck_top_at, visor_profile.height_at,
                -size.depth / 2.0, size.depth / 2.0, visor_report,
            )
            visor_report.goals["closed thickness (mm)"] = (
                base_obj.closed_plane_z() + lid.height()
            )
            check_hinge_fits(
                hinge.diameter, base_obj.closed_plane_z(), lid.height(), visor_report
            )
            axis_z = base_obj.hinge_axis_z()
            knuckle_x0, knuckle_x1 = hinge.base_knuckle_span(size.width)
            rear_y = -size.depth / 2.0
            check_hinge_clearance(
                (
                    knuckle_x0, knuckle_x1,
                    rear_y, rear_y + config.wall_thickness,
                    axis_z - hinge.diameter / 2.0, axis_z + hinge.diameter / 2.0,
                ),
                placements, visor_report,
                extra_boxes={
                    f"{side} end cheek": (
                        c0, c1, rear_y, rear_y + config.wall_thickness,
                        axis_z - hinge.diameter / 2.0, axis_z + hinge.diameter / 2.0,
                    )
                    for side, (c0, c1) in zip(("left", "right"), hinge.cheek_spans(size.width))
                } | {
                    "flange": (
                        hinge.part_span(size.width)[0], hinge.part_span(size.width)[1],
                        rear_y, rear_y + hinge.flange_depth,
                        -config.wall_thickness - hinge.flange, 0.0,
                    )
                },
            )
            from utilities.validation import check_hinge_sweep

            check_hinge_sweep(
                hinge.cheek_spans(size.width), hinge.base_knuckle_span(size.width),
                hinge.lid_notch_spans(size.width),
                hinge.web_top, hinge.radius, visor_report,
            )
            print("[pipeline] closed-device validation:")
            print(visor_report.summary())
            if not visor_report.passed and not ignore_validation:
                raise SystemExit(
                    "[pipeline] aborted: Visor does not close flush "
                    "(pass --ignore-validation to build anyway)"
                )

        if "lid_shell" in buckets:
            parts["lid_shell"] = lid.build_shell()

        if "lid_bezel" in buckets:
            parts["lid_bezel"] = lid.build_bezel()

        if "lid" in buckets:
            lid_shell_solid = lid.build_shell()
            lid_bezel_solid = lid.build_bezel()
            lid_solid = lid_shell_solid
            if display_assembly_solid is not None:
                lid_solid = cad_helpers.union(lid_solid, display_assembly_solid)
            lid_solid = cad_helpers.union(lid_solid, lid_bezel_solid)
            parts["lid"] = lid_solid

            if display_placements:
                gltf_parts["lid"] = assembly.build_colored(
                    placements=display_placements,
                    role_map=role_map,
                    extra_parts=[("case", cad_helpers.union(lid_shell_solid, lid_bezel_solid))],
                )

        if "base_knuckle" in buckets or "hinge" in buckets:
            knuckle_solid = base_obj.build_knuckle()
        if "base_knuckle" in buckets:
            parts["base_knuckle"] = knuckle_solid
            gltf_parts["base_knuckle"] = cad_helpers.new_assembly()
            cad_helpers.assembly_add(
                gltf_parts["base_knuckle"], knuckle_solid, "Base knuckle",
                color_for("base_knuckle"),
            )

        if "hinge" in buckets:
            hinge_z = base_obj.hinge_axis_z()
            on_axis = lambda s: cad_helpers.translate(s, 0.0, -size.depth / 2.0, hinge_z)
            hardware = on_axis(hinge.build_hardware(size.width))
            lid_knuckles = on_axis(hinge.build_lid_knuckles(size.width))
            parts["hinge"] = cad_helpers.union(hardware, lid_knuckles, knuckle_solid)
            # One color per hinge piece: the Base knuckle part, its end cheeks,
            # the Lid knuckles and the bolts/nuts/washers/caps.
            colored = cad_helpers.new_assembly()
            cheeks = []
            for c0, c1 in hinge.cheek_spans(size.width):
                box = cad_helpers.translate(
                    cad_helpers.box_centered(c1 - c0, 4 * hinge.diameter, 4 * hinge.diameter),
                    (c0 + c1) / 2.0, -size.depth / 2.0, hinge_z,
                )
                cheeks.append(cad_helpers.intersect(knuckle_solid, box))
            cheek_solid = cad_helpers.union(*cheeks)
            for role, label, shape in (
                ("base_knuckle", "Base knuckle", cad_helpers.cut(knuckle_solid, cheek_solid)),
                ("end_cheek", "End cheeks", cheek_solid),
                ("lid_knuckle", "Lid knuckles", lid_knuckles),
                ("hinge_hardware", "Bolts, nuts, washers, caps", hardware),
            ):
                cad_helpers.assembly_add(colored, shape, label, color_for(role))
            gltf_parts["hinge"] = colored

        # ── Opened assembly: base in ZX plane, lid upward, LCD faces +Z ──
        if "assembly_opened" in buckets:
            from assemblies.assembly import select_placements

            if base_obj is None:
                base_obj = base
            if "display" in components:
                display_placement = next(
                    p for p in placements
                    if p.component is components["display"]
                )
            lid = Lid(
                components["display"], config, hinge=hinge,
                world_z=display_placement.z,
                footprint=(size.width, size.depth),
                visor=base_obj.visor_profile(),
                assembly=assembly,
                interior_placements=self._lid_interior(placements, components),
            )

            # Build base solid (closed position).
            base_solid = base_obj.build_bottom()
            if "keyboard" in components:
                base_subset_roles = {components["keyboard"]}
                for role in (
                "sbc", "sbc_plug", "hdmi_plug_sbc", "controller", "battery",
                "usb_breakout",
            ):
                    if role in components:
                        base_subset_roles.add(components[role])
                subset = select_placements(placements, base_subset_roles)
                if subset:
                    base_solid = cad_helpers.union(
                        base_solid, assembly.build_subset(subset)
                    )
            base_solid = cad_helpers.union(base_solid, base_obj.build_top())

            # Build lid solid (closed position).
            lid_solid = lid.build_shell()
            display_placements = select_placements(
                placements,
                {
                    components["display"], components["driver"],
                    components["hdmi_plug_driver"],
                }
            )
            if display_placements:
                lid_solid = cad_helpers.union(
                    lid_solid, assembly.build_subset(display_placements)
                )
            lid_solid = cad_helpers.union(lid_solid, lid.build_bezel())

            # Hinge axis in the original frame.
            depth = size.depth
            hinge_z = base_obj.hinge_axis_z()
            driver_height = float(
                config.hardware.get("driver_board", {}).get("height", 4.6)
            )

            # Step 1: stand the closed assembly upright so the base sits in
            # the ZX plane (vertical), keyboard facing +Y.
            #   -90° about X: (x,y,z) → (x, z, -y)
            #   Hinge at (0, -depth/2, hinge_z) → (0, hinge_z, depth/2)
            base_u = cad_helpers.rotate_x(base_solid, -90)
            lid_u = cad_helpers.rotate_x(lid_solid, -90)
            hinge_u = hinge.build(case_depth=size.width, drop=base_obj.knuckle_drop())
            hinge_u = cad_helpers.translate(
                hinge_u, 0.0, -depth / 2.0, hinge_z
            )
            hinge_u = cad_helpers.rotate_x(hinge_u, -90)

            # Step 2: open the lid +90° about the hinge axis so it extends
            # in +Y (upward from the base) with the LCD facing +Z.
            ax_y = hinge_z
            ax_z = depth / 2.0
            lid_open = cad_helpers.rotate_about(
                lid_u, (0.0, ax_y, ax_z), (1.0, ax_y, ax_z), 90
            )

            # Step 3: flip the whole assembly 180° about Y so the base rear
            # faces -Z instead of +Z.
            base_f = cad_helpers.rotate_y(base_u, 180)
            lid_f = cad_helpers.rotate_y(lid_open, 180)
            hinge_f = cad_helpers.rotate_y(hinge_u, 180)

            # Step 4: rotate the lid 180° about the Y axis through the hinge
            # center so the LCD faces +Z again (the Y flip flipped it to -Z).
            # Hinge after step 3: (0, hinge_z, -depth/2) along X.
            hy = hinge_z
            hz = -depth / 2.0
            lid_f = cad_helpers.rotate_about(lid_f, (0, hy, hz), (0, hy + 1, hz), 180)

            # Step 5: translate the lid in -Z so its +Z face (LCD side) sits
            # at the hinge, making the lid extend behind the hinge in -Z.
            lid_total_h = (
                config.display.height + driver_height
                + 2 * config.clearance.shell + 2 * config.wall_thickness
            )
            z_offset = display_placement.z - hinge_z
            dist_to_plus_z = z_offset + lid_total_h / 2.0
            lid_f = cad_helpers.translate(lid_f, 0, 0, -dist_to_plus_z)

            parts["assembly_opened"] = cad_helpers.union(base_f, lid_f, hinge_f)

        # --- Sections (ADR 0003) ---------------------------------------------
        # Every wide printable part is split into two or three Sections along
        # its Seams; the Sections, not the whole part, are what must fit the
        # printer, so they are validated here and exported with the rest.
        from geometry import edge_treatment
        from geometry.printability import (
            BED_DOWN, bed_face_area, check_bed_face, overhang_faces,
        )
        from geometry.split import check_build_volume, check_sections, split_sections

        split_sources = {
            "base_bottom": "tray",
            "base_top": "deck",
            "lid_shell": "lid_shell",
            "lid_bezel": "bezel",
            "keyboard_plate": "keyboard_plate",
        }
        printable: dict[str, object] = {}
        section_depths = {
            name: size.depth for name in split_sources if name != "keyboard_plate"
        }
        split_plans: dict[str, tuple[list, float]] = {}
        for name, key in split_sources.items():
            if name in section_depths and key in config.split:
                split = config.split[key]
                if split.section_names != SECTION_NAMES[name]:
                    raise SystemExit(
                        f"[pipeline] aborted: config.split.{key} has {split.sections} "
                        f"Sections but target {name} names {SECTION_NAMES[name]}"
                    )
                split_plans[name] = (split.seams(), section_depths[name])
        if "keyboard_plate" in parts:
            # The plate Seam is derived from the key layout, not configured:
            # it must run through the key-column gaps (ADR 0003).
            from keyboard.geometry.seam import plate_seam, seam_conflicts

            plate_model = components["keyboard"].plate_model()
            plate_cfg = plate_seam(plate_model)
            conflicts = seam_conflicts(plate_model, plate_cfg)
            print(
                "[pipeline] keyboard_plate Seam avoids switch cutouts: "
                f"{'PASS' if not conflicts else 'FAIL'}"
            )
            for conflict in conflicts:
                print(f"  [x ] {conflict}")
            if conflicts and not ignore_validation:
                raise SystemExit(
                    "[pipeline] aborted: plate Seam cuts a switch cutout "
                    "(pass --ignore-validation to build anyway)"
                )
            split_plans["keyboard_plate"] = ([plate_cfg], plate_model.metadata.height)
        section_report = ValidationReport()
        section_info: dict[str, dict] = {}
        bed_areas: dict[str, float] = {}
        for part_name, (seams, part_depth) in split_plans.items():
            if part_name not in parts:
                continue
            sections = split_sections(parts[part_name], seams, part_depth)
            names = SECTION_NAMES[part_name]
            errors = check_sections(parts[part_name], sections)
            section_info[part_name] = {
                "sections": len(sections), "rejoin": not errors,
                "names": [f"{part_name}_{n}" for n in names],
            }
            for section_name, section in zip(names, sections):
                full = f"{part_name}_{section_name}"
                # Edge treatment goes on each Section after the lossless rejoin
                # check above: concave joints get a stress-relief chamfer, the
                # bed face a small outer chamfer against elephant's foot (which
                # trims the Seam faces too).
                treated = ValidationReport()
                section = edge_treatment.relieve_concave_joints(
                    section, BED_DOWN, config.edges.chamfer_factor * config.wall_thickness,
                    treated,
                )
                section = edge_treatment.bed_chamfer(
                    section, BED_DOWN, config.edges.bed_chamfer, treated
                )
                for message in treated.warnings:
                    section_report.warn(f"{full}: {message}")
                check_bed_face(
                    full, section, BED_DOWN, config.material.min_bed_face_area, section_report
                )
                bed_areas[full] = bed_face_area(section, BED_DOWN)
                for face in overhang_faces(section, BED_DOWN)[:1]:
                    section_report.warn(
                        f"{full}: overhang {face.angle_from_vertical:.0f} deg from vertical "
                        f"({face.area:.0f} mm^2 at {tuple(round(c) for c in face.center)}) needs support"
                    )
                parts[full] = section
                printable[full] = section
                colored_section = cad_helpers.new_assembly()
                cad_helpers.assembly_add(
                    colored_section, section, full, color_for(f"section_{section_name}")
                )
                gltf_parts[full] = colored_section
            if errors:
                print(f"[pipeline] {part_name} Sections: FAIL")
                for error in errors:
                    print(f"  [x ] {error}")
                if not ignore_validation:
                    raise SystemExit(
                        f"[pipeline] aborted: {part_name} Sections are invalid "
                        "(pass --ignore-validation to build anyway)"
                    )
        # A Section named on its own (e.g. ``lid_shell_left``) exports just that
        # Section; the whole part and the other Sections were only built to
        # check it.
        only_sections = requested_sections(target_tokens)
        if only_sections:
            for part_name in split_sources:
                names = [f"{part_name}_{n}" for n in SECTION_NAMES[part_name]]
                if not only_sections & set(names + [part_name]):
                    continue
                if names[0] not in parts:
                    continue  # unsplit part: the whole part is its only form
                for name in [part_name] + names:
                    if name not in only_sections:
                        for table in (parts, printable, gltf_parts):
                            table.pop(name, None)
        fit_errors = check_build_volume(printable)
        print(
            f"[pipeline] build volume: {len(printable)} printable part(s): "
            f"{'PASS' if not fit_errors else 'FAIL'}"
        )
        for error in fit_errors:
            print(f"  [x ] {error}")
        print("[pipeline] printability:")
        print(section_report.summary())
        if (fit_errors or not section_report.passed) and not ignore_validation:
            raise SystemExit(
                "[pipeline] aborted: a printable part exceeds the build volume "
                "or has no bed face (pass --ignore-validation to build anyway)"
            )

        # Export all built parts.
        provenance = self._provenance()
        metrics: dict[str, object] = {}
        if metrics_path is not None:
            from utilities.metrics import shape_metrics
        for name, solid in parts.items():
            if metrics_path is not None:
                metrics[name] = shape_metrics(solid)
            for fmt, exporter_cls in EXPORTERS.items():
                exporter = exporter_cls()
                exporter.metadata = provenance
                path = exporter.output_path(f"cyberdeck_{name}")
                # glTF prefers the colored per-component/sub-assembly
                # `ColoredAssembly` built above; buckets without one (e.g.
                # hinge, a single part) fall back to the fused solid, which
                # GltfExporter wraps in a single default color.
                export_obj = gltf_parts.get(name, solid) if fmt == "gltf" else solid
                exporter.export(export_obj, path)
                # SvgExporter can skip writing the file on a subprocess crash
                # (see exports/export_svg.py) rather than take the build
                # down with it — its own warning already explains why, so
                # this only needs to avoid claiming a nonexistent file was
                # exported and attempting metadata on it.
                if not path.exists():
                    continue
                if not apply_fs_metadata(provenance, path):
                    print(f"[pipeline] warning: could not write fs metadata for {path}")
                print(f"[pipeline] exported {name} -> {path}")

        # Per-component debug STLs.
        stl_cls = EXPORTERS.get("stl")
        if stl_cls is not None:
            stl_exporter = stl_cls()
            stl_exporter.metadata = provenance
            if "components" in buckets:
                for comp_name, comp in components.items():
                    try:
                        comp_solid = comp.build()
                    except NotImplementedError:
                        continue
                    path = stl_exporter.output_path(f"component_{comp_name}")
                    stl_exporter.export(comp_solid, path)
                    if metrics_path is not None:
                        metrics[f"component_{comp_name}"] = shape_metrics(comp_solid)
                    if not apply_fs_metadata(provenance, path):
                        print(f"[pipeline] warning: could not write fs metadata for {path}")
                    print(f"[pipeline] exported component {comp_name} -> {path}")
            else:
                for role in comp_roles:
                    comp = components[role]
                    try:
                        comp_solid = comp.build()
                    except NotImplementedError:
                        continue
                    path = stl_exporter.output_path(f"component_{role}")
                    stl_exporter.export(comp_solid, path)
                    if metrics_path is not None:
                        metrics[f"component_{role}"] = shape_metrics(comp_solid)
                    if not apply_fs_metadata(provenance, path):
                        print(f"[pipeline] warning: could not write fs metadata for {path}")
                    print(f"[pipeline] exported component {role} -> {path}")

        if metrics_path is not None:
            import json

            # Pipeline-level results next to the per-target shape metrics: how
            # each part was split, what it prints on, how many screws of each
            # kind hold the case together, and the HARD/SOFT check outcomes.
            lid_data = getattr(self, "_data_lid", None)
            metrics["_pipeline"] = {
                "sections": section_info,
                "print_orientation": {n: list(BED_DOWN.normal) for n in printable},
                "bed_face_mm2": bed_areas,
                "screws": {
                    "plate": len(components["keyboard"].mounting_holes()),
                    "bezel": len(lid_data.screw_positions()) if lid_data else 0,
                    "deck": len(base.columns()),
                    "hinge_bolts": 2,
                    "hinge_flange": sum(len(v) for v in base.knuckle_screw_sites().values()),
                    "hinge_deck": sum(len(v) for v in base.deck_knuckle_sites().values()),
                },
                "checks": {c.name + (f"#{i}" if sum(1 for d in fastening_report.checks if d.name == c.name) > 1 else ""): c.passed
                           for i, c in enumerate(fastening_report.checks)},
                "hard_failures": len(fastening_report.failures) + len(section_report.failures),
                "soft_warnings": len(fastening_report.warnings) + len(section_report.warnings),
            }
            Path(metrics_path).write_text(json.dumps(metrics, indent=2, sort_keys=True))
            print(f"[pipeline] wrote metrics -> {metrics_path}")


def _git_rev() -> str | None:
    """Return the short HEAD revision, or ``None`` if not in a git repo."""
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return None
    if out.returncode != 0:
        return None
    return out.stdout.strip() or None


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="cyberdeck",
        description="Parametric clamshell cyberdeck CAD generator.",
    )
    parser.add_argument(
        "--config",
        default="config/default.yaml",
        help="path to the default YAML configuration",
    )
    parser.add_argument(
        "--layout",
        default="compact",
        choices=list(LAYOUTS),
        help="layout definition to place components",
    )
    parser.add_argument(
        "--layout-recipe",
        default=None,
        help="path to a YAML recipe file, used instead of the built-in recipe",
    )
    parser.add_argument(
        "--steps",
        default="all",
        choices=["all", "data"],
        help="'all' runs every stage; 'data' stops before CAD generation",
    )
    parser.add_argument(
        "--targets",
        default="all",
        help="comma-separated build targets (default: all). "
             "Buckets: all, assembly, base, base_bottom, base_top, "
             "lid, lid_shell, lid_bezel, keyboard_plate, hinge, display, components. "
             "Per-component: comp:<role> (e.g. comp:driver).",
    )
    parser.add_argument(
        "--ignore-validation",
        action="store_true",
        help="build and export even if a hard constraint (collision, "
             "clearance, etc.) fails, instead of aborting. The failure is "
             "still printed. For inspecting a known-bad layout while "
             "iterating on a fix, not for shipping the result.",
    )
    parser.add_argument(
        "--metrics",
        default=None,
        metavar="PATH",
        help="write a JSON geometry-metrics dump (volume/bbox/center of "
             "mass per target) to PATH. Used for golden-master regression "
             "checks, e.g. across the CadQuery -> build123d port.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv or sys.argv[1:])
    pipeline = BuildPipeline(
        config_path=args.config,
        layout_name=args.layout,
        recipe_path=args.layout_recipe,
    )
    try:
        pipeline.run(
            steps=args.steps,
            targets=args.targets,
            ignore_validation=args.ignore_validation,
            metrics_path=args.metrics,
        )
    except NotImplementedError as exc:
        print(f"[pipeline] CAD stage not yet implemented: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
