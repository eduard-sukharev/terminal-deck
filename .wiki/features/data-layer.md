---
title: "Data Layer"
type: "feature"
status: "active"
language: "default"
source_paths: ["components/", "utilities/", "layouts/", "assemblies/assembly.py", "routing/cable_routing.py", "keyboard/"]
updated_at: "2026-08-07"
---

# Data Layer

The part of the pipeline that runs **without CadQuery**. Everything here is pure
Python data — it imports cleanly and is what `--steps data` exercises.

## What it covers

* **Components** (`components/`) — the data model and measured part definitions.
  See [[component-model]].
* **Config loading** (`utilities/config_loader.py`) — YAML → frozen `Config`.
  See [[config-dataclasses]].
* **Layouts** (`layouts/`) — placement-only definitions. `layouts/base.py`
  provides the placement frame. Three kinds of layouts:
  * **Imperative** (`layout_default.py`, `layout_compact.py`) — direct
    `Placement()` calls with hardcoded arithmetic.
  * **Constraint-based Python** (`layout_constrained.py`, `layout_default_v2.py`,
    `layout_compact_v2.py`) — declarative `Constraint` objects resolved by
    `LayoutComposer`. See [[constraint-system]].
  * **YAML recipes** (`config/layouts/default.yaml`, `config/layouts/compact.yaml`)
    — layouts defined entirely in YAML, loaded by `RecipeLayout`. Support
    `{component.field}` and `{config.path}` references. See [[constraint-system]].
  `make_layout(name, components, config, recipe_path)` is the factory.
* **Constraint system** (`layouts/constraints.py`, `layouts/composer.py`,
  `layouts/resolvers/`) — 13 constraint types with 13 real resolvers (no stubs).
  Pure data, no CadQuery. See [[constraint-system]].
* **Assembly sizing** (`assemblies/assembly.py`) — computes enclosure size,
  mounting bosses, and connector cutouts from placements without building solids.
  Also provides `select_placements(placements, keep)` for grouping placements
  by component identity (used by the display sub-assembly target) and
  `Assembly.build_subset(placements)` for building a subset of placements
  into a world-transformed solid.
* **Cable routing** (`routing/cable_routing.py`) — tracks HDMI/USB/power, outputs
  minimum bend radius and clearance tunnels.
* **Fasteners** (`utilities/fasteners.py`) — screw/insert/nut-trap library.
* **Validation** (`utilities/validation.py`) — the 9-check suite. See
  [[validation-suite]].
* **Keyboard subsystem** (`keyboard/`) — pure data: KLE layout parsing, switch
  and stabilizer libraries, plate geometry model, and its own validation. No
  CadQuery; the cyberdeck adapter (`components/keyboard_plate.py`) extrudes the
  model into a solid only during the CAD pass. See [[keyboard-subsystem]].
* **Build targets** (`utilities/targets.py`) — `resolve_targets(tokens, roles)`
  validates and resolves `--targets` tokens into bucket names and per-component
  roles. Pure data, no CadQuery.

## The CadQuery boundary

`utilities/cq_helpers.py` is the **only** module that imports CadQuery, and it
does so lazily (`require_cq()`). Geometry modules go through it — nothing else
is allowed to `import cadquery`. This is what keeps the data layer importable
without CadQuery. See [[cad-conventions]].

## How it plugs into the pipeline

`BuildPipeline.load_config` → `load_components` → `place_layout` → `validate`
all run on the data layer. The enclosure build and export stages happen on top
in [[cad-generation]]. The full sequence is in [[build-pipeline]].
