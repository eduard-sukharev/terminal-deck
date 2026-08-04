---
title: "Build Pipeline"
type: "flow"
status: "active"
language: "default"
source_paths: ["main.py", "docs/design_spec.md"]
updated_at: "2026-08-04"
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
3. `place_layout()` — `make_layout(name, components)` → placements.
4. `validate()` — runs [[validation-suite]], prints the report.
5. Build the `Assembly` → `enclosure_size()`, `bosses()`, `connector_cutouts()`.
6. `cq_helpers.require_cq()` — enter the CAD pass ([[cad-generation]]).
7. Build hinge → assembly solid → base shell → lid shell → hinge solid.
8. Export every part through the `EXPORTERS` registry to `generated/`.

## Failure mode

A `NotImplementedError` from a CAD stage is caught in `main()` and printed as
"CAD stage not yet implemented" with exit code 2.

See [[data-layer]] and [[cad-generation]] for what each half of the pipeline does,
and [[component-data-pipeline]] for the philosophy underneath.
