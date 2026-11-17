---
status: accepted
amends: ADR-0019
---

# The accessory rail is printed, bolted to the Tray's vertical X walls

ADR-0019 made the Tray's X walls vertical so "the accessory rail can bolt to a
flat face", but left the interface as two square-nut pockets and assumed the
rail bars were user-supplied. In practice a MIL-STD-1913 section is a simple
prism to print, and the case is useless with an accessory interface nobody has
a matching rail for. The interface also needs a defined stance, a defined screw
and a place for the nut: a raw pocket in a 2 mm wall gives the nut nothing to
bear on and the screw nothing to clamp.

## Decision

- **The rail is printed.** `components/accessory_rail.py` builds the rail blank
  and the washer puck; `case.chassis` cuts the matching station features into
  the Tray. Both read the same `geometry.rail_mounts` pattern, so a hole cannot
  drift between the Tray and the rail it carries.
- **Two M4 stations per wall, at `y = ±30`** (`slide.rail.stations: 2`,
  `station_spacing: 60.0`). They are mirrored about the wall's centre, on the
  wall's mid-height (`parting_z / 2` = 8.075). `station_spacing` must be an
  **even count and a whole number of slot pitches**: 60 is `6 x 10`, which also
  lands both screws on the profile's **bridge centres** instead of mid-slot, so
  the counterbore of the profile (a later slice) can never eat a slot. The old
  `+/−25` stance did not satisfy that; the band joint's X-wall column sits at
  `y = ±44.25` (Ø10 boss, footprint from 39.25), so the `±30` pad reaches 35.6
  and leaves a 3.65 mm gap.
- **Each station is a pad, not a bare pocket.** The pad is a square column
  `2 x wall` (4.00 mm) deep into the cavity, `11.20 mm` wide, from the floor's
  top (2.00) up to the Parting plane (16.15), merged into the wall and the
  floor. Nothing about it is a free-hanging boss, the Deck above it is the
  band's wall, and the band joint's columns are untouched. Its square
  **pocket** is `10.00 x 10.00 x 2.60` deep, opening from the pad's cavity face
  (`x = ±114.583`) and floored at `±117.183`: the face the puck bears on.
- **Two 45° gussets per station**, fore and aft of the pad, sharing **one run**
  (`3.05 mm` on the shipped numbers). The run is derived from the tightest free
  run across *all* stations -- the rear station's neighbour is the band column
  -- so a station next to a column shortens its partner's rib too instead of
  leaving one rib a fin. The rib's tip is truncated one minimum feature before
  the floor, so it lands on a small vertical face rather than a knife edge, and
  the rib never rises past the screw axis.
- **The nut rides in a printed washer puck**, not in the wall: a square
  `9.60 x 9.60 x 2.80` printed washer with a `7.20 x 7.20 x 2.20` DIN 562 M4
  pocket, its floor `0.60` (one minimum feature) under the nut. It cannot
  rotate (square pocket in a square pad pocket), cannot fall in (the pocket
  floor behind it), and **protrudes one fit** (`0.20`) so it lifts back out with
  a fingernail. The nut's own fit comes from `utilities.fasteners`
  (`SQUARE_NUTS["M4"]`, 7.0 across the flats, 2.2 thick).
- **The screw stack is derived and pinned to a stock length.** A button-head M4
  comes from outside: through the counterbore in the rail (`Ø8.00 x 2.40`), the
  rail's web (`2.60`), the wall (`2.00`), the pad behind the pocket (`1.40`),
  the puck's floor (`0.60`) and the nut (`2.20`) = **8.80 mm**. The stock length
  is the first `STANDARD_LENGTHS["M4"]` entry at least one minimum feature
  past it: **M4 x 10**, leaving 1.20 mm of thread past the nut (at most one
  pitch of waste).
- **The rail blank** is `21.2 mm` across the wall (MIL-STD-1913, so it overhangs
  the 2 mm wall by 9.6 mm a side and the device stands on its lower edges),
  `5.0 mm` thick, and `spacing + 2 x pitch = 80 mm` long, with a counterbored
  M4 hole on each station. **The profile -- the 10 mm slots and the hex top --
  is a later slice** on top of an unchanged interface; the blank exists now so
  the stance, the screw and the nut are settled and printable.
- **Six HARD checks** guard the interface (`utilities/slider_validation`):
  `slide-rail-stations` (even, mirrored, one Z per pair), `-spacing` (one
  `station_spacing` apart and within a micrometre of a bridge centre),
  `-clear` (pads clear the band columns; every gusset keeps its run),
  `-pocket` (puck floor, pad ring and the pocket's Z margins),
  `-screw` (the rail web under the head, and the stock length with a minimum
  feature past the nut up to one pitch) and `-envelope` (the rail fits the
  wall's straight span and the build volume, and does overhang the wall).
- **New build targets:** `rail`, `rail_washer`, and the two placed sets in the
  `chassis`/`assembly`/`assembly_opened` glTF, each with its own colour
  (`accessory_rail` violet, `rail_washer` yellow).

## Consequences

- The Tray's X wall is no longer plain: from `y = ±21.95` to `±38.05` each wall
  carries a pad (`±24.40 … ±35.60`) and a truncated rib each way inside the
  cavity, so the wall-thickness probe in
  `tests/test_slider_case.py` moved to `y = 0` (between the stations).
- The rail's outer face is `x = ±125.583`, 5 mm proud of the case's widest
  point: the case grows nothing, but the accessory interface is the outermost
  feature and a rail-mounted device stands on the rail's edges, not the Tray
  floor.
- The rail, the pucks and the four M4 x 10 screws are printed/purchased parts,
  not user-supplied rail sections; `docs/design_spec.md`'s "no decorative
  picatinny rails" rule still bans *decorative* rails, and this one is
  functional.
- Tests: `tests/test_rail_mounts.py` (pattern, pads, pockets, gussets, screw
  stock and each HARD check forced to fail), `tests/test_accessory_rail.py`
  (the Tray's station features and both printed parts, placed and probed on the
  built solid), plus `tests/test_fasteners.py`, `tests/test_config_loader.py`
  and the automatic `tests/test_colors.py`.
