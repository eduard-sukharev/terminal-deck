"""Cyberdeck build CLI and pipeline driver.

Implements the build pipeline from ``docs/design_spec.md``:

    load configuration -> load components -> place layout -> validate
    placement -> slide budget -> slider validation -> build chassis/screen
    lid/slide -> export STEP/STL/glTF

The data layer (config, components, layout, validation, slide budget) and the
first-generation slider CAD pass (chassis, screen lid, guide hardware, closed
and open assembly exports) are implemented. ``--steps`` lets you run only the
data layer (e.g. ``--steps data``).
"""

from __future__ import annotations

import argparse
import datetime
import json
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path

from components.battery import Battery
from components.display_88 import Display88
from components.hdmi_driver import HdmiDriver
from components.orange_pi_zero2w import OrangePiZero2W
from components.rp2040_keyboard import Rp2040Keyboard
from components.rp2040_zero import Rp2040Zero
from components.usb_breakout import UsbBreakout
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
        layout_name: str = "slider",
        topics: tuple[str, ...] = ("display", "keyboard", "hardware", "slide"),
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

        # The slider buries the RP2040 under the keyboard plate; the SBC sits
        # in the rear band, not under the keyboard. The plate standoff is
        # sized for the controller's switch-body clearance.
        keyboard = Rp2040Keyboard(keyboard_cfg)
        keyboard.set_plate_raise(
            keyboard.plate_raise_for_buried(
                part_height=rib_height(cfg.wall_thickness)
                + controller.size().height,
                gap=float((cfg.keyboard.controller or {}).get("z_clearance", 2.0)),
            )
        )
        driver = HdmiDriver(display_cfg)
        return {
            "display": Display88(display_cfg),
            "driver": driver,
            "keyboard": keyboard,
            # The controller is its own placed component, not a sub-part of
            # the keyboard: the switch bodies hang 7 mm below the plate, so it
            # cannot fit under there — it sits on the case floor under the
            # keyboard's raised rear.
            "controller": controller,
            "sbc": sbc,
            # External accessory: the battery model is retained for the
            # pack on the accessory rail, but it is not a chassis placement.
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

    def _run_slider_data(
        self,
        config,
        components,
        placements,
        steps: str,
        targets: str,
        ignore_validation: bool,
        metrics_path: str | None = None,
    ) -> None:
        """The slider's data stage: budget, checks and the placement envelope.

        With ``steps="all"`` it continues into the first-generation CAD shell
        and its exports (issue #3).
        """
        from assemblies.assembly import Assembly
        from components.slide import compute_slide_budget
        from utilities.slider_validation import run_slider_checks

        assembly = Assembly(placements, config)
        size = assembly.enclosure_size()
        print(
            f"[pipeline] placement envelope: {size.width:.1f} x "
            f"{size.depth:.1f} x {size.height:.1f} mm "
            "(component extent incl. walls; the device envelope is the slide "
            "budget below)"
        )

        budget = compute_slide_budget(config, components)
        print("[pipeline] slide budget:")
        print(budget.summary())

        report = run_slider_checks(budget, config, placements)
        print("[pipeline] slider validation:")
        print(report.summary())
        if not report.passed and not ignore_validation:
            raise SystemExit(
                "[pipeline] aborted: slider validation failed "
                "(pass --ignore-validation to inspect a rejected layout)"
            )

        if steps == "data":
            return
        self._run_slider_cad(
            config, components, placements, budget, targets,
            ignore_validation, metrics_path,
        )

    def _run_slider_cad(
        self,
        config,
        components,
        placements,
        budget,
        targets: str,
        ignore_validation: bool,
        metrics_path: str | None = None,
    ) -> None:
        """Build and export the first-generation slider case (issue #3)."""
        from assemblies.assembly import Assembly, select_placements
        from case.chassis import Chassis
        from case.screen_lid import ScreenLid
        from case.slider_frame import SliderFrame
        from components.slide import build_guide_rod, build_linear_bearing
        from exports import EXPORTERS
        from utilities import cad_helpers as ch

        ch.require_cad()
        frame = SliderFrame.from_data(config, budget, components, placements)
        chassis_shell = Chassis(config, frame).build()

        # The hub's +Y port strip is the externally reachable I/O; bore its
        # openings through the chassis rear wall. The east USB-A is blocked by
        # the right side pod and is intentionally not exposed.
        hub = components.get("usb_breakout")
        hub_placement = next(
            (p for p in placements if p.component is hub), None
        ) if hub is not None else None
        if hub_placement is not None:
            port_tools = []
            for connector in hub.connectors():
                if connector.internal or connector.direction[1] <= 0:
                    continue
                wx, _, wz = hub_placement.world_offset(
                    connector.x, connector.y, connector.z
                )
                tool = ch.box_centered(
                    connector.width + 2.0 * frame.clearance,
                    3.0 * frame.wall,
                    connector.height + 2.0 * frame.clearance,
                )
                port_tools.append(
                    ch.translate(tool, wx, frame.depth / 2.0, wz)
                )
            if port_tools:
                chassis_shell = ch.clean(ch.cut(chassis_shell, *port_tools))

        lid_shell = ScreenLid(config, frame).build()

        rods = [
            ch.translate(
                build_guide_rod(config.slide.rod.diameter, frame.rod_length),
                side * frame.rod_x,
                frame.rod_y,
                frame.rod_z,
            )
            for side in (-1, 1)
        ]
        bearings = [
            ch.translate(
                build_linear_bearing(
                    frame.bearing_outer, frame.bearing_bore, frame.bearing_length
                ),
                side * frame.rod_x,
                frame.clamp_center_y,
                frame.rod_z,
            )
            for side in (-1, 1)
        ]
        rods_compound = ch.make_compound(rods)
        bearings_compound = ch.make_compound(bearings)
        slide = ch.make_compound(rods + bearings)

        assembly = Assembly(placements, config)
        role_map = {id(component): role for role, component in components.items()}
        chassis_roles = ("keyboard", "sbc", "usb_breakout", "controller")
        lid_roles = ("display", "driver")
        chassis_parts = select_placements(
            placements, {components[r] for r in chassis_roles if r in components}
        )
        lid_parts = select_placements(
            placements, {components[r] for r in lid_roles if r in components}
        )
        chassis_with_parts = ch.make_compound(
            [chassis_shell] + [assembly.build_subset([p]) for p in chassis_parts]
        )
        lid_with_parts = ch.make_compound(
            [lid_shell] + [assembly.build_subset([p]) for p in lid_parts]
        )
        assembly_solid = ch.make_compound(
            [chassis_with_parts, lid_with_parts, slide]
        )
        travel = budget.travel
        assembly_opened = ch.make_compound(
            [
                chassis_with_parts,
                ch.translate(lid_with_parts, 0.0, travel, 0.0),
                ch.translate(rods_compound, 0.0, travel, 0.0),
                bearings_compound,
            ]
        )

        plate = components["keyboard"].build_plate()
        split = config.slide.split
        chassis_left, chassis_right = ch.split_sections(
            chassis_shell, split.get("chassis")
        )
        lid_left, lid_right = ch.split_sections(lid_shell, split.get("screen_lid"))
        plate_left, plate_right = ch.split_sections(
            plate, split.get("keyboard_plate")
        )

        parts = {
            "assembly": assembly_solid,
            "assembly_opened": assembly_opened,
            "chassis": chassis_with_parts,
            "chassis_left": chassis_left,
            "chassis_right": chassis_right,
            "screen_lid": lid_with_parts,
            "screen_lid_left": lid_left,
            "screen_lid_right": lid_right,
            "slide": slide,
            "keyboard_plate": plate,
            "keyboard_plate_left": plate_left,
            "keyboard_plate_right": plate_right,
            "display": ch.make_compound(
                [assembly.build_subset([p]) for p in lid_parts]
            ),
        }

        tokens = [token.strip() for token in targets.split(",") if token.strip()]
        if "all" in tokens:
            tokens = list(parts) + ["components"]
        selected: dict[str, object] = {}
        for token in tokens:
            if token == "components":
                # Only the components the slider actually places. The battery
                # is an external accessory and the cable plugs are not modelled
                # in this generation; they stay reachable via comp:<role>.
                placed_roles = {
                    "display", "driver", "keyboard", "sbc",
                    "usb_breakout", "controller",
                }
                for role, component in components.items():
                    if role not in placed_roles:
                        continue
                    try:
                        selected[f"component_{role}"] = component.build()
                    except NotImplementedError:
                        continue
            elif token.startswith("comp:"):
                role = token.split(":", 1)[1]
                if role not in components:
                    raise ValueError(f"unknown component role {role!r}")
                selected[f"component_{role}"] = components[role].build()
            elif token in parts:
                selected[token] = parts[token]
            else:
                raise ValueError(
                    f"unknown slider target {token!r}; expected one of "
                    f"{sorted(parts)} or 'components'"
                )

        # Sections must fit the printer; the whole part is exported for
        # reference but is not printable across X.
        printable = (
            "chassis_left",
            "chassis_right",
            "screen_lid_left",
            "screen_lid_right",
            "keyboard_plate_left",
            "keyboard_plate_right",
        )
        volume = (220.0, 220.0, 256.0)
        failures = []
        for name in printable:
            if name not in selected:
                continue
            x, y, z = ch.bounding_box_mm(selected[name])
            ok = x <= volume[0] + 1e-6 and y <= volume[1] + 1e-6 and z <= volume[2] + 1e-6
            print(
                f"[pipeline] {name}: {x:.1f} x {y:.1f} x {z:.1f} mm "
                f"{'fits' if ok else 'EXCEEDS'} the build volume"
            )
            if not ok:
                failures.append(name)
        if failures and not ignore_validation:
            raise SystemExit(
                f"[pipeline] aborted: Sections exceed the build volume: {failures}"
            )

        gltf_assembly = assembly.build_colored(
            placements=placements,
            role_map=role_map,
            extra_parts=[
                ("chassis", chassis_shell),
                ("screen_lid", lid_shell),
                ("guide_rod", rods_compound),
                ("linear_bearing", bearings_compound),
            ],
        )
        gltf_chassis = assembly.build_colored(
            placements=chassis_parts,
            role_map=role_map,
            extra_parts=[("chassis", chassis_shell)],
        )
        gltf_lid = assembly.build_colored(
            placements=lid_parts,
            role_map=role_map,
            extra_parts=[
                ("screen_lid", lid_shell),
                ("guide_rod", rods_compound),
                ("linear_bearing", bearings_compound),
            ],
        )

        def _move_y(solid):
            return ch.translate(solid, 0.0, budget.travel, 0.0)

        open_transform = {
            id(components[role]): _move_y
            for role in ("display", "driver")
            if role in components
        }
        gltf_opened = assembly.build_colored(
            placements=placements,
            role_map=role_map,
            transform=open_transform,
            extra_parts=[
                ("chassis", chassis_shell),
                ("screen_lid", _move_y(lid_shell)),
                ("guide_rod", _move_y(rods_compound)),
                ("linear_bearing", bearings_compound),
            ],
        )
        gltf_special = {
            "assembly": gltf_assembly,
            "assembly_opened": gltf_opened,
            "chassis": gltf_chassis,
            "screen_lid": gltf_lid,
        }

        provenance = self._provenance()
        metrics: dict[str, object] = {}
        if metrics_path is not None:
            from utilities.metrics import shape_metrics
        for name, solid in selected.items():
            if metrics_path is not None:
                metrics[name] = shape_metrics(solid)
            x, y, z = ch.bounding_box_mm(solid)
            print(
                f"[pipeline] {name}: bbox {x:.1f} x {y:.1f} x {z:.1f} mm, "
                f"volume {ch.volume_mm3(solid):.0f} mm^3"
            )
            for fmt in ("step", "stl", "gltf"):
                exporter = EXPORTERS[fmt]()
                exporter.metadata = provenance
                path = exporter.output_path(f"cyberdeck_{name}")
                obj = gltf_special.get(name, solid) if fmt == "gltf" else solid
                exporter.export(obj, path)
                if path.exists() and not apply_fs_metadata(provenance, path):
                    print(f"[pipeline] warning: could not write fs metadata for {path}")
                print(f"[pipeline] exported {name} -> {path}")
        if metrics_path is not None:
            metrics["_pipeline"] = {
                "layout": self.layout_name,
                "targets": sorted(selected),
            }
            Path(metrics_path).write_text(
                json.dumps(metrics, indent=2, sort_keys=True)
            )
            print(f"[pipeline] wrote metrics -> {metrics_path}")

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
            Comma-separated build targets (default ``"all"``): ``assembly``,
            ``assembly_opened``, ``chassis`` (+``_left/_right``),
            ``screen_lid`` (+``_left/_right``), ``slide``,
            ``keyboard_plate``, ``display``, ``components``. Per-component:
            ``comp:<role>``.
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

        if self.layout_name == "slider":
            self._run_slider_data(
                config, components, placements, steps, targets,
                ignore_validation, metrics_path,
            )
            return



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
        description="Parametric slider cyberdeck CAD generator (the slider CAD path is in progress; the data stage is complete).",
    )
    parser.add_argument(
        "--config",
        default="config/default.yaml",
        help="path to the default YAML configuration",
    )
    parser.add_argument(
        "--layout",
        default="slider",
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
             "Buckets: all, assembly, assembly_opened, chassis, screen_lid, "
             "slide, keyboard_plate, display, components. "
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
