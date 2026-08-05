---
title: "Keycaps and Switch Rendering"
type: "feature"
status: "active"
language: "default"
source_paths: ["components/keycap_set.py", "components/rp2040_keyboard.py", "components/keyboard_plate.py", "keyboard/keycaps/", "keyboard/geometry/keycaps.py", "keyboard/reference/keycap_profiles.yaml", "keyboard/registry.py", "utilities/cq_helpers.py"]
updated_at: "2026-08-05"
---

# Keycaps and Switch Rendering

How the keyboard component renders its top surface: an XDA keycap set lofted
above the plate, simplified switch bodies poking through it, and true
through-holes in the plate.

## Keycap profiles (pure data)

Keycap profiles live in `keyboard/reference/keycap_profiles.yaml` and are
registered through the same registry pattern as switches/stabilizers
(`KeycapProtocol`, `register_keycap`, `get_keycap` in `keyboard/registry.py`).
Only one profile ships today:

```yaml
profiles:
  xda:
    base_size: 18.5       # bottom square side for a 1u key
    top_diameter: 15.0    # top circle diameter for a 1u key
    height: 9.0           # cap height
    segments: 32          # loft sample count per wire
```

The corner radius is derived (`top_diameter / 2`), never stored.

## Cap geometry

`keyboard/geometry/keycaps.py` is pure math, no CadQuery:

* `rectangle_vertices(w, d, n)` — samples a rectangle boundary at *n* uniform
  angles from centre.
* `stadium_vertices(w, d, r, n)` — samples a stadium (rounded rectangle)
  boundary on the same rays. A stadium with `w == d == 2r` degenerates to a
  circle, so 1u keys use the same code path.
* `keycap_specs(keys, profile, pitch, centroid)` — per-key dimensions: bottom
  `key.width × 18.5` by `18.5` deep; top `key.width × 15.0` by `15.0` band with
  `7.5` corner radius. Wide keys get a stadium top instead of an ellipse (e.g.
  a 1.75u Shift cap tops out at 26.25 × 15).

## Lofting the caps

`components/keycap_set.py` (`KeycapSet`) is the CAD adapter: it builds one
lofted cap per switch centre and returns them as a **compound** (see
[[cad-generation]] for why batching matters). `enabled: false` in config yields
no caps.

## Simplified switch bodies

`components/rp2040_keyboard.py` renders a minimal switch under each cap (the
full MX housing is omitted so plate cutouts stay visible):

* a 13 mm cube whose **bottom** face sits 5 mm below the plate top surface, so
  it passes up through the plate cutout and pokes into the keycap;
* a 4 mm diameter cylinder poking 3.5 mm below the cube bottom.

The keycap bottom sits `CAP_PLATE_GAP = 5.5` mm above the plate top (the
exposed switch stem), so `keyboard.size().height` is
`plate_raise + plate_thickness + 5.5 + cap_height`.

## Through-holes

`components/keyboard_plate.py` cuts switch and stabilizer holes with the cut
solid centred mid-plate (`z = plate_thickness / 2`), so they go from the bottom
plate face to the top face — real through-holes, not embossed indents.
