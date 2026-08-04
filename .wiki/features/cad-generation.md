---
title: "CAD Generation"
type: "feature"
status: "active"
language: "default"
source_paths: ["assemblies/assembly.py", "case/base.py", "case/lid.py", "components/hinge.py", "geometry/", "exports/", "utilities/cq_helpers.py"]
updated_at: "2026-08-04"
---

# CAD Generation

The CadQuery pass that turns placements into solid geometry. Requires the
miniforge env (`cq_helpers.require_cq()`).

## What gets built

* **Assembly solid** (`Assembly.build()`) — unions component solids at their
  placements.
* **Base shell** (`case.Base.build()`) — an open-top tray shelled from
  `config.wall.thickness`, with bosses, ribs, vents, and connector cutouts.
  Boolean-heavy; this is the slow part (~1 min).
* **Lid shell** (`case.Lid.build()`) — an open-bottom lid with a glass opening,
  sized from the display placement and the case footprint.
* **Hinge** (`components/hinge.py`) — barrels, pin, and wire tunnel, built from
  `config.hinge` and translated to the rear gap between base cavity and lid.
* **Geometry primitives** (`geometry/`) — boss, fillet, shell, ribs, vents,
  cutouts. These must go through `utilities/cq_helpers.py`. Switch/stabilizer
  cutouts live in the `keyboard/` package (`keyboard/geometry/`), not here; the
  plate is extruded by the `components/keyboard_plate.py` adapter from the
  keyboard geometry model.
* **Exports** (`exports/`) — real STEP/STL/SVG exporters (`EXPORTERS` registry),
  writing `cyberdeck_{assembly,base,lid,hinge}.step/.stl/.svg` to `generated/`.

## The CadQuery adapter

`utilities/cq_helpers.py` wraps CadQuery (`box_centered`, `cylinder_centered`,
`translate`, `require_cq`, ...). It imports lazily so the [[data-layer]] stays
importable without CadQuery. Never bypass it.

## Wiring

`main.py`'s `run()` orchestrates all of it: after validation, it builds the
assembly, base, lid, and hinge solids, then loops the parts over the exporter
registry. The hinge math stays in `components/hinge.py` and cable routing in
`routing/cable_routing.py` — never recreated inline. See [[build-pipeline]].
