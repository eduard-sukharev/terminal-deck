---
status: accepted
amends: ADR-0016, ADR-0024
---

# The material dihedral picks the edge treatment: inside fillets, outside
# chamfers

`docs/design_spec.md` § Edge Treatment has been "chamfer-first": outside edges
are chopped with a 45 degree chamfer, and a fillet is allowed only as a sparing
exception on hidden inside joints (ADR-0016, ADR-0023, ADR-0024). That reads as
a look preference, and it made the fillet feel optional — something to reach
for when a joint happens to be hidden, rather than the correct treatment for a
whole class of edge.

The physical distinction is not "outside" and "inside" as visual labels, but
the material dihedral at the edge. Measure the angle between the two faces
through the material:

* `<= 90` degrees is a **convex** edge: material on one side only, the edge is
  exposed, and a chamfer chops it into the case's brutal hi-tech look. A round
  here would soften the part toward a consumer appliance and, on a
  downward-facing edge, print as an overhang.

* `>= 270` degrees is a **concave** edge: the same square joint read from the
  void side. The two faces meet in a reentrant corner, which concentrates
  stress and starts cracks in a printed part. A fillet is what relieves it;
  a chamfer leaves the sharp rebate that the stress runs into.

## Decision

- **The dihedral decides, not the visibility.** Concave edges are filleted;
  convex edges are chamfered. Never a chamfer on a concave edge, never a fillet
  on a convex one.
- **Every boss base is filleted.** A boss meets its floor, wall or ring at a
  concave angle, so its base takes the fillet — the same rule as any other
  reentrant corner, not a special case. The same applies to cavity floor/wall,
  wall/wall, boss/wall, boss/floor and rib/floor joints.
- **The fillet must print the way the part is printed.** Judge each joint in
  that part's own print orientation, not in the assembly's Z. A concave joint
  that opens toward that part's bed keeps its 45 degree chamfer
  (`edges.chamfer_factor * wall`): the round approaches horizontal there and
  prints as a curved overhang, while the 45 degree chamfer is the widest
  self-supporting break. A joint that opens away from the part's bed takes the
  round. The Deck prints face down, so its inner ceiling is the bed face and
  its bosses stand on it — they are filleted, not chamfered.
- **Two radii, from config, because the rounds share a corner.**
  `chassis_joint.column_fillet` (1.5 mm) merges a column's chords into the wall
  it crosses (ADR-0024); `chassis_joint.boss_base_fillet` (0.6 mm) rounds the
  base ring, and must stay below `column_fillet`: the base round's endpoints
  land on the chord merge, and OCC cannot roll a fillet off another fillet's
  surface. Every chord merge runs before any base round, so a base round beside
  a neighbouring family's chord cannot block it. The `edges.*` factors size the
  other inside joints. Nothing is hardcoded, and a fillet that does not fit is
  skipped with a SOFT warning rather than blocking the build.
- **`geometry/edge_treatment.py` implements the rule.** `merge_column_walls`
  fillets the chords where columns and Well bosses cross a face (ADR-0024);
  `fillet_boss_bases` rounds the ring where a boss springs from its plane, and
  `boss_base_edges` applies the print-orientation gate (the cove must open away
  from that part's bed). The vertical wall/wall relief and the Seam tab corners
  are filleted; the joints that open toward the part's bed keep the chamfer;
  bed-facing outside edges keep `edges.bed_chamfer`. `PrintOrientation`
  (``geometry/printability.py``) is per part, and each treatment reads it rather
  than assuming assembly Z.

## Consequences

- The rule can be stated in one sentence and checked mechanically: classify the
  edge by its material angle, then apply the matching treatment.
- The Deck's bosses take the round, not the chamfer: the Deck prints face down,
  so its inner ceiling is the bed face and its bosses stand on it. Orientation
  is read per part, never from the assembly's Z — a joint's direction toward the
  bed is a property of how that piece is printed.
- Every Tray column's floor ring is rounded (`boss_base_fillet`), and the Deck
  attempts the same round on every band and M2 boss base. Most band bases take
  it; the rest stay sharp by geometry, not by preference: the two end band
  stations where the corner chop crowds the ring, and most M2 bases where the
  base ring's ends land on the ring's outer face's own ceiling edge. The band
  boss owns the shared corner where the two crowd, and the M2 round is skipped
  with a SOFT warning.
- A concave edge that OCC cannot roll stays sharp and is reported. It is a known
  gap (the crowded Well-ring chords and M2 bases, the X walls, the corner
  chamfer), not a second category of edge.
- `docs/design_spec.md` § Edge Treatment, `CONTEXT.md` and `AGENTS.md` state the
  dihedral rule; the old "chamfer-first, fillets sparingly" wording is retired.
