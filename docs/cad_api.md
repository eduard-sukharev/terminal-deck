# CAD API

This document is the contract for the CAD generation pass. It lists every
function that must produce geometry and what it must consume. No hardcoded
dimensions anywhere: all values come from configuration, measured components,
or calculated geometry.

## Pipeline

```
load configuration -> load components -> place layout -> validate placement
-> enclosure -> bosses -> hinge -> cutouts -> ribs -> export -> validate
```

## Functions to implement

### Geometry (`geometry/`)

| Function | Consumes | Produces |
|----------|----------|----------|
| `boss.build(spec, x, y)` | `BossSpec` | boss solid with bore |
| `boss.boss_spec(...)` | wall, screw, insert | `BossSpec` (implemented) |
| `fillet.fillet_edges(shape, edge_radius)` | solid, radius | filleted solid |
| `fillet.fillet_corners(shape, corner_radius)` | solid, radius | filleted solid |
| `shell.offset_shell(shape, wall_thickness)` | solid, wall | hollowed solid |
| `ribs.build(spec, w, d)` | `RibSpec` | rib solids |
| `vents.build(spec)` | `VentSpec` | vent slots |
| `cutouts.build(cutouts, shell)` | `Cutout[]`, shell | shell with openings |

### Case (`case/`)

| Method | Consumes | Produces |
|--------|----------|----------|
| `Base.build()` | placements, config | base shell + walls/bosses/ribs/vents/cutouts |
| `Lid.build()` | display, config | lid shell + bezel + glass recess + mounts |

### Components (`components/`)

Each `Component.build()` produces the component's solid centered on its
reference origin.

### Exports (`exports/`)

`Exporter.export(shape, path)` — implemented; delegates to CadQuery exporters.

## Rules

* No magic numbers. Every dimension from config / measured / calculated.
* `wall_thickness = config.wall.thickness` is the single wall parameter.
* Fillets use `config.corners.edge_radius` and `config.corners.radius`.
* Heat inserts come from `utilities/fasteners.py`, never recreated.
* Hinge math lives in `components/hinge.py`, never in the enclosure.
* Cable routing lives in `routing/cable_routing.py`.
* The keyboard plate is independent of the enclosure
  (`components/keyboard_plate.py`).
* Display is never assumed centered on the driver board.
* Functions stay short (<100 lines), pure where possible, and document units
  and assumptions.

## Validation

Every build runs `utilities/validation.run_all(...)`, checking:

no collisions / no floating bosses / minimum wall thickness / minimum screw
clearance / minimum cable bend / no connector blocked / lid closes / hinge
clears.
