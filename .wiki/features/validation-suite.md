---
title: "Validation Suite"
type: "feature"
status: "active"
language: "default"
source_paths: ["utilities/validation.py", "main.py"]
updated_at: "2026-08-04"
---

# Validation Suite

Every build runs a set of checks on **pure data** (placements + component specs +
config) — no CadQuery needed. That is what `--steps data` prints as the report.

## The 8 checks (`utilities/validation.py`)

1. **no-collisions** — placed components overlap in XY *and* Z (the clamshell
   overlaps in XY by design; it only fails when Z ranges also collide).
2. **no-floating-bosses** — every component with mounting holes has a supporting
   wall beneath (`shell_depths`).
3. **minimum-wall-thickness** — `config.wall.thickness` is at least 2.0 mm.
4. **minimum-screw-clearance** — screw clearance is at least the printable
   `material.minimum_feature`.
5. **minimum-cable-bend** — routed bend radius ≥ minimum (filled by the routing
   stage; defaults to a pass).
6. **no-blocked-connector** — every non-internal connector has a matching shell
   opening (`shell_opening` list).
7. **lid-closes** — lid interior clears the tallest placed component.
8. **hinge-clears** — hinge Z span does not intersect the component volume.

## Shape

`CheckResult(name, passed, message)` and `ValidationReport` aggregate them;
`report.summary()` renders the "N checks: PASS/FAIL" block the CLI prints.
`run_all(...)` runs the full suite with sensible defaults for geometry-derived
inputs.

`BuildPipeline.validate` in `main.py` computes `max_height` from placements and
passes pre-enclosure assumptions: mounted components sit on the base floor
(`shell_depths = wall_thickness`) and every external connector needs an opening.

See [[build-pipeline]] for where validation sits in the run, and [[cad-conventions]]
for the rules the checks enforce.
