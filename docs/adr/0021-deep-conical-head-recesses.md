---
status: accepted
amends: ADR-0012, ADR-0018
---

# The Tray's band screws are buried one wall below the Parting plane, reached
# down a deep conical access cavity

ADR-0018 seated the chassis band screws' button heads in a **keyhole recess**
cut into the Tray's floor: a stadium counterbore with a 45° lift-out ramp. Its
weakness is depth. The head is only as deep as the printed part lets a driver
come in from the side (seats at z 1.85), so the long screws (**M3 × 18**,
grip 14.30) thread through a Ø3.2 hole up the station column to the insert
high above. The column is a long lever arm the head does nothing about, and a
side-entry recess forces the ramp and the per-station rotation machinery on
every caller.

## Decision

- **The head seats at `z_seat = parting_z − wall`** (14.15): exactly one wall
  of material (2.00) between the head's bearing face and the Parting plane —
  the deepest any head can be buried without entering the Deck half. The pocket
  is the head's exact height (Ø6.10 × 1.65, seat ring 1.45), so the grip is
  that same wall, **2.00**, and the stock screw shortens to **M3 × 6**
  (engagement 4.00 of 4.00 — at the `deck_screw` rule's boundary; real button
  heads measure ≈1.6 tall and buy ~0.05 of extra thread).
- **The driver reaches the head down a cone that widens to the floor face.**
  The access cavity is a rotationally symmetric frustum from the head pocket's
  neck (z 12.50, Ø6.10) up to the floor face. The mouth stays one
  `minimum_feature` inside the station's column footprint —
  `mouth_radius = base_boss / 2.0 − minimum_feature` (Ø6.60 at the long
  walls, Ø8.80 at the ends), cone half-angles 1.1° / 6.1° — so the pier keeps
  a thick wall at the floor (`margin − mouth_radius` = the skin lip plus one
  minimum feature = 1.20 at the long walls) instead of dying into a knife
  edge. Printable without supports, no ramp, no per-station rotation; the
  driver enters straight along the screw axis.
- **The column is strict where the screw and the head need it, conical
  below.** From the cone's neck to the Parting plane the column is a plain
  cylinder of `2 × (pocket_radius + minimum_feature)` = Ø7.30 (the pocket
  plus one minimum feature a side); below the neck it is a frustum from its
  floor footprint (Ø7.80) down to the strict diameter, its outer wall running
  conical beside the cavity. The Deck's insert boss stays a straight
  full-height cylinder (strict dimensions for the heat-set insert).
- **ADR-0018's keyhole stays the lid's band joint** (`geometry/joint.py`).
  The lid's screws can come in from the side because its access face is open;
  the chassis access face is the Tray's floor, where depth is free and
  side-entry is not. Both profiles live in `geometry/head_recess.py`:
  `fasteners.HeadRecess` + `build_cutter` (keyhole) and `DeepRecess` +
  `deep_recess` + `build_deep_cutter` (deep cone).
- **The base taper pads track the mouth**: `pad_radius = mouth_radius +
  min_feature` (pad Ø7.80, stop Ø13.80), so the taper dies into the pad right
  at the cone's lip. The taper still stops well before the corners; no corner
  changes. (A later change may run the taper through the cavities of all
  non-corner stations; the cone mouths already exceed the taper's plan gap
  there.)

## Consequences

- `geometry/chassis_joint.py` sizes a `DeepRecess` and exposes `skin`
  (`parting_z − z_seat`); `TrayStation.mouth_radius` replaces
  `mouth_chamfer`, alongside `strict_boss` (the strict zone's diameter) and
  `base_boss` (the floor footprint); `ChassisJoint.recess` is a `DeepRecess`.
- `case/chassis.build_tray()` cuts one `build_deep_cutter` per station — no
  `normal`, no rotation — and raises each column as a frustum below the
  cone's neck plus a strict cylinder above it.
- `geometry/base_taper.py` sizes the pads from `mouth_radius` (pad Ø7.80,
  stop Ø13.80 — the pad is the column's floor footprint plus one minimum
  feature).
- HARD checks `slide-chassis-joint-seat` / `-floor` / `-pocket` / `-column` /
  `-parting` pin the new invariants (seat at `parting_z − wall`, lip ≥
  `minimum_feature`, pocket inside the column).
- The floor head recess ring — the binding plan constraint of ADR-0012/0013 —
  is gone: the binding constraints are now the 2.3 mm insert skin at the long
  sides and the cone lip.
