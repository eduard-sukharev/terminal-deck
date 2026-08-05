# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Parametric clamshell cyberdeck CAD generator (CadQuery), for field debugging of
3D printers. Target hardware: Orange Pi Zero 2W SBC, 8.8" 1920x480 HDMI
display, 40% Cherry-MX-compatible RP2040/QMK keyboard. This is **not** a maker
platform — no GPIO, sensors, LEDs, or decorative elements. Priorities:
robustness, serviceability, printability, parametricity, reusability.

## Environment (critical)

- **Must activate miniforge first** — the base conda env is Python 3.7 and
  fails to import (`typing.Final` missing). CadQuery 2.8 lives in miniforge.
  ```bash
  source $HOME/miniforge/bin/activate
  ```

## Commands

```bash
make data                    # data layer only (config → components → layout → validation)
make all                     # full CAD + exports (STEP/STL/SVG to generated/)
make test                    # pytest
make check                   # py_compile all modules (run after `make data`)
make clean                   # remove generated files and __pycache__

# equivalent direct invocations
python main.py --config config/default.yaml --layout default --steps data
python main.py --steps all
python -m pytest tests/test_layouts.py            # single test file
python -m pytest tests/test_layouts.py::test_name -v   # single test
```

`--steps data` runs config → components → layout → validation (8 checks) and
prints the report; no CadQuery needed. `--steps all` additionally sizes the
enclosure/bosses/cutouts and builds+exports the assembly/base/lid/hinge
solids. Full run takes ~1 min (boolean-heavy base shell). `--layout` accepts
`default`, `default_v2`, `compact`, `compact_v2`, `constrained`,
`recipe_default`, `recipe_compact`; `--layout-recipe <path>` overrides the
built-in recipe for `recipe_*` layouts with an arbitrary YAML file.

## Architecture

Pipeline: `Component -> Placement -> Assembly -> Enclosure -> Features -> Export`.
Everything derives from reusable components; every dimension originates from
configuration, a measured component, or calculated geometry — never
intuition. Wire-up for the full pipeline lives in `main.py` (`BuildPipeline`).

- **Data layer (implemented, no CadQuery needed):** `components/base.py`
  (`BoundingBox`/`Hole`/`Connector`/`Keepout` + `Component` ABC),
  `utilities/config_loader.py`, `utilities/fasteners.py`,
  `utilities/validation.py`, `layouts/*`, `assemblies/assembly.py`,
  `routing/cable_routing.py`, and the `keyboard/` package (KLE → layout →
  switch/stabilizer libraries → plate geometry model + its own validation).
- **CAD generation (implemented, requires CadQuery):** `Assembly.build()`
  unions component solids at their placements; `case.Base.build()` shells the
  open-top tray (bosses/ribs/vents/cutouts); `case.Lid.build()` shells the
  open-bottom lid (glass opening); `components/hinge.py` builds the barrels,
  pin, and wire tunnel; `geometry/*` hold the primitives.
- `utilities/cq_helpers.py` is the **only** CadQuery adapter; it imports
  lazily so the data layer stays importable without CadQuery. Geometry
  modules must go through it, not `import cadquery` directly.
- `exports/` exporters delegate to CadQuery exporters (STEP/STL/SVG).

### Layout system: two generations

Older layouts (`layout_default.py`, `layout_default_v2.py`,
`layout_compact.py`, `layout_compact_v2.py`, `layout_constrained.py`) place
components procedurally in Python — direct, imperative placement code.

Newer **constraint-based** layouts (`recipe_default`, `recipe_compact`)
declare placements as data instead of code:

```
YAML recipe (config/layouts/*.yaml)
  → layouts/recipe_loader.py    parses YAML into Constraint dataclasses
  → layouts/constraints.py      constraint types (EdgeAlignment, CenteredOn,
                                 FixedPosition, CenteredGroup, Clearance,
                                 ZStack, SharePlane, RegionConstraint,
                                 CablePath, FootprintMatch,
                                 RelativePlacement, TargetEnvelope) — pure
                                 data, no logic
  → layouts/composer.py         LayoutComposer resolves each constraint in
                                 recipe order via a registered resolver,
                                 accumulates placements, and produces a
                                 ConstraintReport (HARD violations fail the
                                 build; SOFT warn; GOAL is a reported metric)
  → layouts/resolvers/*.py      one resolver per constraint kind (13
                                 resolvers) — small geometric procedures,
                                 not a general CSP solver
```

Both generations are layout-only: **layouts contain no CAD**, only
placements. `layouts/layout_recipe.py` is the adapter that runs a recipe
through the composer and returns placements in the same shape the older
imperative layouts return.

### Keyboard subsystem

`keyboard/` is a self-contained geometry generator (see
`docs/keyboard_architecture.md`) with **no dependency on cyberdeck code** —
it must stay importable without CadQuery. The cyberdeck adapters
(`components/keyboard_plate.py`, `components/rp2040_keyboard.py`) extrude its
model during the CAD pass.

Data flow: KLE JSON → `keyboard/layout/kle_parser.py` → internal
`KeyboardLayout`/`Key` model (purely descriptive, no geometry) →
`keyboard/switches/kb_builder.py` + `keyboard/stabilizers/kb_builder.py`
(geometry libraries behind a common interface — the plate generator never
knows which switch/stabilizer family it's using) →
`keyboard/geometry/plate.py` (subtracts cutouts, adds mounting holes) →
CadQuery solid, consumed by the cyberdeck assembly. Physical dimensions live
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
- Hinge math lives in `components/hinge.py`, cable routing in
  `routing/cable_routing.py`, fasteners in `utilities/fasteners.py` — never
  recreated inline.
- Component sizes/holes are verified against real datasheets (see
  `docs/component_spec.md`); SBC connector edge positions are user-calibrated
  measurements recorded in `components/orange_pi_zero2w.py`.

## Config

`config/default.yaml` is merged with `display.yaml`, `keyboard.yaml`,
`hardware.yaml` (topic files override). `config/layouts/*.yaml` hold
constraint recipes for the `recipe_*` layouts. `utilities/config_loader.py`
maps YAML to frozen dataclasses; adding a YAML key usually requires adding a
field to the matching dataclass (e.g. `Display`).

## Docs

`docs/design_spec.md` (conventions/philosophy), `docs/coordinate_system.md`,
`docs/component_spec.md` (datasheet-verified dimensions), `docs/cad_api.md`,
`docs/keyboard_architecture.md` (full keyboard subsystem spec).
