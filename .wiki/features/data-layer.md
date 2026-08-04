---
title: "Data Layer"
type: "feature"
status: "active"
language: "default"
source_paths: ["components/", "utilities/", "layouts/", "assemblies/assembly.py", "routing/cable_routing.py"]
updated_at: "2026-08-04"
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
  provides the placement frame; `layout_default.py` and `layout_compact.py`
  are the concrete layouts. `make_layout(name, components)` is the factory.
* **Assembly sizing** (`assemblies/assembly.py`) — computes enclosure size,
  mounting bosses, and connector cutouts from placements without building solids.
* **Cable routing** (`routing/cable_routing.py`) — tracks HDMI/USB/power, outputs
  minimum bend radius and clearance tunnels.
* **Fasteners** (`utilities/fasteners.py`) — screw/insert/nut-trap library.
* **Validation** (`utilities/validation.py`) — the 8-check suite. See
  [[validation-suite]].
* **Constants** (`utilities/constants.py`) — connector type identifiers and
  other shared values.

## The CadQuery boundary

`utilities/cq_helpers.py` is the **only** module that imports CadQuery, and it
does so lazily (`require_cq()`). Geometry modules go through it — nothing else
is allowed to `import cadquery`. This is what keeps the data layer importable
without CadQuery. See [[cad-conventions]].

## How it plugs into the pipeline

`BuildPipeline.load_config` → `load_components` → `place_layout` → `validate`
all run on the data layer. The enclosure build and export stages happen on top
in [[cad-generation]]. The full sequence is in [[build-pipeline]].
