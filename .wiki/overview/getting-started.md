---
title: "Getting Started"
type: "overview"
status: "active"
language: "default"
source_paths: ["README.md", "AGENTS.md", "main.py"]
updated_at: "2026-08-04"
---

# Getting Started

A smart newcomer's first 10 minutes with this repo.

## Environment

CadQuery 2.8 lives in the miniforge env, and the base conda env is Python 3.7
(too old — `typing.Final` missing). Activate miniforge first:

```bash
source $HOME/miniforge/bin/activate
```

There is no test suite or CI; verification is `py_compile` plus the CLI.

## Run it

```bash
python main.py --config config/default.yaml --layout default --steps data
python main.py --steps all
python -m py_compile main.py components/*.py geometry/*.py layouts/*.py assemblies/*.py case/*.py routing/*.py exports/*.py utilities/*.py
```

* `--steps data` — config → components → layout → validation (8 checks), prints
  a report. No CadQuery needed.
* `--steps all` — additionally builds the assembly/base/lid/hinge solids and
  exports STEP/STL/SVG to `generated/`. Boolean-heavy base shell takes ~1 min.

## Expected success output

`--steps data` ends with something like:

```
[pipeline] placement validation:
5 checks: PASS
  [ok  ] no-collisions: ...
  ...
```

## First files to read

1. `docs/design_spec.md` — the master spec (goals, conventions, API contract).
2. `main.py` — `BuildPipeline.run` wires the whole pipeline together.
3. `components/base.py` — the data model and `Component` interface.
4. `utilities/config_loader.py` — how YAML becomes the `Config` dataclass.

## One safe first change

Edit `config/default.yaml` — e.g. change `wall.thickness` — then re-run
`--steps data` and watch the validation report reflect it. Nothing breaks; you
see how config flows to geometry.

## One tempting dangerous change

Import CadQuery directly in a geometry module instead of going through
`utilities/cq_helpers.py`, or hardcode a dimension in a component. That bypasses
the lazy-import adapter and the "no magic numbers" rule, and silently breaks the
component → assembly → enclosure contract. See [[cad-conventions]].
