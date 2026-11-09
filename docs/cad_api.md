# CAD API

This document is the contract for the CAD generation pass. It lists every
function that must produce geometry and what it must consume. No hardcoded
dimensions anywhere: all values come from configuration, measured components,
or calculated geometry.

## Pipeline

```
load configuration -> load components -> place layout -> validate placement
-> enclosure -> bosses -> slide -> cutouts -> ribs -> export -> validate
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
| `Chassis.build_tray()` | placements, config | chassis floor + walls/bosses/ribs/vents/cutouts |
| `Chassis.build_deck()` | placements, config | Deck: keyboard Well, Bearing clamps, Rear band |
| `ScreenLid.build_bezel()` | display, config | inverted-tray front + glass opening |
| `ScreenLid.build_back()` | display, config | flat back panel + guide-rod C-channels |

### Components (`components/`)

Each `Component.build()` produces the component's solid centered on its
reference origin.

### Exports (`exports/`)

`Exporter.export(shape, path)` — implemented; delegates to build123d exporters.

## Rules

* No magic numbers. Every dimension from config / measured / calculated.
* Every assembly build also exports a glTF with one color per component
  (`Assembly.build_colored()`, palette in `utilities/colors.py`) so parts are
  easy to distinguish. Each component role gets its own opaque color; apply
  transparency only where it makes the inside visible (the case shell).
* `wall_thickness = config.wall.thickness` is the single wall parameter.
* Fillets use `config.corners.edge_radius` and `config.corners.radius`.
* Heat inserts come from `utilities/fasteners.py`, never recreated.
* Slide math lives in `components/slide.py`, never in the enclosure.
* Cable routing lives in `routing/cable_routing.py`.
* The keyboard plate is independent of the enclosure
  (`components/keyboard_plate.py`).
* Display is never assumed centered on the driver board.
* Functions stay short (<100 lines), pure where possible, and document units
  and assumptions.

## Validation

Every build runs `utilities/validation.run_all(...)`, checking:

no collisions / no floating bosses / minimum wall thickness / minimum screw
clearance / minimum cable bend (drag chain) / no connector blocked / closed
lid covers the chassis / slide travel exposes the keyboard / slide sweep
clears / guide span and lid retention.
