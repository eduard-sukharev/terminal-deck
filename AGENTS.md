# AGENTS.md

This file provides guidance to AI coding agents (Claude Code, etc.) when working with code in this repository.

Parametric **slider** cyberdeck CAD generator (build123d), for field debugging
of 3D printers. Target hardware: Orange Pi Zero 2W SBC, 8.8" 1920x480 HDMI
display, 40% Cherry-MX-compatible RP2040/QMK keyboard. The screen lid slides
along the face over the chassis to reveal the keyboard (ADR-0009; the clamshell
is retired). This is **not** a maker platform — no GPIO, sensors, LEDs, or
decorative elements. Priorities: robustness, serviceability, printability,
parametricity, reusability.

> **Migration status.** `docs/form_factor.md`, `CONTEXT.md` and ADR-0009 define
> the slider. The Python case code still builds the retired clamshell until the
> slider skeleton lands (next step); the target names below are what that
> skeleton implements. Do not add new clamshell features.

## Build volume

Target printer build volume: **220 × 220 × 256 mm** (X × Y × Z). Every
printable part (chassis tray/deck, screen-lid bezel/back, keyboard plate,
bearing clamp, etc.) must fit this envelope in its intended print orientation;
if a part would exceed it in every viable orientation, split it into joined
printable pieces (alignment features + fasteners) rather than silently
exceeding the limit. See `.agents/skills/cad/references/fdm-printing.md` for
the full FDM manufacturability ruleset (wall thickness, clearances, overhangs,
boss design, build-volume checks).

## Environment (critical)

- **Use the `cyberdeck` conda env** — the base conda env is Python 3.7 and
  fails to import (`typing.Final` missing). Create it once, then activate:
  ```bash
  conda create -n cyberdeck python=3.12 && conda activate cyberdeck
  pip install -r requirements.txt
  ```
- **Backend:** build123d (ADR 0002). Core components are ported; the case
  parts are rebuilt for the slider per `docs/form_factor.md`.

## Commands

```bash
make data                    # data layer only (config → components → layout → validation)
make all                     # full CAD + exports (STEP/STL/SVG/glTF to generated/)
make test                    # pytest
make check                   # py_compile all modules (run after `make data`)
make clean                   # remove generated files and __pycache__

# equivalent direct invocations
python main.py --config config/default.yaml --layout slider --steps data
python main.py --steps all
python main.py --steps all --targets display                 # display sub-assembly only (fast)
python main.py --steps all --targets display,chassis         # selected targets
python -m pytest tests/test_layouts.py            # single test file
python -m pytest tests/test_layouts.py::test_name -v   # single test
```

`--steps data` runs config → components → layout → validation and prints the
report; no CAD library needed. `--steps all` additionally sizes the
chassis/lid, bearing clamps and cutouts, and builds+exports the assembly,
chassis and screen lid.

**Edge treatment runs per Section** (after the lossless rejoin check): OCC can
segfault on a chamfer, so `cad_helpers` runs each attempt in a child process
(`utilities/_cad_worker.py`); a failing edge is skipped with a SOFT warning.

**Selective build targets** (`--targets`, comma-separated), target set:

- `assembly` — full union of all placements
- `chassis` — combined chassis: chassis_tray + keyboard + chassis_deck
- `chassis_tray` — floor, walls, ribs, vents, connector cutouts, Parting plane
- `chassis_deck` — top surface: keyboard Well, Bearing clamps, Rear band
- `screen_lid` — combined screen lid: bezel + display + back panel
- `screen_lid_bezel` — inverted-tray front with the glass opening
- `screen_lid_back` — flat back panel with the guide-rod C-channels
- `keyboard_plate` — the switch plate
- `slide` — guide rods, linear bearings, Bearing clamps, drag-chain anchors
- `display` — LCD panel + HDMI driver combined (the sub-assembly, fast)
- `components` — all per-component debug STLs
- `comp:<role>` — a single component's raw STL (e.g. `comp:driver`, `comp:display`)
- `all` — every target above (default)

Every wide part is split into **two** Sections along X and exported as Sections
alongside the whole part (ADR 0003, superseding 0001): `<part>_left` /
`<part>_right` for `chassis_tray`, `chassis_deck`, `screen_lid_bezel`,
`screen_lid_back`, `keyboard_plate`. Seams come from the per-part `split:`
section of `config/default.yaml` (`sections`, `x`, `style`, `step`, `steps`) and
the run fails if a Section is disconnected, doesn't rejoin, exceeds the build
volume or has no flat bed face. Naming a Section on its own (e.g.
`--targets chassis_tray_left`) exports only that Section; naming the part or a
bucket containing it exports all of them.
Makefile convenience targets: `make display`, `make chassis`, `make chassis_tray`,
`make chassis_deck`, `make screen_lid`, `make screen_lid_bezel`,
`make screen_lid_back`, `make slide`, `make assembly`, `make components`,
`make build TARGETS=...`.

