---
title: "Constraint System"
type: "concept"
status: "active"
language: "default"
source_paths: ["layouts/constraints.py", "layouts/composer.py", "layouts/resolvers/", "layouts/layout_constrained.py", "layouts/recipe_loader.py", "config/layouts/"]
updated_at: "2026-08-06"
---

# Constraint System

A declarative constraint system replaces imperative layout math with composable rules. Layouts become recipes of `Constraint` objects resolved by small procedural resolvers — no general CSP solver, no hardcoded coordinate formulas.

## Architecture

```
Layout recipe (list of Constraints)
    │
    ▼
LayoutComposer.compose(constraints, components, config)
    │
    ├─ For each constraint: dispatch to registered Resolver
    │     resolver reads current partial placements
    │     resolver writes new/changed placements
    │
    ├─ Post-pass: validate ALL constraints
    │     - HARD: error if violated
    │     - SOFT: warn if violated
    │     - GOAL: report metric
    │
    ▼
list[Placement] + ConstraintReport
```

## Constraint types (`layouts/constraints.py`)

| Constraint | Purpose |
|---|---|
| `EdgeAlignment` | Align component edge to enclosure wall or another component |
| `CenteredOn` | Center component on X/Y within enclosure or relative to another |
| `CenteredGroup` | Center a group's bounding box on an axis (rebalancing) |
| `FixedPosition` | Set component position directly on specified axes |
| `RelativePlacement` | Place at explicit offset from another component |
| `ZStack` | Assign Z heights to layers |
| `Clearance` | Validate minimum gap between keepout volumes |
| `SharePlane` | Set all subjects to same Z plane |
| `RegionConstraint` | Validate component is within named region |
| `CablePath` | Validate cable route between connectors |
| `FootprintMatch` | Validate shared XY footprint |
| `TargetEnvelope` | Record enclosure size hint |
| `KeyboardMountingHoles` | Compute plate mounting holes between rows, near wide keys |

## Resolvers (`layouts/resolvers/`)

Each constraint kind has a corresponding resolver — a small (~30 line) geometric
procedure. All 13 constraint types have real resolvers; no stubs remain. Resolvers
split into two groups:

* **Placement producers** — `fixed_position`, `centered_on`, `centered_group`,
  `edge_alignment`, `relative_placement`, `z_stack`, `share_plane`,
  `keyboard_mounting_holes`
* **Verification-only** — `clearance`, `region`, `cable_path`, `port_access`,
  `footprint_match` (validate an already-resolved layout)
* **Envelope publisher** — `target_envelope` (declares enclosure size so
  wall-relative resolvers align against real walls)

## Layout classes

| Class | File | Description |
|---|---|---|
| `ConstraintLayout` | `layouts/layout_constrained.py` | Base class: overrides `_build_placements` with `LayoutComposer` |
| `RecipeLayout` | `layouts/layout_recipe.py` | Loads constraints from a YAML file instead of Python |
| `LayoutDefaultV2` | `layouts/layout_default_v2.py` | Constraint-based default layout (matches original) |
| `LayoutCompactV2` | `layouts/layout_compact_v2.py` | Constraint-based compact layout (matches original) |

## YAML recipes (`config/layouts/`)

Layouts can be defined entirely in YAML — no Python code needed. The
`RecipeLayout` adapter loads a YAML file via `recipe_loader.py`, which parses
each constraint entry into the matching `Constraint` dataclass:

```yaml
constraints:
  - kind: fixed_position
    subject: keyboard
    y: 35.0
  - kind: centered_on
    subject: keyboard
    axes: ["x"]
```

Values support `{component.field}` and `{config.path}` references (e.g.
`{sbc.depth}`, `{config.wall_thickness}`) resolved at load time. Arithmetic
expressions over references are also supported (e.g.
`"{display.width} + 2 * {config.clearance.shell} + 2 * {config.wall_thickness}"`).

Built-in recipes:
* `config/layouts/default.yaml` — clamshell with battery on base floor beside SBC
* `config/layouts/compact.yaml` — clamshell with battery under raised keyboard plate

## CLI usage

```bash
python main.py --layout default_v2 --steps data     # constraint-based Python layout
python main.py --layout recipe_default --steps data  # YAML recipe layout
python main.py --layout recipe_default --layout-recipe my_layout.yaml  # custom recipe
```

## Constraint report

When using a constraint-based layout, the pipeline prints a constraint resolution
report alongside the validation report. Hard violations abort the build:

```
[pipeline] constraint resolution:
12 constraints: PASS
  [ok  ] fixed_position: keyboard @ (0.0, 35.0, 0.0)
  [ok  ] centered_on: keyboard centered on x
  [ok  ] keyboard_mounting_holes: keyboard mounting holes: (-89.2, -14.8); ...
```

See [[build-pipeline]] for where constraints fit in the run, and [[data-layer]] for the data side.
