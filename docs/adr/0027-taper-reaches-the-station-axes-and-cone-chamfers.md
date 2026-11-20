---
status: accepted
amends: ADR-0019, ADR-0022
supersedes: ADR-0023
---

# The base taper's face at the table passes through the band stations' axes;
# the cones' outside edges take the 45° chamfer, not a fillet

ADR-0019's 15° base taper left the sloped face 2.32 mm inside the access cone's
mouth at the table, so each long-wall station kept a floor strip of skin
between the cone's opening and the taper's line, and ADR-0023 eased that
opening with a fillet on two edge classes -- the mouth rims (1.0 mm) and the
taper-flared lips (radius-limited to 0.47 mm).

Two things were wrong with that. The taper was still shallow enough that the
floor near each screw read as a flat ledge rather than a drafted foot, and the
fillet contradicted the dihedral rule ADR-0025 states: the cones' mouth rims
and lips are **convex** edges (the material sits on one side), so they take the
45° chamfer, never a fillet.

## Decision

- **The taper's reach is derived, not configured.** `geometry/base_taper`
  sets `inset = chassis_joint.side_inset` (4.5 mm) and derives the angle off
  vertical from it over the band's bottom (`atan(4.5 / 13.15)` ≈ **18.89°**).
  The face at the table therefore passes exactly through the six long-wall
  stations' axes. `chassis_joint.taper_angle` is retired; no magic number
  replaces it.
- **The taper cuts the outboard half of each cone mouth away.** At a
  through-station the face at the table is the station's axis plane, so the
  outboard half of the Ø6.60 mouth is air and the inboard half-ring remains as
  the bed rim. The opening flares up into the lip -- a closed ellipse whose
  cusp sits at `z ≈ 9.11` (was 6.4) -- while the pier ring at the taper's top
  stays 1.45 mm and only grows. The base depth between the corner pads is
  **131.0** (was 132.95); the four corner pads keep the full face and their
  Ø13.80 stop.
- **The cones' outside edges take `edges.bed_chamfer` (0.5 mm, 45°).** Both
  classes `geometry.edge_treatment.cone_cut_edges` selects -- the mouth rims
  at the bed and the taper-flared lips -- are chamfered, never filleted. The
  lips go **first** and the rims are re-selected afterwards: a chamfer that
  meets a lip at the bed leaves lip stubs OCC cannot treat, while the lip
  first keeps the rim a clean arc. `chassis_joint.taper_fillet` and
  `geometry.head_recess.cone_rim_fillet_run` are retired.
- **The HARD checks follow.** `chassis-taper-opens` now pins
  `station.margin == taper.inset` (the face on the axis) instead of "inside the
  mouth"; `chassis-taper-chamfer` replaces `-fillet` and requires the chamfer
  plus one minimum feature below the pocket's neck (2.29 mm of room at 0.5);
  `chassis-taper-pad` measures the corner pad's bed ring against the physical
  stop radius including the chamfer (3.1 mm), not the data pad radius.

## Consequences

- The bed silhouette between the pads is 9 mm shallower than the band, and
  each long-wall access hole reads as a half-cone open at the bottom with a
  45° chamfer on its rim. A chamfer on a cone-against-plane edge is itself a
  conical face, so the bed opening grows by exactly the chamfer size on every
  side (Ø6.60 → Ø7.60 at a through-station) and the new bed boundary is still
  a circle, never a torus.
- On the shipped numbers the treatment removes ≈ 37 mm³ from the Tray (13.3
  from the six lips, 24.3 from the twelve rims), with every edge taking it --
  no SOFT skips.
- The cavity shrinks by the extra 0.98 mm of draft at low Z: the SBC's rear
  gap at the floor goes 5.01 → 4.18 mm, still well inside the minimum feature.
- The taper prints support-free at 18.9° off vertical; the walls' edges with
  the floor and the interior rings stay sharp (the selector never picks them).
- `tests/test_base_taper.py`, `tests/test_chassis_joint.py` and
  `tests/test_edge_treatment.py` pin the derived inset/angle, the 12 rims +
  6 lips, the chamfer's clean run and the grown bed opening.
