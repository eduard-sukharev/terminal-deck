---
title: "Component Model"
type: "entity"
status: "active"
language: "default"
source_paths: ["components/base.py", "docs/component_spec.md"]
updated_at: "2026-08-04"
---

# Component Model

The data model in `components/base.py` is what keeps placement, assembly, and
enclosure generation generic. Every hardware component exports the same surface,
so downstream code never cares which specific board it is dealing with.

## Value types (frozen dataclasses, mm)

* `BoundingBox(width, depth, height)` — measured overall size.
* `Hole(x, y, diameter)` — a mounting hole in the component frame.
* `Connector(type, x, y, z, direction, width, height, depth, internal=False)` —
  a physical connector with position, facing direction, and opening size.
  `internal=True` means it mates to a part inside the case (no shell cutout).
* `Keepout(width, depth, height)` — the volume other parts must not enter.

All constructors reject non-positive dimensions via `__post_init__`.

## The Component interface

`Component` (ABC, `components/base.py`) declares:

* `name: str` — human-readable name.
* `size() -> BoundingBox` — abstract, must override.
* `mounting_holes() -> list[Hole]` — default `[]`.
* `connectors() -> list[Connector]` — default `[]`.
* `keepout() -> Keepout` — defaults to size + 4 mm cable allowance.
* `reference_origin() -> tuple` — world-frame origin offset; default `(0,0,0)`
  (origin = center of base).
* `build()` — generates CadQuery geometry; raises `NotImplementedError` in the
  scaffolding pass.

## Implementations

`components/` holds one module per part: `orange_pi_zero2w.py`, `display_88.py`,
`hdmi_driver.py`, `rp2040_keyboard.py`, `keyboard_plate.py`, `usb_breakout.py`,
`heatset_insert.py`, `hinge.py`, `rp2040_zero.py`.

Connector type identifiers are the string constants in `utilities/constants.py`
(e.g. `CONNECTOR_HDMI`), re-exported from `components/base.py`.

The keyboard is currently modeled as grid-based components (`keyboard_plate.py`,
`rp2040_keyboard.py`) driven by `config/keyboard.yaml`. A richer KLE-driven
keyboard subsystem is specced but not implemented — see
[[keyboard-subsystem]].

See [[data-layer]] for how these feed the build, and [[component-data-pipeline]]
for where the interface fits.