## Architecture

Pipeline: `Component -> Placement -> Assembly -> Enclosure -> Features -> Export`.
Everything derives from reusable components; every dimension originates from
configuration, a measured component, or calculated geometry — never
intuition. Wire-up lives in `main.py` (`BuildPipeline`, `run()`).

- **Data layer (implemented, no CAD library needed):** `components/base.py`
  (`BoundingBox`/`Hole`/`Connector`/`Keepout` + `Component` ABC),
  `utilities/config_loader.py`, `utilities/fasteners.py`,
  `utilities/validation.py`, `layouts/*`, `assemblies/assembly.py`,
  `routing/cable_routing.py`, and the `keyboard/` package (KLE → layout →
  switch/stabilizer libraries → plate geometry model + its own validation).
- **CAD generation (required build123d):** `Assembly.build()` unions component
  solids at their placements; `case.chassis.Chassis.build_tray()` and
  `build_deck()` produce the Tray (floor, walls, bosses, ribs, vents, cutouts,
  Parting plane) and the Deck (keyboard Well, Rear band, Bearing clamps);
  `case.chassis_fastening.py` holds their CAD-free fastening data (Parting
  plane, Deck columns, Seam bands/lugs, bearing-clamp seats);
  `case.screen_lid.ScreenLid.build_bezel()` and `build_back()` produce the
  inverted-tray front (glass opening, panel and driver in the tray) and the flat
  back panel (guide-rod C-channels); `components/slide.py` describes the two
  LM…LUU guide rods, their bearings and the drag chain from `config/slide.yaml`
  (rod length, bearing size, clamp, travel, channel); `geometry/*` hold the
  primitives.
- `utilities/cad_helpers.py` is the **only** CAD adapter (build123d); it imports
  lazily so the data layer stays importable without a CAD library. Geometry
  modules must go through it, not `import build123d` directly.
- `exports/` exporters delegate to build123d exporters (STEP/STL/SVG/glTF).
  The glTF exporter (`exports/export_gltf.py`) takes a
  `cad_helpers.ColoredAssembly` (built by `Assembly.build_colored()`, colors
  from `utilities/colors.py`), not a single fused solid.
- **Assemblies are always also rendered to glTF with one color per
  component.** Every component role needs its own opaque entry in
  `utilities/colors.py` (`tests/test_colors.py` fails otherwise); use
  transparency only where it helps you see inside — currently the chassis and
  lid shells. Any new assembly or build target that groups parts must go
  through `Assembly.build_colored()` and export glTF too.

### Layout system

The single layout, `slider`, is **constraint-based**: it declares placements
as data rather than code.

```
config/layouts/slider.yaml      the recipe (the only one)
  → layouts/recipe_loader.py    parses YAML into Constraint dataclasses
  → layouts/constraints.py      constraint types (EdgeAlignment, CenteredOn,
                                 FixedPosition, CenteredGroup, Clearance,
                                 ZStack, SharePlane, RegionConstraint,
                                 CablePath, FootprintMatch, DeckMount,
                                 RelativePlacement, TargetEnvelope) — pure
                                 data, no logic
  → layouts/composer.py         LayoutComposer resolves each constraint in
                                 recipe order via a registered resolver,
                                 accumulates placements, and produces a
                                 ConstraintReport (HARD violations fail the
                                 build; SOFT warn; GOAL is a reported metric)
  → layouts/resolvers/*.py      one resolver per constraint kind
```

Most placements are derived from component sizes and config; the recipe's
`fixed_position` entries are the deliberate manual overrides, each annotated
with why it cannot be derived.

Layouts contain no CAD, only placements. `layouts/layout_recipe.py` is the
adapter that runs a recipe through the composer and returns placements;
`layouts/layout_constrained.py` is its composer-backed base class.

### Keyboard subsystem

`keyboard/` is a self-contained geometry generator (see
`docs/keyboard_architecture.md`) with **no dependency on cyberdeck code** —
it must stay importable without a CAD library. The cyberdeck adapters
(`components/keyboard_plate.py`, `components/rp2040_keyboard.py`) extrude its
model during the CAD pass.

Data flow: KLE JSON → `keyboard/layout/kle_parser.py` → internal
`KeyboardLayout`/`Key` model → `keyboard/switches/kb_builder.py` +
`keyboard/stabilizers/kb_builder.py` → `keyboard/geometry/plate.py` →
solid, consumed by the cyberdeck assembly. Physical dimensions live in
`keyboard/reference/*.yaml`, never hardcoded in source. Every generated plate
is checked by `keyboard/validation.py`.

