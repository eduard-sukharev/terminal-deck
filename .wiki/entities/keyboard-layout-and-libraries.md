---
title: "Keyboard Layout Model and Libraries"
type: "entity"
status: "active"
language: "default"
source_paths: ["docs/keyboard_architecture.md", "keyboard/layout/", "keyboard/geometry/", "keyboard/reference/", "keyboard/registry.py", "keyboard/metadata.py", "keyboard/validation.py"]
updated_at: "2026-08-04"
---

# Keyboard Layout Model and Libraries

The pieces the [[keyboard-subsystem]] is built from: the internal layout model,
the switch/stabilizer libraries, reference data, metadata, and validation.

## Input

The canonical input is a Keyboard Layout Editor (KLE) JSON layout. The initial
layout is the JD40 preset with project-specific modifications. No key
coordinates are ever duplicated anywhere else — the layout file is the single
source of truth for key positions.

## Internal layout model

The parser converts KLE into a purely descriptive model with **no geometry**:

```
KeyboardLayout  keys: List[Key]
Key             x, y, rotation, width, height, legend, switch_type, stabilizer_type
```

## Switch library

Each switch family (`switches/kb_builder.py`) implements the
`SwitchProtocol` from `keyboard/registry.py`:

```
SwitchProtocol  cutout_vertices(), plate_tolerance(), plate_thickness(),
                switch_center(), metadata()
```

Five families are registered from the reference data: `square` (code 0),
`mx_alps` (1), `mx_wings` (2), `mx_rotatable` (3), `alps_only` (4). A per-key
``_t`` code in the KLE JSON selects the shape, falling back to the config default
family. The plate generator never knows which family it is using — it only talks
to the abstract interface (`keyboard/geometry/cutouts.py`).

## Stabilizer library

Stabilizers follow the same philosophy (`stabilizers/kb_builder.py`). Three
families are registered: ``cherry`` (s=1, Cherry spec), ``costar_compat``
(s=0, costar-compatible), and ``costar`` (s=2, twin-slot).  Combined types
produce a single polygon per key that includes the switch opening; costar
produces two separate slot polygons. A key needs stabilizers when its effective
width ≥ 2.0 units.  The plate generator requests geometry from the stabilizer
rather than computing it.

## Reference library (single source of truth)

All physical dimensions live as immutable data in `reference/*.yaml`
(`switch_cutouts.yaml`, `stabilizer_cutouts.yaml`), transcribed from
**kb_builder** (https://github.com/swill/kb_builder) `lib/builder.py`. Loaded at
import time by the two `kb_builder.py` modules and shipped as package data:

```yaml
types:
  - code: 1
    name: mx_alps
    width: 15.6
    height: 14.0
    nominal_thickness: 1.6
    recommended_clearance: 0.05
    vertices:
      - [7.0, -7.0]
      # ... cutout polygon, closure point repeated
```

No production geometry contains hardcoded dimensions copied from datasheets.

## Metadata

Geometry ships with structured metadata the enclosure reads without re-measuring
CAD: `width`, `height`, `switch_centers`, `mounting_points`, `bounding_box`,
`plate_thickness`.

## Outputs

Plate, switch cutouts, stabilizer cutouts, mounting holes, plate outline,
bounding box, key metadata, switch center locations, the CadQuery solid, and an
optional DXF export. No enclosure geometry is generated.

## Validation

Every generated plate must pass: no overlapping cutouts, valid stabilizer
spacing, switch inside outline, mounting holes inside plate, minimum edge
distance, valid plate thickness, no duplicate keys, supported switch and
stabilizer families. Generation fails with explicit errors rather than silently
producing invalid geometry.

## Configuration

Switching layouts or switch families requires only config changes, never code:

```yaml
keyboard:
  layout_source: keyboard/layouts/jd40.json
  switch: {family: mx_alps}
  stabilizer: {family: cherry}
  plate: {thickness: 1.5, edge_margin: 8.0, corner_radius: 8.0}
  mounting: {screw: M2, edge_offset: 5.0}
```
