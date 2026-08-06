---
title: "Validation Suite"
type: "feature"
status: "active"
language: "default"
source_paths: ["utilities/validation.py", "main.py"]
updated_at: "2026-08-06"
---

# Validation Suite

Every build runs a set of checks on **pure data** (placements + component specs +
config) — no CadQuery needed. That is what `--steps data` prints as the report.

## The 9 checks (`utilities/validation.py`)

1. **no-collisions** — placed components overlap in XY *and* Z (the clamshell
   overlaps in XY by design; it only fails when Z ranges also collide). Uses
   `occupied_volumes()` so hollow parts only collide where they occupy space.
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
9. **dimension-consistency** — keyboard and display envelope widths are
   compatible (they share the hinge axis; width ratio must be ≤ 1.15). Every
   placed component fits within the enclosure envelope.

## Constraint resolution report

When using a constraint-based layout ([[constraint-system]]), the pipeline also
prints a constraint resolution report after the validation report. This shows
every constraint in the recipe and whether it was satisfied:

```
[pipeline] constraint resolution:
12 constraints: PASS
  [ok  ] fixed_position: keyboard @ (0.0, 35.0, 0.0)
  [ok  ] centered_on: keyboard centered on x
  [ok  ] keyboard_mounting_holes: keyboard mounting holes: (-89.2, -14.8); ...
```

The constraint report runs alongside the existing validation — both are printed
for constraint-based layouts. Imperative layouts only show the validation report.

## Shape

`CheckResult(name, passed, message)` and `ValidationReport` aggregate them;
`report.summary()` renders the "N checks: PASS/FAIL" block the CLI prints.
`run_all(...)` runs the full suite with sensible defaults for geometry-derived
inputs.

`BuildPipeline.validate` in `main.py` computes `max_height` from placements and
passes pre-enclosure assumptions: mounted components sit on the base floor
(`shell_depths = wall_thickness`) and every external connector needs an opening.
For constraint-based layouts, the pipeline also prints the constraint resolution
report after validation (hard violations abort the build).

See [[build-pipeline]] for where validation sits in the run, and [[cad-conventions]]
for the rules the checks enforce.
