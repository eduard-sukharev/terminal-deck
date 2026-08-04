---
title: "Keyboard Layout Model and Libraries"
type: "entity"
status: "draft"
language: "default"
source_paths: ["docs/keyboard_architecture.md"]
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

Each switch family (`switches/kb_builder.py`) implements one
interface:

```
Switch  cutout(), plate_tolerance(), plate_thickness(), pcb_keepout(),
        body_size(), mounting_features(), switch_center(), metadata()
```

The plate generator must never know which family it is using — it only talks to
the abstract interface. This keeps the subsystem independent of any switch
family (one of the [[keyboard-subsystem]] design goals).

## Stabilizer library

Stabilizers follow the same philosophy (`stabilizers/kb_builder.py`).
Three families are registered from kb_builder's cutout geometry:
``cherry`` (s=1, Cherry spec), ``costar_compat`` (s=0, costar-compatible),
and ``costar`` (s=2, twin-slot).  Combined types produce a single polygon
per key that includes the switch opening; costar produces two separate slot
polygons.  The plate generator requests geometry from the stabilizer rather
than computing it.

## Reference library (single source of truth)

All physical dimensions live as immutable data in `reference/*.yaml`
(`switch_cutouts.yaml`, `stabilizer_cutouts.yaml`):

```yaml
plate_cutout:
  width: 14.00
  height: 14.00
  corner_radius: 0.50
plate:
  nominal_thickness: 1.60
recommended_clearance:
  0.05
```

No production geometry contains hardcoded dimensions copied from datasheets.
Reference geometry for switch and stabilizer types can be sourced from
**kb_builder** (https://github.com/swill/kb_builder, `../kb_builder`) — its
`lib/builder.py` encodes Cherry MX/costar/spacebar cutout geometry for the same
KLE format.

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
  layout: {source: layouts/jd40.json}
  switch: {family: mx_alps}
  stabilizer: {family: cherry}
  plate: {thickness: 1.6, edge_margin: 6.0, corner_radius: 8.0}
  mounting: {screw: M2, edge_offset: 5.0}
```
