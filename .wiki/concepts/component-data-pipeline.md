---
title: "Component → Assembly → Enclosure Pipeline"
type: "concept"
status: "active"
language: "default"
source_paths: ["docs/design_spec.md", "README.md", "main.py"]
updated_at: "2026-08-04"
---

# Component → Assembly → Enclosure Pipeline

The central idea of the project: **never write CAD directly around dimensions.**
Instead, geometry derives from reusable components through a fixed pipeline:

```
Component → Placement → Assembly → Enclosure → Features → Export
```

## What each stage means

* **Component** — a hardware part (SBC, display, keyboard, HDMI driver board)
  implements the `Component` interface: `size()`, `mounting_holes()`,
  `connectors()`, `keepout()`, `reference_origin()`, `build()`. See
  [[component-model]].
* **Placement** — the layout puts components at positions in a frame. Layouts
  (`layouts/`) contain **placements only, no CAD**.
* **Assembly** — resolves collisions, cable clearance, connector accessibility,
  mounting bosses, and the enclosure size.
* **Enclosure** — the base and lid shells generated from the placed set.
* **Features** — bosses, cutouts, ribs, vents, hinge.
* **Export** — STEP/STL/SVG files.

## Why it matters

If component interfaces stay stable, the enclosure regenerates correctly when
configuration changes, with minimal or no code changes. This is what makes the
cyberdeck *parametric* and what lets the tool be reusable across hardware
(screen sizes, keyboard layouts, different SBCs).

The build pipeline that executes this chain is described in [[build-pipeline]].
The layout files live in `layouts/`; the "placements only" rule is enforced by
[[cad-conventions]].
