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
| `split.split_part(shape, split, depth, wall)` | part, configured `Split` | its printable Sections (own Seam) |
| `rail_mounts.rail_mounts(config, joint)` | config, chassis joint | the accessory rail's stations: pads, pockets, gusset run, puck and screw stack (ADR-0020) |
| `seam_joint.add_pins(body, seam, pin, sites, substrate, upward)` | Seam, `SeamPin`, sites | the two fin-pair pin pockets of a half |
| `seam_joint.pin_planes(config, budget)` | config, budget | each part's pin substrate Z and direction |
| `edge_treatment.*`, `printability.*` | Sections | chamfers, bed faces |

### Case (`case/`)

| Method | Consumes | Produces |
|--------|----------|----------|
| `Chassis.build()` | config, frame | assembled chassis: Tray + Deck compound |
| `Chassis.build_tray()` | config, frame | lower bowl: prismatic walls, 15° base taper on the end walls, floor, straight screw columns (ADR-0019), rail pads/pockets/gussets (ADR-0020) |
| `Chassis.build_deck()` | config, frame | purely prismatic Deck: keyboard Well, seats, insert bosses |
| `Chassis.tray_sections()` / `deck_sections()` | — | each half's printable Sections, on that piece's configured Seam |
| `ScreenLid.build()` | config, frame | assembled lid: Bezel + Back plate as a compound |
| `ScreenLid.build_bezel()` | config, frame | display tray, glass opening, band posts, joint inserts |
| `ScreenLid.build_back()` | config, frame | flat Back plate: clamp slots, Rod-clamp inserts, band screws |
| `ScreenLid.bezel_sections()` / `back_sections()` | — | each part's printable Sections, on that piece's configured Seam |

### Components (`components/`)

Each `Component.build()` produces the component's solid centered on its
reference origin.

| Function | Consumes | Produces |
|----------|----------|----------|
| `accessory_rail.build_rail(mounts)` | `RailMounts` | the printed rail blank, counterbored M4 holes on the station offsets |
| `accessory_rail.build_rail_washer(mounts)` | `RailMounts` | the square washer puck with the DIN 562 nut pocket |
| `accessory_rail.place_rail(mounts, side)` / `place_rail_washer(mounts, station)` | `RailMounts` | the parts in the chassis frame |

### Exports (`exports/`)

`Exporter.export(shape, path)` — implemented; delegates to build123d exporters.

## Rules

* No magic numbers. Every dimension from config / measured / calculated.
* Every assembly build also exports a glTF with one color per component
  (`Assembly.build_colored()`, palette in `utilities/colors.py`) so parts are
  easy to distinguish. Each component role gets its own opaque color; apply
  transparency only where it makes the inside visible (the case shell).
* `wall_thickness = config.wall.thickness` is the single wall parameter.
* Edges follow the material dihedral (ADR-0025): `config.corners.chamfer` for
  the visible outer case corners (convex), `config.edges.*` for the inside
  joint relief and the bed face, `config.chassis_joint.column_fillet` for the
  column/wall merges and `config.chassis_joint.boss_base_fillet` for the boss
  bases (concave). Concave edges are filleted, convex ones chamfered; a concave
  joint that opens toward the bed keeps the chamfer. A tight-lip Well boss is
  bridged into its facing wall as a rectangle (ADR-0026); its wall chords and
  base edges come from `rect_junction_edges` / `rect_base_edges`, and every
  Well boss is widened by `keyboard.mounting.boss_widen`.
* Heat inserts come from `utilities/fasteners.py`, never recreated.
* Slide math lives in `components/slide.py`, never in the enclosure.
* The FPC guard is built by `ScreenLid.build_fpc_guard()` (a separate printed
  part, positioned on the display's back in the assembly) and exported as the
  `fpc_guard` target; its planform, channel and grille come from
  `SliderFrame` (ADR-0013).
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
