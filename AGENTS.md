# AGENTS.md

This file provides guidance to AI coding agents (Claude Code, etc.) when working with code in this repository.

Parametric clamshell cyberdeck CAD generator (build123d), for field debugging of
3D printers. Target hardware: Orange Pi Zero 2W SBC, 8.8" 1920x480 HDMI
display, 40% Cherry-MX-compatible RP2040/QMK keyboard. This is **not** a maker
platform — no GPIO, sensors, LEDs, or decorative elements. Priorities:
robustness, serviceability, printability, parametricity, reusability.

## Build volume

Target printer build volume: **220 × 220 × 256 mm** (X × Y × Z). Every
printable part (base bottom/top, lid base/bezel, hinge, keyboard plate,
etc.) must fit this envelope in its intended print orientation; if a part
would exceed it in every viable orientation, split it into joined printable
pieces (alignment features + fasteners) rather than silently exceeding the
limit. See `.agents/skills/cad/references/fdm-printing.md` for the full
FDM manufacturability ruleset (wall thickness, clearances, overhangs, boss
design, build-volume checks).

## Environment (critical)

- **Use the `cyberdeck` conda env** — the base conda env is Python 3.7 and
  fails to import (`typing.Final` missing). Create it once, then activate:
  ```bash
  conda create -n cyberdeck python=3.12 && conda activate cyberdeck
  pip install -r requirements.txt
  ```
- **Backend:** build123d (CadQuery was removed, `docs/adr/0002`). The Core
  components are ported and match the geometry baseline; the case parts are
  still the pre-migration design and are rebuilt per `docs/form_factor.md`.

## Commands

```bash
make data                    # data layer only (config → components → layout → validation)
make all                     # full CAD + exports (STEP/STL/SVG/glTF to generated/)
make test                    # pytest
make check                   # py_compile all modules (run after `make data`)
make clean                   # remove generated files and __pycache__

# equivalent direct invocations
python main.py --config config/default.yaml --layout default --steps data
python main.py --steps all
python main.py --steps all --targets display                 # display sub-assembly only (fast)
python main.py --steps all --targets display,base             # selected targets
python -m pytest tests/test_layouts.py            # single test file
python -m pytest tests/test_layouts.py::test_name -v   # single test
```

`--steps data` runs config → components → layout → validation (8 checks) and
prints the report; no CAD library needed. `--steps all` additionally sizes the
enclosure/bosses/cutouts and builds+exports the assembly/base/lid/hinge
solids. Full run takes ~1 min (boolean-heavy base shell). There is one
layout, `compact` (the default); `--layout-recipe <path>` runs an arbitrary
YAML recipe file through the same composer instead of the built-in one.

**Edge treatment runs per Section** (after the lossless rejoin check): OCC can
segfault on a chamfer, so `cad_helpers` runs each attempt in a child process
(`utilities/_cad_worker.py`); a failing edge is skipped with a SOFT warning.
A full `make all` takes ~8 minutes for that reason.

**Selective build targets** (`--targets`, comma-separated):
- `assembly` — full union of all placements
- `base` — combined base assembly: base_bottom + keyboard + base_top
- `base_bottom` — base bottom tray (floor, walls, bosses, ribs, vents, cutouts)
- `base_top` — base top deck with keyboard cutout
- `lid` — combined lid assembly: lid_shell + display + lid_bezel
- `lid_shell` — lid rear shell tray
- `lid_bezel` — lid front plate with glass cutout
- `<part>_left` / `<part>_center` / `<part>_right` — one Section of
  `base_bottom`, `lid_shell` (three Sections) or `base_top`, `lid_bezel`,
  `keyboard_plate` (two; no `_center`). Every wide part is always split and
  exported as Sections alongside the whole part (ADR 0003, superseding 0001);
  Seams come from the per-part `split:` section of `config/default.yaml`
  (`sections`, `x`, `style`, `step`, `steps`) and the run fails if a Section is
  disconnected, doesn't rejoin, exceeds the build volume or has no flat bed
  face. Naming a Section on its own (e.g. `--targets lid_shell_center`)
  exports only that Section; naming the part or a bucket containing it exports
  all of them.
- `hinge` — the two purchased Torque hinges (ADR 0007), closed, on the Hinge
  axis
- `display` — LCD panel + HDMI driver combined (the sub-assembly, fast)
- `components` — all per-component debug STLs
- `comp:<role>` — a single component's raw STL (e.g. `comp:driver`, `comp:display`)
- `all` — every target above (default)

