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
import sys
from dataclasses import asdict
from pathlib import Path

from components.display_88 import Display88
from components.hdmi_driver import HdmiDriver
from components.orange_pi_zero2w import OrangePiZero2W
from components.rp2040_keyboard import Rp2040Keyboard
from components.usb_breakout import UsbBreakout
from layouts import make_layout
from utilities.config_loader import Config, load_config
from utilities.validation import run_all


class BuildPipeline:
    """Drives a complete cyberdeck build from configuration."""

    def __init__(
        self,
        config_path: str | Path = "config/default.yaml",
        layout_name: str = "default",
        topics: tuple[str, ...] = ("display", "keyboard", "hardware"),
    ) -> None:
        self.config_path = Path(config_path)
        self.layout_name = layout_name
        self.topics = topics
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
            "controller": cfg.keyboard.controller or {},
        }
        return {
            "display": Display88(display_cfg),
            "driver": HdmiDriver(display_cfg),
            "keyboard": Rp2040Keyboard(keyboard_cfg),
            "sbc": OrangePiZero2W(cfg.hardware),
            "usb_breakout": UsbBreakout(cfg.hardware),
        }

    def place_layout(self, components: dict):
        layout = make_layout(self.layout_name, components)
        return layout

    def validate(self, placements, shell_depths=None, openings=None) -> str:
        """Run the placement validation suite and return its summary."""
        assert self.config is not None
        max_height = max(
            (p.z + p.component.size().height for p in placements), default=0.0
        )
        report = run_all(
            placements,
            self.config,
            shell_depths=shell_depths or {},
            shell_opening=openings or [],
            max_component_height=max_height,
            lid_interior_height=max_height,
            hinge_z_span=0.0,
        )
        return report.summary()

    def run(self, steps: str = "all") -> None:
        """Execute the pipeline up to ``steps``.

        Parameters
        ----------
        steps : str
            ``"all"`` runs every stage including CAD generation and export;
            ``"data"`` stops before CAD generation.
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

        keyboard_component = components.get("keyboard")
        if keyboard_component is not None and hasattr(keyboard_component, "validate"):
            kb_errors = keyboard_component.validate()
            print(
                f"[pipeline] keyboard validation: "
                f"{len(kb_errors)} check(s): "
                f"{'PASS' if not kb_errors else 'FAIL'}"
            )
            for error in kb_errors:
                print(f"  [x ] {error}")

        if steps == "data":
            return

        from assemblies.assembly import Assembly

        assembly = Assembly(placements, config)
        size = assembly.enclosure_size()
        print(
            f"[pipeline] enclosure: {size.width:.1f} x {size.depth:.1f} x "
            f"{size.height:.1f} mm"
        )
        print(f"[pipeline] bosses: {len(assembly.bosses())}")
        print(f"[pipeline] cutouts: {len(assembly.connector_cutouts())}")

        if steps != "all":
            return

        # --- CAD stages ---------------------------------------------------
        from case.base import Base
        from case.lid import Lid
        from components.hinge import Hinge as HingePart
        from exports import EXPORTERS
        from utilities import cq_helpers

        cq_helpers.require_cq()

        hinge_cfg = {
            "diameter": config.hinge.diameter,
            "pin": config.hinge.pin,
            "wire_tunnel": config.hinge.wire_tunnel,
        }
        hinge = HingePart(hinge_cfg, wall_thickness=config.wall_thickness)

        assembly_solid = assembly.build()
        base = Base(assembly, config, hinge=hinge)
        base_solid = base.build()

        # The lid takes the display placement and the case footprint.
        display = next(p for p in placements if p.component is components["display"])
        lid = Lid(
            display.component,
            config,
            hinge=hinge,
            world_z=display.z,
            footprint=(size.width, size.depth),
        )
        lid_solid = lid.build()

        # Hinge barrels at the rear edge, centered in the gap between the base
        # cavity top and the lid underside.
        base_top = max(
            (p.z + p.component.size().height for p in placements if p.z <= 1e-6),
            default=0.0,
        ) + config.clearance.shell
        driver_height = float(config.hardware.get("driver_board", {}).get("height", 4.6))
        lid_outer_bottom = display.z - driver_height - config.clearance.shell - config.wall_thickness
        hinge_z = (base_top + lid_outer_bottom) / 2.0
        hinge_solid = hinge.build(case_depth=size.width)
        hinge_solid = cq_helpers.translate(hinge_solid, 0.0, -size.depth / 2.0, hinge_z)

        parts = {
            "assembly": assembly_solid,
            "base": base_solid,
            "lid": lid_solid,
            "hinge": hinge_solid,
        }
        for name, solid in parts.items():
            for fmt, exporter_cls in EXPORTERS.items():
                exporter = exporter_cls()
                path = exporter.output_path(f"cyberdeck_{name}")
                exporter.export(solid, path)
                print(f"[pipeline] exported {name} -> {path}")


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
        default="default",
        choices=["default", "compact"],
        help="layout definition to place components",
    )
    parser.add_argument(
        "--steps",
        default="all",
        choices=["all", "data"],
        help="'all' runs every stage; 'data' stops before CAD generation",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv or sys.argv[1:])
    pipeline = BuildPipeline(
        config_path=args.config,
        layout_name=args.layout,
    )
    try:
        pipeline.run(steps=args.steps)
    except NotImplementedError as exc:
        print(f"[pipeline] CAD stage not yet implemented: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
