---
status: accepted
amends: ADR-0009, ADR-0012
---

# The Tray's side walls are vertical; its end walls leave the table with a base taper

The slider's Tray has been drafted since ADR-0009: it widened from its base up to
`band_z0` (13.15 mm) and then ran prismatic to the Parting plane. The draft was
there to make the part look cast rather than stacked, and it cost the case a
number that had to be carried through the budget, the band joint's station
margins and the Tray's column frustum.

The accessory rail changes that. The rail is a picatinny/NATO rail bolted to the
Tray's **X side wall**, and a rail on a sloped face cannot work: the rail's web
must lie flat on the wall over its whole length, its two screws must land on one
plane, and the nut pocket behind them must be square to their axis. On a 7°
draft the wall leans 7 mm over the 57 mm of visible height, so a straight rail
would either rock or need a wedge under it.

The Tray's front/rear end walls are vertical for a different reason: the guide
span and the rod end clamps are pinned to the 140 mm face-height budget, and
drafting them would eat that clearance. They do, however, meet the table in a
hard 90° edge over the full depth of the case, which reads as a thicker, blockier
part than the chopped lid above it.

## Decision

- **The Tray is prismatic.** `draft` is now the **lid's** knob only
  (`draft.lid: 7.0`; `utilities.config_loader.Draft` has no other field). The
  budget's `draft_allowance`, the lid's `_outer_shell()` and the cavity behind it
  keep using it; nothing in the chassis does.
- **`geometry.base_taper` owns the Tray's end-wall taper.** Both end walls leave
  the table with a `chassis_joint.taper_angle` (15°) taper that runs up to the
  **bottom of the joint band** (`band_z0` = 13.15 mm), so the band itself stays
  prismatic and the slope stops 3 mm short of the Parting plane -- the old
  "taper + band" silhouette, on the one pair of walls that may lean. Over
  13.15 mm at 15° the face at the table is `tan(15°) * 13.15 = 3.52 mm` inside
  the wall: the base is a couple of millimetres deeper than a chamfer-scale
  taper and reads as a taper, not a trimmed foot.
- **The taper is a draft: the cavity follows.** `build_cutter` takes the wedge
  off the outside and `build_fill` puts the same 15° line back one wall further
  in, from the floor's top up to the taper's top. The wall keeps its 2.00 mm
  thickness over the whole slope instead of thinning to a knife edge at the
  table (below the crossing height the cut alone would remove the wall
  entirely). Below the floor there is no cavity to restore, so the deeper
  bottom edge stays.
- **The taper dies into a pad at every wall station.** The band joint's head
  recesses sit in the floor `4.5 mm` from those walls and keep only a **0.85 mm**
  ring, and the station's column (which carries the screw from the floor to the
  plane) would stand proud of the tapered face. The taper is therefore
  suppressed inside a circle of
  `pad_radius = pocket_radius + mouth_chamfer + minimum_feature = 4.25 mm` plus
  `taper_runout = 3.0 mm`, i.e. `stop_radius = 7.25 mm`, around each station.
  The circle's arc is the **rounded stop** where the taper ends; the pads keep
  the full face (the recess's ring) at all ten wall stations and swallow the
  columns, leaving a locally thicker wall there.
- **One number sizes the cut, the fill and the plan.** `BaseTaper` holds the
  angle, the height, the inset, the pad and stop radii, the stations and the
  resulting runs of full taper along each wall; `build_cutter`/`build_fill`
  only extrude. On the shipped numbers the taper runs `59.52 / 25.72 / 25.72 /
  59.52` mm per wall between the pads and the net change over the prismatic
  Tray is ≈ −0.9 cm³ (the cut and the fill nearly cancel; only the pads add).
- **The stations improve for free.** With no draft the floor skin is the band's
  skin, so every station's `base_boss` equals its `boss` (7.8 mm at the corners
  and long walls, 7.8 mm at the ends) and the Tray's columns are straight, not
  frustums. The corner station's margin goes `3.808 → 4.5 mm`, its mouth
  `0.158 → 0.6 mm` and its recess skin `0.600 → 0.85 mm`; the end station's
  `base_boss` goes `8.571 → 10.0` (its floor margin is now `6.5` mm, so the
  cap no longer bites).
- **Four HARD checks** guard the taper (`utilities/slider_validation`):
  `chassis-taper-draft` (the taper moves the outer face *and* the cavity face,
  leaving a real cavity at the table), `-band` (it stops at `band_z0`), `-pad`
  (the pad leaves `minimum_feature` outside every recess mouth and covers every
  station's column) and `-stop` (every run and every stop is at least
  `minimum_feature` inside the wall, so the pads never swallow the wall whole).

## Consequences

- The base footprint is the closed-face width: `base_width == band_width ==
  241.17` (was 237.94). The silhouette is one width from the table up, and the
  lid is the only half that tapers. The footprint's *depth* is the only thing
  the taper moves: `140` at the band, `132.96` between the pads at the table.
- The Tray's `build_tray()` is a prismatic outer box and a prismatic cavity
  (`chamfer_vertical_edges` + the derived inner chamfer), then the taper cutter,
  the taper fill, the columns, the screws and the Seam pins. `_column` uses a
  straight cylinder whenever `base_boss >= boss`.
- The rail's face is flat and square at `x = ±120.58`: the full Tray side from
  the table to the Parting plane (16.15), `y = ±70` above the base taper and
  `±66.48` on the runs at the table, where the taper has taken its 3.52 mm.
- The taper prints face-down with no support: both faces lean 15° from
  vertical, and the interior slope is shallow enough for the cavity too.
- Not touched: ADR-0015's Seams and per-piece splits (the taper is below the
  band and inside the pads at every station), ADR-0012's band geometry and
  station positions, and the lid's 7° draft.
- Tests: `tests/test_base_taper.py` (data + cutter + built solid, both walls,
  the pad and the stop) replaces the Tray-draft assertions in
  `tests/test_chassis_joint.py` and `tests/test_slider_case.py`; the width
  assertions in `tests/test_slide.py` now name `config.draft.lid`.
