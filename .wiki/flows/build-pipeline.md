---
title: "Build Pipeline"
type: "flow"
status: "active"
language: "default"
source_paths: ["main.py", "docs/design_spec.md"]
updated_at: "2026-08-06"
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
4. `validate()` — runs [[validation-suite]], prints the report. For constraint-based
   layouts, also prints the constraint resolution report.
5. Build the `Assembly` → `enclosure_size()`, `bosses()`, `connector_cutouts()`.
6. `cq_helpers.require_cq()` — enter the CAD pass ([[cad-generation]]).
7. Build hinge → assembly solid → base shell → lid shell → hinge solid.
8. Export every part through the `EXPORTERS` registry to `generated/`.

## Layout choices

Available `--layout` values:

| Layout | Type | Description |
|---|---|---|
| `default` | Imperative | Original layout (Python) |
| `default_v2` | Constraint-based | Matches default, plus HDMI cable path + mounting hole constraints |
| `compact` | Imperative | Original compact layout (Python) |
| `compact_v2` | Constraint-based | Matches compact |
| `constrained` | Constraint-based | Empty recipe (base class) |
| `recipe_default` | YAML recipe | `config/layouts/default.yaml` |
| `recipe_compact` | YAML recipe | `config/layouts/compact.yaml` |

Use `--layout-recipe PATH` to override the recipe file for `recipe_*` layouts.

## Failure mode

A `NotImplementedError` from a CAD stage is caught in `main()` and printed as
"CAD stage not yet implemented" with exit code 2.

See [[data-layer]] and [[cad-generation]] for what each half of the pipeline does,
[[constraint-system]] for the constraint architecture, and
[[component-data-pipeline]] for the philosophy underneath.
