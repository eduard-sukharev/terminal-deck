---
title: "Cyberdeck Wiki"
type: "index"
status: "active"
language: "default"
last_commit: "e52b40da73c8b49ccb31e0bf23955152059b5bec"
updated_at: "2026-08-04"
---

# Cyberdeck Wiki

## What is this?

A fully parametric clamshell cyberdeck CAD generator. It turns YAML configuration
(display, keyboard, SBC) into a complete 3D-printable enclosure: assembly solid,
base and lid shells, hinge barrels, and STEP/STL/SVG export files. The tool is a
terminal for field debugging of 3D printers (SSH, tmux, git, firmware flashing),
not a maker platform.

Everything is generated — the design philosophy is "never write CAD directly around
dimensions". Dimensions come from configuration, measured components, or calculated
geometry, and the enclosure regenerates when you change the config. See
[[component-data-pipeline]].

## Get started

The data layer needs no CadQuery; the CAD pass needs the miniforge env.

```bash
source $HOME/miniforge/bin/activate        # CadQuery 2.8 lives here
python main.py --config config/default.yaml --layout default --steps data
python main.py --steps all                  # full CAD + exports (~1 min)
```

Expected output of `--steps data`: a placement validation report with 8 checks
(`5 checks: PASS`). The full run writes `cyberdeck_{assembly,base,lid,hinge}.step/.stl/.svg`
into `generated/`.

First files to read:

* `main.py` — the pipeline driver (`BuildPipeline.run`)
* `docs/design_spec.md` — the master spec (architecture + conventions)
* `docs/component_spec.md` — the Component API contract
* `components/base.py` — the data model (`BoundingBox`, `Hole`, `Connector`, `Keepout`)

Safe first change: tweak `config/default.yaml` (e.g. `wall.thickness`) and re-run
`--steps data` to see the validation output shift.

Tempting dangerous change: editing `utilities/cq_helpers.py` to import CadQuery
globally, or hardcoding a dimension in a component — both break the
component → assembly → enclosure contract. See [[cad-conventions]].

## Why does it exist?

Hand-built CAD for a specific set of hardware is a dead end: change one board and
the whole case needs re-modeling. The parametric pipeline means the enclosure is a
function of configuration. The spec also exists to stop an autonomous LLM from
hardcoding dimensions or writing monolithic CAD scripts — see `docs/design_spec.md`.

## What happens when I run it?

`main.py --steps all` runs the full pipeline:

load config → load components → place layout → validate → size enclosure → build
bosses/cutouts → build assembly solid → shell the base and lid → build hinge →
export STEP/STL/SVG → run validation.

`--steps data` stops after validation (no CadQuery needed). See [[build-pipeline]].

## Where is data saved?

* Configuration lives in `config/` (topic files merge over `default.yaml`).
* Everything the pipeline emits goes to `generated/`:
  * `generated/step/`, `generated/stl/`, `generated/svg/` — exported models
  * `generated/renders/`, `generated/ergogen/` — render PNGs and keyboard-plate
    artifacts (untracked)
* CAD builds are in-memory; only exported files are written.

## What are the important moving parts?

* The **data layer** (no CadQuery): components, config loading, layouts, assembly
  sizing, cable routing, validation. See [[data-layer]].
* The **CAD generation** pass: assembly union, base/lid shells, hinge, exporters,
  all routed through the single CadQuery adapter `utilities/cq_helpers.py`. See
  [[cad-generation]].
* The **validation suite** — 8 checks that run on pure data. See [[validation-suite]].
* The **config model** — frozen dataclasses that every dimension flows from. See
  [[config-dataclasses]].
* The **component model** — the interface every hardware part implements. See
  [[component-model]].
* The **keyboard subsystem** (design-phase) — a proposed `keyboard/` package
  converting KLE JSON layouts into CadQuery plate geometry via switch/stabilizer
  libraries. Not yet implemented; the current plate comes from grid config. See
  [[keyboard-subsystem]].

## What should I avoid breaking?

* The single wall parameter: `config.wall.thickness`. Everything derives from it.
* The coordinate system: +X right, +Y forward, +Z up; origin = center of base.
  Never redefine origins. Units are always millimeters.
* `utilities/cq_helpers.py` is the **only** place allowed to touch CadQuery;
  geometry modules must go through it.
* No magic numbers — unmeasured dimensions carry `# TODO: measure`.
* Layouts contain placements only, never CAD. See [[cad-conventions]].

## Where do I look first?

Read `docs/design_spec.md` for the full contract, then `main.py` to see how the
pieces connect, then [[getting-started]] for the first 10 minutes. The docs
directory (`docs/cad_api.md`, `docs/component_spec.md`, `docs/coordinate_system.md`)
is the design-spec reference material.
