---
status: accepted
amends: ADR-0014
---

# The Well ring fills back over the plate's notches; wall-adjacent columns
# and the Well bosses fillet-merge into the faces they cross

ADR-0014 cut the Deck's Well ring at the five front-wall band stations, where
a band column's disc crosses the plate's border: the plate was notched (it is
a separate sheet and must give way) and the ring's outer reach was interrupted
with the same rectangle. The rectangles read as five stray cutouts in the
Well, and every column or boss standing against a vertical face kept a sharp
reentrant corner along the chords where its cylinder crosses that face -- a
crack starter in the print, in the most handled part of the case: the twelve
band columns against the cavity walls of both halves, and the plate's eight M2
bosses against the ring's own outer face.

## Decision

- **The ring is continuous.** The plate below stays notched at the five
  front-wall stations (the columns are Deck material; the sheet is not), but
  the ring above fills the same plan area, fused to the band bosses. Nothing
  clashes -- the notches are exactly where the plate has no material -- and
  the Well's outer face reads as one unbroken wall. `case/chassis.py` no
  longer cuts `mounts.notches` out of the ring; `geometry/well_mounts.py`
  still derives the notches for the plate.
- **Columns and Well bosses merge into the faces they cross by a fillet.**
  Wherever a disc crosses one of those faces -- the ten front/rear wall
  stations in both the Tray and the Deck, and the eight M2 bosses on the ring's
  front/rear outer faces -- the reentrant corner along the chord is filleted at
  `chassis_joint.column_fillet` (1.5 mm) by
  `geometry.edge_treatment.merge_column_walls`: the fillet runs along print Z
  in both orientations, so it prints cleanly (the one sanctioned fillet use,
  ADR 0003), and it only adds corner material outside the insert, the head
  pocket and the screw, which sit on the column's axis, far inboard of the
  chord.
- **Applied while the junction edges run the wall's full height.** In the
  Tray the merge runs right after the columns are unioned, before the taper
  fill and cut and before the access cones: the taper's cavity-side fill would
  otherwise narrow the face below the band and cut the chords into the sloped
  region, so it is unioned in after the merge (union order is otherwise free);
  the wedge cut then passes through the columns as before. In the Deck the
  merge runs right after the band bosses, before the insert holes, seat pockets
  and Seam pins. The taper cut and the cones then slice the fillet where the
  wall gives way, and what remains is the eased corner everywhere the wall
  stands beside the column. Applied late, the same edges arrive segmented (the
  cone mouths cut them into stubs a fillet cannot roll off) and OCC refuses
  them.
- **Only the columns' own chords are selected.** `column_junction_edges` picks
  vertical concave edges lying on the faces it is given (`|y|` at the front/rear
  cavity half-depth and, in the Deck, at the Well ring's outer face) and on a
  column's outer surface. Two sets are treated:

  * the ten front/rear wall stations, in both halves (the cavity faces);
  * the eight Well M2 bosses, on the ring's outer faces: each sits
    `bore_margin + hole/2` outboard of that face, so its disc pierces it and
    leaves two chords that take the same fillet. The ring then reads as one
    wall with its bosses.

  The chords a *band* column leaves on the Well ring's outer face stay sharp:
  at the five notched front-wall stations the band boss's chord passes
  ~0.1 mm from the M2 boss's, so no fillet can roll between them (at any
  radius; OCC refuses the pair, the M2 one alone takes it). The chords where a
  column crosses the corner chamfer, and the X-wall chords of the end
  stations, stay sharp too.
- **The chord fit is pinned.** Two HARD checks: `slide-chassis-joint-column-fillet`
  requires `column_fillet` + one minimum feature to fit the tightest wall
  chord (2.66 mm, at the strict column diameter above the cones' necks, where
  the chord is shortest), and `keyboard-mounts-fillet` the same for the Well
  bosses' chord (2.24 mm).

## Consequences

- The five rectangular cutouts are gone from the Well; the plate's notches
  are invisible under the continuous ring.
- The ten wall junctions per half read as one smooth ridge in the print, and
  the Well's outer face runs into each M2 boss as a bead instead of a reentrant
  corner. The chords where a band column crosses the ring's face, the corner
  chamfer and the end stations' X walls stay sharp by design.
- A failing edge is skipped with a SOFT warning by the same isolated,
  divide-and-conquer treatment as the other edge treatments -- the build
  never blocks on a fillet. The access cones clip the fillet at the floor
  and leave a short sharp stub beside each cone mouth (z ~2..6) that OCC
  cannot roll off onto the cone; the cone's own mouth rim (ADR-0023) is the
  eased edge there.
- `test_ring_covers_the_plate_notches` pins the continuous ring,
  `test_columns_merge_into_the_cavity_walls` pins the band columns' merge and
  `test_the_well_bosses_merge_into_the_rings_outer_face` the Well bosses'.
