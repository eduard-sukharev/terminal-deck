---
title: "Build Pipeline"
type: "flow"
status: "active"
language: "default"
source_paths: ["main.py", "docs/design_spec.md"]
updated_at: "2026-08-07"
---

# Build Pipeline

`main.py` drives the whole build through `BuildPipeline`. The documented sequence
from `docs/design_spec.md`:

```
load configuration → load components → place layout → validate placement →
generate enclosure → generate bosses → generate hinge → generate cutouts →
generate ribs → export STEP/STL/SVG → run validation
```

## `--steps` control

`BuildPipeline.run(steps)`:

* **`data`** — config → components → layout → validation, then stops. No
  CadQuery imported. This is the fast feedback loop.
* **anything else / `all`** — continues: sizes the enclosure, computes bosses and
  connector cutouts, then (for `all`) builds the CAD solids and exports.

For `all`, the stages are:

1. `load_config()` — merge topic YAML into `Config`.
2. `load_components()` — instantiate `Display88`, `HdmiDriver`, `Rp2040Keyboard`,
   `OrangePiZero2W`, `UsbBreakout` from config.
3. `place_layout()` — `make_layout(name, components, config)` → placements.
   Constraint-based layouts ([[constraint-system]]) resolve constraints into
   placements via `LayoutComposer`.
4. `validate()` — runs [[validation-suite]] (9 checks), prints the report. For
   constraint-based layouts, also prints the constraint resolution report. Hard
   constraint violations abort the build before CAD generation.
5. Build the `Assembly` → `enclosure_size()`, `bosses()`, `connector_cutouts()`.
6. `cq_helpers.require_cq()` — enter the CAD pass ([[cad-generation]]).
7. Build hinge → assembly solid → base bottom → base top → keyboard
   sub-assembly → lid base → lid bezel → display sub-assembly (LCD + HDMI
   driver combined) → hinge solid.
8. Export every part through the `EXPORTERS` registry to `generated/`.
   Only requested `--targets` are built and exported.

## Layout choices

Available `--layout` values:

| Layout | Type | Description |
|---|---|---|
| `default` | Imperative | Original layout (Python) |
| `default_v2` | Constraint-based | Matches default, plus HDMI cable path + mounting hole constraints |
| `compact` | Imperative | Original compact layout (Python) |
| `compact_v2` | Constraint-based | Matches compact |
| `constrained` | Constraint-based | Empty recipe (base class) |
| `recipe_default` | YAML recipe | `config/layouts/default.yaml` — clamshell with battery on base floor |
| `recipe_compact` | YAML recipe | `config/layouts/compact.yaml` — clamshell with battery under keyboard |

Use `--layout-recipe PATH` to override the recipe file for `recipe_*` layouts
with an arbitrary YAML file. Recipes support `{component.field}` and
`{config.path}` references resolved at load time.

## `--targets` selective build

`--targets` (comma-separated, default `all`) controls which CAD solids are
built and exported.  This speeds up the debug loop by skipping expensive
booleans (the base shell takes ~1 min).

| Target | What is exported |
|---|---|---|
| `assembly` | Full union of all placements |
| `base` | Combined base: base_bottom + keyboard_assembly + base_top |
| `base_bottom` | Bottom tray (floor, walls, bosses, ribs, vents, cutouts) |
| `base_top` | Top deck with keyboard cutout |
| `lid` | Combined lid: lid_base + display_assembly + lid_bezel |
| `lid_base` | Rear shell tray only |
| `lid_bezel` | Front plate with glass cutout only |
| `hinge` | Hinge barrels + pin + wire tunnel |
| `display` | LCD panel + HDMI driver combined (fast) |
| `components` | All per-component debug STLs |
| `comp:<role>` | Single component's raw STL (e.g. `comp:driver`) |

The display sub-assembly is built via `Assembly.build_subset()` using
`select_placements()` to pick the display and driver placements.  It is
computed once and shared between the `display` and `lid` targets. The
keyboard sub-assembly is built the same way and shared between the `base`
and `components` targets.

Makefile convenience targets: `make display`, `make base_bottom`, `make base_top`,
`make lid_base`, `make lid_bezel`, `make build TARGETS=display,base`.

## Failure mode

A `NotImplementedError` from a CAD stage is caught in `main()` and printed as
"CAD stage not yet implemented" with exit code 2.

See [[data-layer]] and [[cad-generation]] for what each half of the pipeline does,
[[constraint-system]] for the constraint architecture, and
[[component-data-pipeline]] for the philosophy underneath.