## Conventions (from `docs/design_spec.md` — do not violate)

- **No magic numbers.** Every dimension comes from config, a measured
  component, or calculated geometry. Unmeasured values carry
  `# TODO: measure`.
- Units: mm always. Coordinates: +X right, +Y along the slide (toward the
  screen end), +Z up (thickness); origin = centre of the chassis footprint on
  the table plane. Never redefine origins.
- `wall_thickness = config.wall.thickness` is the single wall parameter.
- Layouts contain **no CAD** — only placements.
- Slide math lives in `components/slide.py`, cable routing in
  `routing/cable_routing.py`, fasteners in `utilities/fasteners.py` — never
  recreated inline.
- Component sizes/holes are verified against real datasheets (see
  `docs/component_spec.md`); SBC connector edge positions are user-calibrated
  measurements recorded in `components/orange_pi_zero2w.py`.

## Config

`config/default.yaml` is merged with `display.yaml`, `keyboard.yaml`,
`hardware.yaml`, `slide.yaml` (topic files override).
`config/layouts/slider.yaml` holds the constraint recipe for the `slider`
layout. `utilities/config_loader.py` maps YAML to frozen dataclasses; adding
a YAML key usually requires adding a field to the matching dataclass.

The face is flat — `config.deck.slope` and the clamshell's sloped-deck
machinery are gone. `config.slide` holds the purchased linear guide (rod
diameter/length, bearing model, clamp, travel margin, chain pitch/width/bend
radius); the build checks the chosen combination against the 140 mm face-height
budget.

Gotchas:

- **The face-height budget is the binding constraint.** `travel + bearing
  length + end supports + lid bezel ≤ 140`. Travel is the keyboard's front
  offset + depth + open clearance (≈ 93), not the keyboard depth (77.75). One
  bearing per rod; a second one breaks the budget.
- The keyboard is the tallest content along the face: its Well position sets
  the travel. The SBC and controller sit **under** the raised keyboard plate,
  in the chassis thickness; they must not add face height.
- The lid's flat back slides over the keycaps: the Well sets that clearance.
  A keycap standing above the Deck is a collision over the whole travel.
- The guide rods live in the lid's side walls (C-channel); the Bearing clamps
  stand on the Deck behind the keyboard and enter the channel through a slot.
  Neither the clamp nor the rod may protrude outside the closed envelope.
- **Components must be centered on their origin in XY and run `[0, height]`
  in Z** (`Placement.box` / `z_bounds` assume it).
- A single bounding box per component only reports where it *isn't* solid as a
  coarse yes/no. Two examples that needed slicing: the keyboard's plate is
  sliced along its depth so a tilted volume isn't attributed to every position
  at once (see `_occupied_volume_slices`); `Battery` slices each cylinder
  along its round axis. The battery is external in the slider, but the model
  stays for the accessory pack.
- `layouts.resolvers.clearance.ClearanceResolver` is a true 3D
  separating-axis test. Calibrate placements against the resolver itself, not
  an independent approximation.
- The screen lid is the only moving part; its sweep must be checked over the
  whole travel (closed → open), not just at the end poses.
- The drag chain is a printed accessory whose channel and anchors are in the
  shell: keep the minimum bend radius and the channel clear over the travel.
- The battery is **external** on an accessory rail; do not grow the chassis
  envelope for it. The side walls carry square-nut pockets for the
  user-supplied picatinny rails; the rails are not printed.

## Docs

`CONTEXT.md` (domain glossary), `docs/form_factor.md` (agreed shape),
`docs/adr/` (decision records), `docs/reference/` (reference images),
`docs/central-unit-slider.md` (source reference measurements and the 140 mm
trim experiment).

`docs/design_spec.md` (conventions/philosophy), `docs/coordinate_system.md`,
`docs/component_spec.md` (datasheet-verified dimensions), `docs/cad_api.md`,
`docs/keyboard_architecture.md` (full keyboard subsystem spec).

## Tools

Use fff and codegraph MCPs for navigating the codebase.
Use ripgrep's `rg` instead of regular `grep`.

## Commits

When asked to commit, agents commit **without signing**: pass `--no-gpg-sign`
to `git commit`.

## Agent skills

### Issue tracker

GitHub Issues on `eduard-sukharev/terminal-deck`, via the `gh` CLI. See `docs/agents/issue-tracker.md`.

### Domain docs

Single-context: `CONTEXT.md` plus `docs/adr/` at the repo root. See `docs/agents/domain.md`.
