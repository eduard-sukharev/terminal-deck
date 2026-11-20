---
status: accepted
amends: ADR-0020
---

# The rail pad's puck pocket has a 45° ramped ceiling, not a flat one

ADR-0020's canned pocket is `10.00 × 10.00 × 2.60` deep, opening from the pad's
cavity face (`x = ±114.583`). Its ceiling was a plain horizontal face at
`z = 13.075` -- the underside of the pad left above it -- and the Tray prints as
modelled (floor down, ADR-0019/0025). Over the pocket the printer therefore had
to lay a horizontal face 2.60 mm deep on nothing but the 1.30 mm pier behind
it: a cantilever, and the only overhang the rail interface contributed.

A chamfer on the mouth's edge alone does not answer that: it softens the lip
but the flat ceiling behind it still spans the pocket. The 45° face has to run
the pocket's whole depth, from the ceiling plane at the pocket's floor up to
the pad's cavity face. That is a chamfer of the shelf itself -- the pad left
above the pocket -- which carries no load: the puck is held by the screw, bears
on the pocket's floor and is square in its pocket's side walls.

## Decision

- **The pocket's ceiling is a 45° ramp over its whole depth**
  (`RailStation.pocket_ramp`, = `pocket_depth`, 2.60 mm). It climbs 1 mm per mm
  from the nominal ceiling corner `(pocket_floor, z1)` and meets the pad's
  cavity face at `z1 + 2.60 = 15.675`. No horizontal face is left anywhere over
  the pocket.
- **The ramp leaves `pocket_lip` of pad above the mouth** (`15.675` under the
  Parting plane / pad top at `16.15`) = **0.475 mm**. That is thinner than
  `material.minimum_feature` (0.6) **on purpose**: it is the edge of the pad's
  wedge over the pocket, not a functional wall -- solid material growing to
  3.075 mm at the back, printed vertically as part of the pad's face, with the
  shelf's underside sloped away from it.
- **The pad is not grown to make room.** The full 45° ramp (2.60) fits between
  the pocket's ceiling plane and the Parting plane without raising the pad or
  dropping the station's screw axis: the PARTING plane is the band joint's
  mating face, and moving the station off the wall's mid-height would amend
  ADR-0020's stance for a cosmetic gain.
- **The cutter is a profile, not a chamfered box.** `Chassis._rail_pocket`
  extrudes a (X, Z) polygon along Y (`cad_helpers.extrude_profile_y`), so the
  45° face is exact and OCC never has to relieve the thin lip or the pier. The
  cutter's 0.10 mm over-cut into the pier stops 0.10 mm below the ceiling and
  the ramp closes it, so the over-cut leaves no horizontal step either.
- **`slide-rail-pocket` (HARD) covers it.** It also requires the ramp to leave
  pad above the mouth (`pocket_lip > 0`) and reports the ramp's depth and the
  lip; a Parting plane low enough for the ramp to reach it fails the check, and
  the derivation's reasons say so.

## Consequences

- The pocket's mouth opens `2.60 mm` higher at the pad's face than at the
  pocket's floor, so the puck slides in under a lead-in instead of a square
  rebate; the puck's back-top corner still meets `pocket_z1` exactly, as it did
  under the flat ceiling.
- The Tray has no overhang face over the pad in its print orientation:
  `tests/test_accessory_rail.py` scans the built Tray with
  `geometry.printability.overhang_faces` over each station's pad footprint and
  requires it empty.
- `tests/test_rail_mounts.py` pins the ramp/lip derivation and forces
  `slide-rail-pocket` to fail on a shortened Parting plane.