Makefile convenience targets: `make display`, `make base`, `make base_bottom`,
`make base_top`, `make lid`, `make lid_shell`, `make lid_bezel`, `make hinge`,
`make assembly`, `make components`, `make build TARGETS=...`.

## Architecture

Pipeline: `Component -> Placement -> Assembly -> Enclosure -> Features -> Export`.
Everything derives from reusable components; every dimension originates from
configuration, a measured component, or calculated geometry — never
intuition. Wire-up for the full pipeline lives in `main.py` (`BuildPipeline`,
`run()`).

- **Data layer (implemented, no CAD library needed):** `components/base.py`
  (`BoundingBox`/`Hole`/`Connector`/`Keepout` + `Component` ABC),
  `utilities/config_loader.py`, `utilities/fasteners.py`,
  `utilities/validation.py`, `layouts/*`, `assemblies/assembly.py`,
  `routing/cable_routing.py`, and the `keyboard/` package (KLE → layout →
  switch/stabilizer libraries → plate geometry model + its own validation).
- **CAD generation (implemented, requires build123d):** `Assembly.build()`
  unions component solids at their placements; `case.Base.build_bottom()` and
  `case.Base.build_top()` produce the Tray (bosses/columns/ribs/vents/cutouts,
  up to the Parting plane) and the Deck (skirt, slab, Well, keyboard cutout,
  insert bosses); `case/base_fastening.py` holds their CAD-free fastening data
  (Parting plane, Deck columns, Seam bands/lugs, hinge pads); `case.Lid.build_shell()` and
  `case.Lid.build_bezel()` produce the lid rear tray and front bezel (glass
  opening); `components/hinge.py` describes the purchased Torque hinges from config (Leaves, holes, the derived axis setback, sweep check) and builds each Leaf's pocket and insert pad, `components/cable_guard.py` the Cable guard on the Hinge axis;
  `geometry/*` hold the primitives.
- `utilities/cad_helpers.py` is the **only** CAD adapter (build123d); it imports
  lazily so the data layer stays importable without a CAD library. Geometry
  modules must go through it, not `import build123d` directly.
- `exports/` exporters delegate to build123d exporters (STEP/STL/SVG/glTF). The
  glTF exporter (`exports/export_gltf.py`) is the odd one out: it takes a
  `cad_helpers.ColoredAssembly` (built by `Assembly.build_colored()`, colors
  from `utilities/colors.py`), not a single fused solid, so components and
  the case shell keep distinct colors in the viewer.
- **Assemblies are always also rendered to glTF with one color per
  component** so parts are easy to tell apart. Every component role needs its
  own opaque entry in `utilities/colors.py` (`tests/test_colors.py` fails
  otherwise); use transparency only where it helps you see inside — currently
  the case shell (`"case"`, alpha 0.55). Any new assembly or build target that
  groups parts must go through `Assembly.build_colored()` and export glTF too,
  not just STEP/STL.

### Layout system

The single layout, `compact`, is **constraint-based**: it declares placements
as data rather than code.

