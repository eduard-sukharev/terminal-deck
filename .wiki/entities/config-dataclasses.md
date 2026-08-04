---
title: "Config Dataclasses"
type: "entity"
status: "active"
language: "default"
source_paths: ["utilities/config_loader.py", "config/default.yaml"]
updated_at: "2026-08-04"
---

# Config Dataclasses

`utilities/config_loader.py` turns YAML into a validated, frozen `Config`
dataclass — the single source of truth for every build dimension.

## Load order

`load_config()` loads `config/default.yaml`, then deep-merges the requested
topic files on top (`display.yaml`, `keyboard.yaml`, `hardware.yaml`). Topic
files override defaults for their own section. Unknown topic names raise.

## The Config shape

Frozen dataclasses nested under `Config`:

* `Wall(thickness)` — the single wall parameter; `Config.wall_thickness` is an
  alias for `config.wall.thickness`. Everything derives from this.
* `Corners(radius, edge_radius)` — fillet radii, never hardcoded.
* `Clearance(shell, insert, screw)` — shell gap, insert clearance, screw clearance.
* `Display(width, height, thickness, diagonal, active_width, active_height)` —
  the 8.8" panel.
* `Bezel(inset, thickness)` and `Glass(recess_depth)` — lid front.
* `Keyboard(columns, rows, pitch, layout)` — the 40% board.
* `Hinge(diameter, pin, wire_tunnel)` — hinge subsystem geometry.
* `Screws(body, standoff)` — screw library references.
* `Material(name, layer_height, minimum_feature)` — printer limits used by
  validation.
* `hardware: dict` — hardware-adjacent sections (`sbc`, `power`, `io`,
  `usb_breakout`, `driver_board`, ...) collected as a plain dict.

Hardware sections are declared as top-level keys in the topic files and are
filtered into `config.hardware` by `_HARDWARE_SECTIONS`.

## Adding a key

Adding a YAML key usually requires adding a field to the matching dataclass (and
often a `build_config` line). See [[data-layer]] for how config flows into the
pipeline and [[cad-conventions]] for why the single wall parameter matters.
