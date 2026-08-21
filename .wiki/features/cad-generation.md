---
title: "CAD Generation"
type: "feature"
status: "active"
language: "default"
source_paths: ["assemblies/assembly.py", "case/base.py", "case/lid.py", "components/hinge.py", "components/keycap_set.py", "geometry/", "exports/", "utilities/cq_helpers.py"]
updated_at: "2026-08-07"
---

# CAD Generation

The CadQuery pass that turns placements into solid geometry. Requires the
miniforge env (`cq_helpers.require_cq()`).

## What gets built

* **Assembly solid** (`Assembly.build()`) — unions component solids at their
  placements.
* **Base bottom** (`case.Base.build_bottom()`) — the bottom tray, shelled open
  at >Z, with bosses, ribs, vents, connector cutouts, and 4 corner standoff
  bosses (M2.5) for the deck. 2 mm chamfer on the bottom perimeter (applied
  before shelling). Boolean-heavy; this is the slow part (~1 min).
* **Base top** (`case.Base.build_top()`) — the deck plate covering the cavity,
  with a keyboard cutout (sized to the keyboard plate + clearance) and 4
  corner M2.5 clearance holes. The deck sits at the keyboard plate top so
  keycaps protrude through the cutout.
* **Combined base** — `--targets base` unions base_bottom + keyboard_assembly +
  base_top into one solid (`cyberdeck_base.*`).
* **Lid base** (`case.Lid.build_base()`) — the rear shell tray, open at −Z
  (toward the base), with a rectangular pocket on the +Z face for the bezel.
  Four M2.5 bosses at the corners accept bezel screws. 2 mm chamfer on the
  bottom perimeter (applied before shelling).
* **Lid bezel** (`case.Lid.build_bezel()`) — the front plate with a centered
  glass cutout and four M2.5 clearance holes. Sits inside the lid_base pocket
  so its front face is flush with the lid_base walls. 2 mm bevel on the inner
  front edge of the glass cutout.
* **Combined lid** — `--targets lid` unions lid_base + display_assembly +
  lid_bezel into one solid (`cyberdeck_lid.*`).
* **Hinge** (`components/hinge.py`) — barrels, pin, and wire tunnel, built from
  `config.hinge` and translated to the rear gap between base cavity and lid.
* **Geometry primitives** (`geometry/`) — boss, fillet, shell, ribs, vents,
  cutouts. These must go through `utilities/cq_helpers.py`. Switch/stabilizer
  cutouts live in the `keyboard/` package (`keyboard/geometry/`), not here; the
  plate is extruded by the `components/keyboard_plate.py` adapter from the
  keyboard geometry model.
* **Exports** (`exports/`) — real STEP/STL/SVG exporters (`EXPORTERS` registry),
  writing `cyberdeck_{assembly,base,base_bottom,base_top,lid,lid_base,lid_bezel,display,hinge}.step/.stl/.svg`
  to `generated/`. Selective via `--targets` (see [[build-pipeline]]).
* **Keyboard render** (`components/keycap_set.py` + `rp2040_keyboard.py`) —
  XDA keycaps lofted above the plate and simplified switch bodies passing
  through it. See [[keycaps]].

## The CadQuery adapter

`utilities/cq_helpers.py` wraps CadQuery (`box_centered`, `cylinder_centered`,
`translate`, `loft_between`, `make_compound`, `require_cq`, ...). It imports
lazily so the [[data-layer]] stays importable without CadQuery. Never bypass it.

## Batching boolean ops

`make_compound(shapes)` groups many solids into one unfused compound so a
single `.union()` fuses them all in one boolean operation. This matters
because the keyboard build previously did 124 sequential unions (82 switch
bodies + 41 keycaps + controller) and took > 5 minutes; batching to 3 fuses
brought it back to under a minute.

## Wiring

`main.py`'s `run()` orchestrates all of it: after validation, it builds the
assembly, base bottom, base top, keyboard sub-assembly, lid base, lid bezel,
display sub-assembly, and hinge solids, then loops the parts over the exporter
registry. The hinge math stays in `components/hinge.py` and cable routing in
`routing/cable_routing.py` — never recreated inline. See [[build-pipeline]].