```
config/layouts/clamshell.yaml   the recipe (the only one)
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
  → layouts/resolvers/*.py      one resolver per constraint kind (14
                                 resolvers) — small geometric procedures,
                                 not a general CSP solver
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
`KeyboardLayout`/`Key` model (purely descriptive, no geometry) →
`keyboard/switches/kb_builder.py` + `keyboard/stabilizers/kb_builder.py`
(geometry libraries behind a common interface — the plate generator never
knows which switch/stabilizer family it's using) →
`keyboard/geometry/plate.py` (subtracts cutouts, adds mounting holes) →
solid, consumed by the cyberdeck assembly. Physical dimensions live
in `keyboard/reference/*.yaml`, never hardcoded in source. Every generated
plate is checked by `keyboard/validation.py` (no overlapping cutouts, switch
inside outline, mounting holes inside plate, valid stabilizer spacing, etc.)
and generation fails with explicit errors rather than emitting invalid
geometry.

Stabilizer families (`keyboard/stabilizers/kb_builder.py`): `costar_compat`
(0) and `cherry` (1) each produce a single polygon per key that already
includes the switch opening (±2.3 mm notch connecting slot to cutout);
`costar` (2) produces two separate slot polygons. All are centered on the
switch center (no Y offset). Unknown per-key `_s` codes fall back to the
config default.

## Conventions (from `docs/design_spec.md` — do not violate)

- **No magic numbers.** Every dimension comes from config, a measured
  component, or calculated geometry. Unmeasured values carry
  `# TODO: measure`.
- Units: mm always. Coordinates: +X right, +Y forward, +Z up; origin = center
  of base. Never redefine origins.
- `wall_thickness = config.wall.thickness` is the single wall parameter.
- Layouts contain **no CAD** — only placements.
- Hinge math lives in `components/hinge.py`, cable routing in
  `routing/cable_routing.py`, fasteners in `utilities/fasteners.py` — never
  recreated inline.
- Component sizes/holes are verified against real datasheets (see
  `docs/component_spec.md`); SBC connector edge positions are user-calibrated
  measurements recorded in `components/orange_pi_zero2w.py`.

## Config

`config/default.yaml` is merged with `display.yaml`, `keyboard.yaml`,
`hardware.yaml` (topic files override). `config/layouts/clamshell.yaml` holds
the constraint recipe for the `compact` layout. `utilities/config_loader.py`
maps YAML to frozen dataclasses; adding a YAML key usually requires adding a
field to the matching dataclass (e.g. `Display`).

`config.deck.slope` (degrees) wedges the base: the top deck stays at its
flat height along the front edge and rises toward the rear, giving the
keyboard a typing tilt and opening rear interior height for the SBC.
`case.base.Base.deck_level_at(y)` is the one place that plane is defined; the
`deck_mount` constraint tilts parts onto it. Set it to `0` for the original
flat deck.

Gotchas around parts buried under the keyboard, or otherwise sharing XY
footprint with something above/below them:

- The switch bodies hang `Rp2040Keyboard.switch_bottom_protrusion` (7 mm)
  **below** the plate, and `occupied_volumes()` reports that band — it is
  what a buried board actually has to clear, not the plate itself. The plate
  standoff is sized for it by `plate_raise_for_buried()`, called from
  `main.py` with the SBC's real height; don't hand-set `plate_raise`.
- Components must be centered on their origin in XY and run `[0, height]` in
  Z (`Placement.box` / `z_bounds` assume it). A body modelled as extending
  *from* its origin gets collision-checked in the wrong place — see
  `components/usb_c_plug.py`, whose `reference_origin()` carries the offset
  instead.
- A single bounding box per component only reports where it *isn't* solid as
  a coarse yes/no, sliced along whichever axis actually varies. Two examples
  that needed slicing to be usable at all: the keyboard's plate is sliced
  along Y so a tilted swing doesn't get attributed to every Y position at
  once (see the `_occupied_volume_slices` docstring there); `Battery` slices
  each cylinder along its round axis so a resting cell's surface, which
  curves away from the tangent line, doesn't report the same full-diameter
  footprint everywhere — without that a cell could never nose under
  anything shorter than its own diameter, even where it demonstrably clears.
- `case.base.Base._base_placements()` filters on `z_bounds()[0] <= wall +
  1e-6` — that threshold holds for boss-raised parts (standoff ==
  `rib_height`), but not for a component raised by a taller, independent
  amount (e.g. the battery's own `cradle_height`, see
  `components/battery.py`/`geometry/cradle.py`): such a part silently drops
  out of that list. Anything that needs every floor part regardless of
  raise height (like the battery cradle generation in
  `Base.build_bottom()`) must scan `self.assembly.placements` directly, not
  `_base_placements()`.
- `layouts.resolvers.clearance.ClearanceResolver` is a true 3D
  separating-axis test (worst case over every sub-volume pair, best
  separating axis per pair) — with no `axis:` pinned, "gap" is *not* simply
  the Z-clearance between two stacked/buried parts, and a hand-rolled
  Z-only script will disagree with it. It must build tilted Z-spans the same
  way collision checking does (`layouts.base.volume_z_span`) — the two
  diverged once (clearance used a naive center+height, undercounting a
  tilted sub-volume's true reach), letting a clearance check pass a
  placement the collision checker correctly rejected. Calibrate placements
  against the resolver itself (or `TestClient`-style direct calls to it),
  not an independent approximation, however careful.

## Docs

`CONTEXT.md` (domain glossary), `docs/form_factor.md` (agreed shape),
`docs/adr/` (decision records), `docs/reference/` (reference images).

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
