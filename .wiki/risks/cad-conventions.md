---
title: "CAD Conventions"
type: "risk"
status: "active"
language: "default"
source_paths: ["docs/design_spec.md", "AGENTS.md", "utilities/cq_helpers.py"]
updated_at: "2026-08-04"
---

# CAD Conventions (what not to break)

The rules from `docs/design_spec.md` that keep the parametric pipeline working.
Violating these silently breaks the component → assembly → enclosure contract.

## Hard rules

* **No magic numbers.** Every dimension comes from config, a measured component,
  or calculated geometry. Unmeasured values carry `# TODO: measure`.
* **Units are always millimeters.** Never inches.
* **Coordinate system:** +X right, +Y forward, +Z up; origin = center of the
  base. Never redefine origins (`reference_origin` defaults to `(0,0,0)`).
* **Single wall parameter:** `config.wall.thickness` (`Wall`). Everything
  derives from it — no ad-hoc wall thicknesses.
* **No hardcoded fillet radii** — use `corners.radius` / `corners.edge_radius`
  from config.
* **Layouts contain no CAD** — only placements.
* **Hinge math** lives in `components/hinge.py`; **cable routing** in
  `routing/cable_routing.py`; **fasteners** in `utilities/fasteners.py`. Never
  recreated inline.
* **`utilities/cq_helpers.py` is the only CadQuery adapter.** It imports lazily
  so the [[data-layer]] stays importable without CadQuery. Geometry modules must
  go through it, not `import cadquery` directly.
* **No `box(220,120,20)`-style magic boxes** — use derived `overall_width()`,
  `overall_depth()`, `overall_height()`.

## Why these matter

The design goal is that changing configuration regenerates the enclosure with
minimal or no code changes (see [[component-data-pipeline]]). Hardcoded values,
redefined origins, or a second wall thickness all break that property and the
validation suite's assumptions ([[validation-suite]]).

## Serviceability intent

Priorities are robust, serviceable, printable, parametric, reusable — the
device is a field-debugging terminal, not a maker platform (no GPIO, sensors,
LEDs, decorative elements).
