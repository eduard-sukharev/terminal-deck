---
status: accepted
amends: ADR-0003
---

# The chassis splits into a Tray and a Deck, joined at a prismatic band

ADR-0003 fixed the Parting plane and its screw, but the slider's chassis was
still built as one printed shell: the Tray's floor and the Deck with the
keyboard Well, the bearing-clamp seats and the Rear band came out of one tall
bowl. That is wrong for the same reason the lid was split (ADR-0011): the Deck
carries the seats, the Well and the SBC pocket on its top face, and they are
trapped inside a shell that can only be printed standing up. It is also not
serviceable — the bearing clamps and the SBC sit under a deck that cannot be
lifted off.

The chassis now splits at the Parting plane like the lid's band joint:

- The **6 mm band** is split evenly around the plane, **3 mm on each half**.
  The Tray is drafted from its base up to `band_z0 = 13.15`, then **prismatic**
  from `band_z0` to the Parting plane (`16.15`); the Deck is **purely
  prismatic** all the way from the plane to the closed face (`32.3`). Only the
  lower half of the silhouette tapers — the Deck and the closed face stay
  straight. The front and rear (Y) walls are vertical, exactly as before.
- Because the band and the whole Deck are prismatic, the **band width is the
  full closed-face width** (`238.917` after ADR-0013; it was `292.392`), not a
  contracted width at the plane; the base is the drafted width at `band_z0`
  (`235.688`).
- The joint is a **plain butt**: ten M3 screws driven from below, through a
  countersunk hole in the Tray's floor and a column standing on it, into a
  heat-set insert in a boss in the Deck's band. The perimeter band carries the
  shear; the screws clamp it.
- Both halves carry a shallow **scallop** at every station, straddling the
  seam. It is a relief line round the joint, not a structural feature.

## The ten stations

Four **corners**, two per **long side** (front and rear), one per **short
side** (left and right). All coordinates below are on the `+x`/`+y` side; the
case mirrors them.

| station | centre (mm) | boss at the plane | Tray column at the floor |
|---|---|---|---|
| corner | ±112.96, ±65.125 | Ø7.80 | Ø6.42 frustum |
| long side | ±39.82, ±65.125 | Ø7.80 | Ø7.80 |
| short side | ±112.96, 43.875 | Ø10.0 | Ø8.57 frustum |

**Revised by ADR-0013.** The case is now only 4.39 mm wider than the keyboard,
so no station fits beside the keys: the corner and long-wall stations sit
`side_inset` (4.5) from the vertical walls — which caps the corners at Ø7.80
too — and the two short-side stations moved from mid-side to the middle of the
free band **behind the keyboard** (`y = (keyboard rear edge + depth/2)/2`).
Sizes, screw, scallops and `parting_z` are unchanged; only those two stations no
longer mirror about the Y centreplane.

- `station_inset` (6.5 mm) places a station from a **drafted X wall**: the
  draft pulls the floor skin inward, so the column's countersink needs the
  extra room. `side_inset` (4.5 mm) places it from a **vertical front/rear
  wall**, where the keyboard plate sits one Well margin inboard and the insert
  boss has to stay clear of it. The long-side stations also sit at `x =
  ±band_width/6`, clear of both the SBC's corners and the Well.
- The boss diameter is capped per station: `boss = min(10, 2·(surface −
  min_feature))`, where `surface` is the distance to the near outer face
  (the 45° chamfer counts as the face at a corner). The long sides are capped
  at **7.8 mm**; the corners and short sides take the full **10 mm**.
- The Tray column is a **frustum**, `base_boss = min(boss, 2·(base_distance −
  min_feature))`: a straight boss of the full diameter cannot both stay inside
  the tapered skin at `z = 0` and merge into the prismatic band wall above
  `band_z0`. At the drafted X-wall stations the floor only allows **Ø8.57**,
  growing to Ø10 at the plane. No clipping, no separate merged-boss pass.

## The screw

`parting_z = 16.15` mm (0.5 × the 32.3 mm chassis top, inside `parting.min` 10
and `parting.max` 20). Grip = `16.15 − 1.5 = 14.65` mm; `deck_screw` therefore
picks **M3 × 18** (new stock length), which engages **3.35 mm** of the 4.0 mm
insert and cannot bottom out. The Tray gets a Ø3.2 through-hole and a Ø6.2 ×
1.5 countersink from below; the Deck gets a Ø4.4 × 4.0 heat-set insert hole
drilled up from the plane.

The Deck's half of the band is only 3 mm tall, shorter than the 4 mm insert,
so each station gets an **insert boss** standing out of the band's cavity:
`boss_height = insert_depth + boss_margin = 5.5` mm. The boss is a cylinder at
the station diameter, merging into the band wall; the insert bottom is at the
plane and 1.5 mm of boss remains above it.

The material left between features is what sizes the joint:

- insert hole to the outer skin at the long sides: 4.5 − 2.2 = 2.3 mm;
- countersink to the outer skin at the floor: 4.5 − 3.1 = **1.40 mm** (the
  front corner, on the 45° chamfer, is the tightest at **0.71 mm**);
- scallop floor to insert hole: 4.5 − 0.8 − 2.2 = **1.50 mm** (≥ `boss_margin`);
- boss to the nearest placed component (the keyboard plate): **1.60 mm**.

## The scallops

At every station both halves get a 10 mm wide, 0.8 mm deep cut across the
seam: 3 mm on the Tray (`band_z0` → `parting_z`), 3 mm on the Deck
(`parting_z` → `band_z1`), so the notch is 6 mm tall — the whole band. Both
halves are prismatic over those spans, so each cut is a **straight prism** at
a constant 0.8 mm depth; the Tray's draft stops below `band_z0`. This is a
pure relief line — it is shallow enough to stay outside the insert hole at
every station (min 1.5 mm of material) and does not touch the pocket rim.

## Consequences

- The chassis is now `chassis_tray` + `chassis_deck` (each with `_left` /
  `_right` Sections at the stepped Seam), and `chassis` is the assembled
  compound. Both halves print flat: after ADR-0013 Tray and Deck are each
  **121.5 × 139.25 × 16.15 mm** as a Section (45 486 / 27 690 mm³ on the left),
  well inside 220 × 220 × 256 mm.
- The Deck is removable, so the keyboard Well, the two bearing-clamp seats,
  the SBC pocket and the underside of the band are all reachable. The bearing
  clamps or the SBC can come out without disturbing the Tray screws.
- The band is **solid** all round: no vents, no connector cutouts cross it.
  Vents stay deferred and must be redesigned outside the band.
- Nine HARD checks in `run_slider_checks` (`slide-chassis-joint-*`):
  band ≥ insert + min feature, the insert boss ≥ insert + min feature, screw
  engagement ≥ one diameter, the tightest boss holds the insert with the boss
  margin, the tightest column holds the screw clearance, the countersink keeps
  its skin, the scallop keeps its insert margin, the band sits inside the
  chassis top, and every station stays clear of a placed component.
- `geometry/chassis_joint.py` sizes the stations as pure data (no CAD
  import); `case/chassis.py` builds `build_tray()` / `build_deck()`. The old
  one-shell `build()` now returns their compound, so the assembly, the opened
  pose and the Section exports are unchanged in shape.
- ADR-0003's "M3 × 20" was a placeholder; the derived screw is **M3 × 18**.
  Its geometry (Parting plane, columns, inserts) stands, and the screw is now
  computed from the plane rather than guessed.
