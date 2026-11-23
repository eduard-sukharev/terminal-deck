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
from collections.abc import Callable
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
from utilities.build_cache import CACHE_FILE_NAME
from utilities.config_loader import Config, load_config
from utilities.file_metadata import apply as apply_fs_metadata
from utilities.validation import ValidationReport, run_all


#: Set from ``--verbose`` in ``main()``: informational messages print only
#: when True. Errors and warnings always print; a failed report prints its
#: full detail regardless. A fully passing quiet run prints nothing.
_VERBOSE = False


def _info(message: str) -> None:
    """Informational pipeline message — shown only with ``--verbose``."""
    if _VERBOSE:
        print(message)


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
            # The plate is the Well Cutout + one wall per side (ADR-0014), so
            # the keyboard model needs the resolved wall thickness and the
            # config-derived wobble/thickness, not just the raw YAML section.
            "wall_thickness": cfg.wall_thickness,
            "plate": {
                **(cfg.keyboard.plate or {}),
                "thickness": cfg.keyboard.plate_thickness,
                "wobble": cfg.keyboard.plate_wobble,
            },
            "mounting": cfg.keyboard.mounting or {},
            # ADR-0006: seam-pin sites and spec for the plate's row-jogging Seam.
            # The sites are the pocket-centre Y values (plate-local), validated
            # by slide-seam-pin-fit/clear; the pin spec comes from config.seam_pin.
            "seam_pin_sites": tuple(
                cfg.slide.seam_pin_sites.get("keyboard_plate", ())
            ),
            "seam_pin": cfg.seam_pin,
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
            # External accessories: the battery and the USB hub live on the
            # accessory rail, not in the chassis. Their models are retained so
            # they can be exported on their own (comp:<role>), but they are not
            # placements.
            "battery": Battery(cfg.hardware),
            "usb_breakout": UsbBreakout(cfg.hardware),
        }

    def place_layout(self, components: dict):
        layout = make_layout(
            self.layout_name, components,
            config=self.config, recipe_path=self.recipe_path,
        )
        return layout

    def validate(self, placements, shell_depths=None, openings=None):
        """Run the placement validation suite and return its report."""
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
        return report

    def _run_slider_data(
        self,
        config,
        components,
        placements,
        steps: str,
        targets: str,
        ignore_validation: bool,
        metrics_path: str | None = None,
        use_cache: bool = True,
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
        _info(
            f"[pipeline] placement envelope: {size.width:.1f} x "
            f"{size.depth:.1f} x {size.height:.1f} mm "
            "(component extent incl. walls; the device envelope is the slide "
            "budget below)"
        )

        budget = compute_slide_budget(config, components)
        if _VERBOSE or not budget.within_face_limit:
            print("[pipeline] slide budget:")
            print(budget.summary())

        # The plate carries the Well's mounting pattern (ears, notches, M2
        # clearance holes) -- one source, derived from the same budget the Deck
        # uses and the keyboard's own placement (its 180 deg turn is the plate's
        # frame, ADR-0014/issue #19).
        from geometry.well_mounts import plate_cutouts, well_mounts

        keyboard = components["keyboard"]
        keyboard_placement = next(
            p for p in placements if p.component is keyboard
        )
        # The plate's switch/stabilizer openings are real areas the ears must
        # clear and the sheet must stay connected around, so the production
        # pattern gets them (ADR-0014 review).
        keyboard.set_well_mounts(
            well_mounts(
                config,
                budget,
                placement=keyboard_placement,
                cutouts=plate_cutouts(keyboard.plate_model()),
            )
        )

        report = run_slider_checks(
            budget, config, placements, mounts=keyboard.well_mounts
        )
        if report.passed and not _VERBOSE:
            # Quiet success: nothing but the warnings.
            for message in report.warnings:
                print(f"  [warn] {message}")
        else:
            print("[pipeline] slider validation:")
            print(report.summary(verbose=_VERBOSE))
        if not report.passed and not ignore_validation:
            raise SystemExit(
                "[pipeline] aborted: slider validation failed "
                "(pass --ignore-validation to inspect a rejected layout)"
            )

        if steps == "data":
            return
        self._run_slider_cad(
            config, components, placements, budget, targets,
            ignore_validation, metrics_path, use_cache,
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
        use_cache: bool = True,
    ) -> None:
        """Build and export the first-generation slider case (issue #3)."""
        from assemblies.assembly import Assembly, select_placements
        from case.chassis import Chassis
        from case.screen_lid import ScreenLid
        from case.slider_frame import SliderFrame
        from components.accessory_rail import (
            build_rail,
            build_rail_washer,
            place_rail,
            place_rail_washer,
        )
        from components.slide import (
            build_bearing_clamp_halves,
            build_guide_rod,
            build_linear_bearing,
            build_rod_clamp,
        )
        from exports import EXPORTERS, GENERATED_DIR
        from geometry.rail_mounts import rail_mounts
        from utilities import cad_helpers as ch
        from utilities.build_cache import BuildCache

        ch.require_cad()
        frame = SliderFrame.from_data(config, budget, components, placements)
        wall = config.wall.thickness
        split = config.slide.split

        if "keyboard_plate" in split:
            print(
                "[pipeline] warning: slide.split.keyboard_plate is retired and "
                "ignored; the plate splits between keys along the Seam its "
                "layout derives (ADR-0014, #9)"
            )
        for retired in ("chassis", "screen_lid"):
            if retired in split:
                print(
                    f"[pipeline] warning: slide.split.{retired} is retired "
                    "(ADR-0015); split the Tray and the Deck (or the Bezel and "
                    "the Back plate) separately"
                )

        def sections_of(name: str, shape, depth: float):
            from geometry.split import split_part

            spec = split.get(name)
            if spec is None:
                raise SystemExit(
                    f"[pipeline] aborted: config.slide.split has no {name!r} entry"
                )
            pieces = split_part(shape, spec, depth, wall)
            if len(pieces) != 2:
                raise SystemExit(
                    f"[pipeline] aborted: {name} split into {len(pieces)} "
                    "Sections; this build exports two per part"
                )
            return pieces

        # Every solid is built on demand and memoised, so a target builds only
        # what it exports: `make chassis` never touches the screen lid,
        # `make screen_lid` never touches the chassis, and a per-piece target
        # (chassis_tray, screen_lid_bezel, ...) builds just that piece and its
        # Sections.
        memory: dict[str, object] = {}

        def once(key: str, build_fn):
            if key not in memory:
                memory[key] = build_fn()
            return memory[key]

        assembly = Assembly(placements, config)
        role_map = {id(component): role for role, component in components.items()}
        chassis_roles = ("keyboard", "sbc", "controller")
        lid_roles = ("display", "driver")
        chassis_parts = select_placements(
            placements,
            {components[r] for r in chassis_roles if r in components},
        )
        lid_parts = select_placements(
            placements, {components[r] for r in lid_roles if r in components}
        )

        # --- chassis pieces ---------------------------------------------------
        def chassis_obj():
            return once("_chassis", lambda: Chassis(config, frame))

        def tray():
            return once("chassis_tray", lambda: chassis_obj().build_tray())

        def deck():
            return once("chassis_deck", lambda: chassis_obj().build_deck())

        def tray_sections():
            return once(
                "_tray_sections",
                lambda: sections_of("chassis_tray", tray(), frame.depth),
            )

        def deck_sections():
            return once(
                "_deck_sections",
                lambda: sections_of("chassis_deck", deck(), frame.depth),
            )

        def chassis_shell():
            return once(
                "_chassis_shell", lambda: ch.make_compound([tray(), deck()])
            )

        # --- screen lid pieces ------------------------------------------------
        def lid_obj():
            return once("_lid", lambda: ScreenLid(config, frame))

        def bezel():
            return once("screen_lid_bezel", lambda: lid_obj().build_bezel())

        def back():
            return once("screen_lid_back", lambda: lid_obj().build_back())

        def bezel_sections():
            return once(
                "_bezel_sections",
                lambda: sections_of(
                    "screen_lid_bezel", bezel(), frame.lid_height
                ),
            )

        def back_sections():
            return once(
                "_back_sections",
                lambda: sections_of("screen_lid_back", back(), frame.lid_height),
            )

        def lid_shell():
            return once("_lid_shell", lambda: ch.make_compound([bezel(), back()]))

        def guard():
            # The FPC guard is a separate printed plate, bonded to the
            # display's back: build it in the display's frame, then place it on
            # the panel.
            return once(
                "fpc_guard",
                lambda: ch.translate(
                    lid_obj().build_fpc_guard(),
                    frame.display_x,
                    frame.display_y,
                    frame.display_z0,
                ),
            )

        # --- guide hardware ---------------------------------------------------
        def rod_clamp_part():
            return once(
                "rod_clamp",
                lambda: build_rod_clamp(
                    config.slide.rod.diameter,
                    frame.rod_raise,
                    frame.rod_clamp_len,
                    frame.rod_clamp_height,
                    frame.rod_clamp_width,
                    config.slide.rod_clamp.screw,
                    frame.rod_clamp_screw_span,
                    config.slide.rod_clamp.set_screw,
                    config.slide.rod_clamp.bottom_edge_chamfer,
                    config.slide.rod_clamp.general_chamfer,
                    config.slide.rod_clamp.top_edge_chamfer,
                ),
            )

        def bearing_clamp_halves_part():
            cc = config.slide.bearing_clamp
            return once(
                "bearing_clamp_halves",
                lambda: build_bearing_clamp_halves(
                    frame.bearing_outer,
                    frame.clamp_width,
                    frame.rod_raise,
                    frame.clamp_len,
                    frame.foot_thickness,
                    frame.foot_top,
                    cc.crown_wall,
                    cc.screw,
                    cc.insert,
                    frame.clamp_span,
                    cc.screw_length,
                    cc.seat_floor,
                    config.material.minimum_feature,
                    cc.edge_chamfer,
                    config.edges.bed_chamfer,
                    cc.corner_chamfer,
                ),
            )

        def bearing_clamp_part():
            # Assembled reference (the two halves as one compound); the
            # printable parts are the separate `bearing_clamp_lower/upper`.
            return once(
                "bearing_clamp",
                lambda: ch.make_compound(list(bearing_clamp_halves_part())),
            )

        def rods():
            return once(
                "_rods",
                lambda: [
                    ch.translate(
                        build_guide_rod(
                            config.slide.rod.diameter, frame.rod_length
                        ),
                        side * frame.rod_x,
                        frame.rod_y,
                        frame.rod_z,
                    )
                    for side in (-1, 1)
                ],
            )

        def rod_clamps():
            return once(
                "_rod_clamps",
                lambda: [
                    ch.translate(
                        rod_clamp_part(),
                        side * frame.rod_x,
                        center_y,
                        frame.panel_inner_z,
                    )
                    for side in (-1, 1)
                    for center_y in frame.rod_clamp_y
                ],
            )

        def bearings():
            return once(
                "_bearings",
                lambda: [
                    ch.translate(
                        build_linear_bearing(
                            frame.bearing_outer,
                            frame.bearing_bore,
                            frame.bearing_length,
                        ),
                        side * frame.rod_x,
                        frame.clamp_center_y,
                        frame.rod_z,
                    )
                    for side in (-1, 1)
                ],
            )

        def bearing_clamps():
            return once(
                "_bearing_clamps",
                lambda: [
                    ch.translate(
                        bearing_clamp_part(),
                        side * frame.rod_x,
                        frame.clamp_center_y,
                        frame.panel_inner_z,
                    )
                    for side in (-1, 1)
                ],
            )

        def rods_compound():
            return once("_rods_compound", lambda: ch.make_compound(rods()))

        def rod_clamps_compound():
            return once(
                "_rod_clamps_compound", lambda: ch.make_compound(rod_clamps())
            )

        def bearings_compound():
            return once("_bearings_compound", lambda: ch.make_compound(bearings()))

        def bearing_clamps_compound():
            return once(
                "_bearing_clamps_compound",
                lambda: ch.make_compound(bearing_clamps()),
            )

        def fixed_hardware():
            return once(
                "_fixed_hardware",
                lambda: ch.make_compound(bearings() + bearing_clamps()),
            )

        def slide():
            return once(
                "slide",
                lambda: ch.make_compound(
                    rods() + rod_clamps() + bearings() + bearing_clamps()
                ),
            )

        # --- sub-assemblies ---------------------------------------------------
        def chassis_with_parts():
            return once(
                "chassis",
                lambda: ch.make_compound(
                    [chassis_shell(), rails_compound(), rail_washers_compound()]
                    + [assembly.build_subset([p]) for p in chassis_parts]
                ),
            )

        def lid_with_parts():
            return once(
                "screen_lid",
                lambda: ch.make_compound(
                    [
                        lid_shell(),
                        rods_compound(),
                        rod_clamps_compound(),
                        guard(),
                    ]
                    + [assembly.build_subset([p]) for p in lid_parts]
                ),
            )

        def assembly_solid():
            return once(
                "assembly",
                lambda: ch.make_compound(
                    [chassis_with_parts(), lid_with_parts(), fixed_hardware()]
                ),
            )

        def assembly_opened():
            return once(
                "assembly_opened",
                lambda: ch.make_compound(
                    [
                        chassis_with_parts(),
                        ch.translate(lid_with_parts(), 0.0, budget.travel, 0.0),
                        fixed_hardware(),
                    ]
                ),
            )

        def display():
            return once(
                "display",
                lambda: ch.make_compound(
                    [assembly.build_subset([p]) for p in lid_parts]
                ),
            )

        # --- accessory rail ---------------------------------------------------
        def rail_pattern():
            return once(
                "_rail_mounts", lambda: rail_mounts(config, frame.chassis_joint)
            )

        def rail_part():
            return once("rail", lambda: build_rail(rail_pattern()))

        def rail_washer_part():
            return once(
                "rail_washer", lambda: build_rail_washer(rail_pattern())
            )

        def rails():
            return once(
                "_rails",
                lambda: [
                    place_rail(rail_pattern(), side) for side in (-1, 1)
                ],
            )

        def rail_washers():
            return once(
                "_rail_washers",
                lambda: [
                    place_rail_washer(rail_pattern(), station)
                    for station in rail_pattern().stations
                ],
            )

        def rails_compound():
            return once("_rails_compound", lambda: ch.make_compound(rails()))

        def rail_washers_compound():
            return once(
                "_rail_washers_compound",
                lambda: ch.make_compound(rail_washers()),
            )

        # --- keyboard plate ---------------------------------------------------
        def plate():
            return once(
                "keyboard_plate", lambda: components["keyboard"].build_plate()
            )

        def plate_sections():
            def build():
                model = components["keyboard"].plate_model()
                _info(
                    "[pipeline] keyboard plate Seam, front to back: "
                    + " -> ".join(
                        f"({x:.2f}, {y:.2f})"
                        for x, y in model.seam.polyline(model.metadata.height)
                    )
                )
                return components["keyboard"].plate_sections()

            return once("_plate_sections", build)

        parts = {
            "assembly": assembly_solid,
            "assembly_opened": assembly_opened,
            "chassis": chassis_with_parts,
            "chassis_left": lambda: once(
                "chassis_left",
                lambda: ch.make_compound(
                    [tray_sections()[0], deck_sections()[0]]
                ),
            ),
            "chassis_right": lambda: once(
                "chassis_right",
                lambda: ch.make_compound(
                    [tray_sections()[1], deck_sections()[1]]
                ),
            ),
            "chassis_tray": tray,
            "chassis_tray_left": lambda: tray_sections()[0],
            "chassis_tray_right": lambda: tray_sections()[1],
            "chassis_deck": deck,
            "chassis_deck_left": lambda: deck_sections()[0],
            "chassis_deck_right": lambda: deck_sections()[1],
            "screen_lid": lid_with_parts,
            "screen_lid_left": lambda: once(
                "screen_lid_left",
                lambda: ch.make_compound(
                    [bezel_sections()[0], back_sections()[0]]
                ),
            ),
            "screen_lid_right": lambda: once(
                "screen_lid_right",
                lambda: ch.make_compound(
                    [bezel_sections()[1], back_sections()[1]]
                ),
            ),
            "screen_lid_bezel": bezel,
            "screen_lid_bezel_left": lambda: bezel_sections()[0],
            "screen_lid_bezel_right": lambda: bezel_sections()[1],
            "screen_lid_back": back,
            "screen_lid_back_left": lambda: back_sections()[0],
            "screen_lid_back_right": lambda: back_sections()[1],
            "slide": slide,
            "fpc_guard": guard,
            "rod_clamp": rod_clamp_part,
            "bearing_clamp": bearing_clamp_part,
            "bearing_clamp_lower": lambda: bearing_clamp_halves_part()[0],
            "bearing_clamp_upper": lambda: bearing_clamp_halves_part()[1],
            "rail": rail_part,
            "rail_washer": rail_washer_part,
            "keyboard_plate": plate,
            "keyboard_plate_left": lambda: plate_sections()[0],
            "keyboard_plate_right": lambda: plate_sections()[1],
            "display": display,
        }

        tokens = [token.strip() for token in targets.split(",") if token.strip()]
        if "all" in tokens:
            tokens = list(parts) + ["components"]

        # Selection is by name; the solid is only built when the target is
        # stale (see the export loop below), so an unchanged piece costs nothing.
        builders: dict[str, Callable[[], object]] = {}
        for token in tokens:
            if token == "components":
                # Only the components the slider actually places. The battery
                # is an external accessory and the cable plugs are not modelled
                # in this generation; they stay reachable via comp:<role>.
                placed_roles = {
                    "display", "driver", "keyboard", "sbc", "controller",
                }
                for role, component in components.items():
                    if role not in placed_roles:
                        continue
                    builders[f"component_{role}"] = (
                        lambda c=component: c.build()
                    )
            elif token.startswith("comp:"):
                role = token.split(":", 1)[1]
                if role not in components:
                    raise ValueError(f"unknown component role {role!r}")
                component = components[role]
                builders[f"component_{role}"] = lambda c=component: c.build()
            elif token in parts:
                builders[token] = parts[token]
            else:
                raise ValueError(
                    f"unknown slider target {token!r}; expected one of "
                    f"{sorted(parts)} or 'components'"
                )

        # Sections must fit the printer; the whole part is exported for
        # reference but is not printable across X.
        printable = (
            "fpc_guard",
            "bearing_clamp_lower",
            "bearing_clamp_upper",
            "rail",
            "rail_washer",
            "chassis_tray_left",
            "chassis_tray_right",
            "chassis_deck_left",
            "chassis_deck_right",
            "screen_lid_bezel_left",
            "screen_lid_bezel_right",
            "screen_lid_back_left",
            "screen_lid_back_right",
            "keyboard_plate_left",
            "keyboard_plate_right",
        )
        volume = (220.0, 220.0, 256.0)

        # The four assembled targets get a per-component coloured glTF; every
        # other target exports its solid as-is.
        def gltf_shape(name: str, solid):
            if name == "assembly":
                return assembly.build_colored(
                    placements=placements,
                    role_map=role_map,
                    extra_parts=[
                        ("chassis_tray", tray()),
                        ("chassis_deck", deck()),
                        ("screen_lid_bezel", bezel()),
                        ("screen_lid_back", back()),
                        ("guide_rod", rods_compound()),
                        ("rod_clamp", rod_clamps_compound()),
                        ("fpc_guard", guard()),
                        ("linear_bearing", bearings_compound()),
                        ("bearing_clamp", bearing_clamps_compound()),
                        ("accessory_rail", rails_compound()),
                        ("rail_washer", rail_washers_compound()),
                    ],
                )
            if name == "assembly_opened":
                open_transform = {
                    id(components[role]): _move_y
                    for role in ("display", "driver")
                    if role in components
                }
                return assembly.build_colored(
                    placements=placements,
                    role_map=role_map,
                    transform=open_transform,
                    extra_parts=[
                        ("chassis_tray", tray()),
                        ("chassis_deck", deck()),
                        ("screen_lid_bezel", _move_y(bezel())),
                        ("screen_lid_back", _move_y(back())),
                        ("guide_rod", _move_y(rods_compound())),
                        ("rod_clamp", _move_y(rod_clamps_compound())),
                        ("fpc_guard", _move_y(guard())),
                        ("linear_bearing", bearings_compound()),
                        ("bearing_clamp", bearing_clamps_compound()),
                        ("accessory_rail", rails_compound()),
                        ("rail_washer", rail_washers_compound()),
                    ],
                )
            if name == "chassis":
                return assembly.build_colored(
                    placements=chassis_parts,
                    role_map=role_map,
                    extra_parts=[
                        ("chassis_tray", tray()),
                        ("chassis_deck", deck()),
                        ("linear_bearing", bearings_compound()),
                        ("bearing_clamp", bearing_clamps_compound()),
                        ("accessory_rail", rails_compound()),
                        ("rail_washer", rail_washers_compound()),
                    ],
                )
            if name == "screen_lid":
                return assembly.build_colored(
                    placements=lid_parts,
                    role_map=role_map,
                    extra_parts=[
                        ("screen_lid_bezel", bezel()),
                        ("screen_lid_back", back()),
                        ("guide_rod", rods_compound()),
                        ("rod_clamp", rod_clamps_compound()),
                        ("fpc_guard", guard()),
                    ],
                )
            return solid

        def _move_y(solid):
            return ch.translate(solid, 0.0, budget.travel, 0.0)

        # A target is reused when its inputs and its three exports are unchanged:
        # nothing is built and nothing is written, so editing one piece only
        # rebuilds that piece (and the assemblies that embed it).
        cache = BuildCache(
            GENERATED_DIR / CACHE_FILE_NAME,
            reuse=use_cache and metrics_path is None,
        )
        if use_cache and metrics_path is not None:
            _info(
                "[pipeline] geometry cache disabled: --metrics needs every "
                "selected target built"
            )

        provenance = self._provenance()
        metrics: dict[str, object] = {}
        if metrics_path is not None:
            from utilities.metrics import shape_metrics

        reused = 0
        built = 0
        for name, build in builders.items():
            artifacts = [
                EXPORTERS[fmt]().output_path(f"cyberdeck_{name}")
                for fmt in ("step", "stl", "gltf")
            ]
            if cache.is_fresh(name, artifacts):
                reused += 1
                _info(f"[pipeline] {name}: unchanged, keeping its exports")
                continue

            try:
                solid = build()
            except NotImplementedError:
                continue
            if solid is None:
                continue
            built += 1

            if name in printable:
                x, y, z = ch.bounding_box_mm(solid)
                fits = (
                    x <= volume[0] + 1e-6
                    and y <= volume[1] + 1e-6
                    and z <= volume[2] + 1e-6
                )
                if fits:
                    _info(
                        f"[pipeline] {name}: {x:.1f} x {y:.1f} x {z:.1f} mm "
                        "fits the build volume"
                    )
                else:
                    print(
                        f"[pipeline] {name}: {x:.1f} x {y:.1f} x {z:.1f} mm "
                        "EXCEEDS the build volume"
                    )
                if not fits and not ignore_validation:
                    raise SystemExit(
                        "[pipeline] aborted: Section exceeds the build "
                        f"volume: {name}"
                    )

            if metrics_path is not None:
                metrics[name] = shape_metrics(solid)
            x, y, z = ch.bounding_box_mm(solid)
            _info(
                f"[pipeline] {name}: bbox {x:.1f} x {y:.1f} x {z:.1f} mm, "
                f"volume {ch.volume_mm3(solid):.0f} mm^3"
            )
            for fmt in ("step", "stl", "gltf"):
                exporter = EXPORTERS[fmt]()
                exporter.metadata = provenance
                path = exporter.output_path(f"cyberdeck_{name}")
                obj = gltf_shape(name, solid) if fmt == "gltf" else solid
                exporter.export(obj, path)
                if path.exists() and not apply_fs_metadata(provenance, path):
                    print(f"[pipeline] warning: could not write fs metadata for {path}")
                _info(f"[pipeline] exported {name} -> {path}")
            cache.record(name, artifacts)
            cache.save()

        print(
            f"[pipeline] build: {built} built, {reused} reused "
            f"({len(builders)} targets)"
        )

        if metrics_path is not None:
            metrics["_pipeline"] = {
                "layout": self.layout_name,
                "targets": sorted(builders),
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
        use_cache: bool = True,
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
            ``screen_lid`` (+``_left/_right``), ``slide``, ``fpc_guard``,
            ``rod_clamp``, ``bearing_clamp``, ``keyboard_plate``, ``display``,
            ``components``. Per-component:
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
        use_cache : bool
            Reuse a target's exports when its inputs (the pipeline sources, the
            configuration tree, the layout recipe and the modules that build
            that piece) and its three artifacts are unchanged. Set this to
            ``False`` to force a full rebuild (``--no-cache`` / ``make
            rebuild``); it is also ignored when ``metrics_path`` is set, since
            the metrics need every selected target built.
        """
        config = self.load_config()
        _info(f"[pipeline] config: {self.config_path} ({self.topics})")
        _info(f"           layout: {self.layout_name}")
        _info(f"           wall_thickness: {config.wall_thickness} mm")

        components = self.load_components()
        _info(f"[pipeline] components: {', '.join(components)}")

        layout = self.place_layout(components)
        placements = layout.placements()
        _info(f"[pipeline] placements: {len(placements)}")

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
        vreport = self.validate(placements, shell_depths, openings)
        if vreport.passed and not _VERBOSE:
            # Quiet success: nothing but the warnings.
            for message in vreport.warnings:
                print(f"  [warn] {message}")
        else:
            print("[pipeline] placement validation:")
            print(vreport.summary(verbose=_VERBOSE))

        if isinstance(layout, ConstraintLayout):
            creport = layout.constraint_report()
            if creport is not None:
                if not (creport.passed and not _VERBOSE):
                    print("[pipeline] constraint resolution:")
                    print(creport.summary(verbose=_VERBOSE))
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
            if comp_errors or _VERBOSE:
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
                ignore_validation, metrics_path, use_cache,
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
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="print informational build output (config header, per-check "
             "report lines, per-target export lines). Without it only "
             "errors and warnings are shown; a fully passing run is "
             "silent (exit code 0).",
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="rebuild every selected target even when its inputs and exports "
             "are unchanged (the incremental build cache lives in "
             f"generated/{CACHE_FILE_NAME}).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    global _VERBOSE
    args = _parse_args(argv or sys.argv[1:])
    _VERBOSE = args.verbose
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
            use_cache=not args.no_cache,
        )
    except NotImplementedError as exc:
        print(f"[pipeline] CAD stage not yet implemented: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
