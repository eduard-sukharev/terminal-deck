# AGENTS.md

Parametric clamshell cyberdeck CAD generator (CadQuery). Spec: `docs/design_spec.md`.
Data layer and CAD generation are both implemented (assembly solid, base/lid
shells, hinge, STEP/STL/SVG export).

## Environment (critical)

- **Must activate miniforge first** — the base conda env is Python 3.7 and
  fails to import (`typing.Final` missing). CadQuery 2.8 lives in miniforge.
  ```bash
  source $HOME/miniforge/bin/activate
  ```
- No tests, no CI. Verification = `py_compile` + the CLI.

## Run / verify

```bash
source $HOME/miniforge/bin/activate
python main.py --config config/default.yaml --layout default --steps data   # data layer only
python main.py --steps all                                                  # full CAD + exports
python -m py_compile main.py components/*.py geometry/*.py layouts/*.py assemblies/*.py case/*.py routing/*.py exports/*.py utilities/*.py keyboard/*.py keyboard/*/*.py
python -m pytest
```

`--steps data` runs config → components → layout → validation (8 checks) and
prints the report. `--steps all` additionally sizes the enclosure/bosses/
cutouts, builds the assembly/base/lid/hinge solids, and exports STEP/STL/SVG
to `generated/`. Full run takes ~1 min (boolean-heavy base shell).

## Architecture

- **Data layer (implemented, no CadQuery needed):** `components/base.py`
  (`BoundingBox`/`Hole`/`Connector`/`Keepout` + `Component` ABC),
  `utilities/config_loader.py`, `utilities/fasteners.py`, `utilities/validation.py`,
  `layouts/*`, `assemblies/assembly.py`, `routing/cable_routing.py`, and the
  `keyboard/*` package (KLE → layout → switch/stabilizer libraries → plate
  geometry model + its own validation; see `docs/keyboard_architecture.md`).
  The `keyboard/` package is pure data — it must stay importable without
  CadQuery (the cyberdeck adapters `components/keyboard_plate.py` and
  `components/rp2040_keyboard.py` extrude its model during the CAD pass).
- **CAD generation (implemented, requires CadQuery):** `Assembly.build()`
  unions component solids at their placements; `case.Base.build()` shells the
  open-top tray (bosses/ribs/vents/cutouts); `case.Lid.build()` shells the
  open-bottom lid (glass opening); `components/hinge.py` builds the barrels,
  pin, and wire tunnel; `geometry/*` hold the primitives. Wire-up lives in
  `main.py run()`.
- `utilities/cq_helpers.py` is the **only** CadQuery adapter; it imports
  lazily so the data layer stays importable without CadQuery. Geometry modules
  must go through it, not `import cadquery` directly.
- `exports/` exporters are real (delegate to CadQuery exporters).

## Conventions (from docs/design_spec.md — do not violate)

- **No magic numbers.** Every dimension comes from config, a measured
  component, or calculated geometry. Unmeasured values carry `# TODO: measure`.
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
`hardware.yaml` (topic files override). `utilities/config_loader.py` maps them
to frozen dataclasses; adding a YAML key usually requires adding a field to the
matching dataclass (e.g. `Display`).