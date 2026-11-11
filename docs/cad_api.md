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
| `ribs.build(spec, w, d)` | `RibSpec` | rib solids |
| `vents.build(spec)` | `VentSpec` | vent slots |
| `cutouts.build(cutouts, shell)` | `Cutout[]`, shell | shell with openings |
| `split.split(...)` | part, `Split` | printable Sections |
| `seam_joint.*` | Seam, `SeamPin` | Seam lugs |
| `edge_treatment.*`, `printability.*` | Sections | chamfers, bed faces |

### Case (`case/`)

| Method | Consumes | Produces |
|--------|----------|----------|
| `Chassis.build()` | config, frame | assembled chassis: Tray + Deck compound |
| `Chassis.build_tray()` | config, frame | lower bowl: taper to `band_z0`, prismatic band, floor, screw columns, lower scallops |
| `Chassis.build_deck()` | config, frame | purely prismatic Deck: keyboard Well, seats, insert bosses, upper scallops |
| `Chassis.sections()` / `tray_sections()` / `deck_sections()` | — | left/right printable Sections of the whole/half |
| `ScreenLid.build()` | config, frame | assembled lid: Bezel + Back plate as a compound |
| `ScreenLid.build_bezel()` | config, frame | display tray, glass opening, band posts, joint inserts |
| `ScreenLid.build_back()` | config, frame | flat Back plate: clamp slots, Rod-clamp inserts, band screws |
| `ScreenLid.sections()` | — | left/right printable Sections of the assembled lid |
| `ScreenLid.bezel_sections()` / `back_sections()` | — | left/right printable Sections of each part |

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
* Edges are chamfer-first: `config.corners.chamfer` for the visible outer
  case corners, `config.edges.*` for inside joint relief and the bed face.
  Fillets are restricted to hidden inside joints (never an outside face).
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
