---
status: accepted
amends: ADR-0024
---

# The corner band stations are webbed into the X walls

A corner band station stands `chassis_joint.side_inset` (4.5) from the vertical
front/rear cavity wall and `chassis_joint.station_inset` (6.5) from the vertical
X wall. Its column pierces the front/rear wall -- the chords ADR-0024 fillets --
but it also reaches **2.95 mm** from its axis to the cavity's **inner corner
chamfer** (ADR-0016), while its disc is Ø7.30 (strict, Tray) / Ø7.80 (base and
Deck), i.e. radius 3.65 / 3.90. The disc therefore bit 0.70-0.95 mm into the
45° chop and left one vertical reentrant chord **on the chamfer face** that no
merge fillet could ease.

That chord is not a "missed selection". `column_junction_edges` matches only
edges whose midpoint lies on a listed `|y|` face, and the chamfer face is not
one -- but even if it were, the round could not roll: the gorge between the
chamfer and the cylinder is 36-41°, and a 1.5 mm fillet needs about
`r / tan(theta/2)` = 4.0 mm of surface on each side, while the chamfer face has
1.26 mm from the chord to its outer corner. On the Deck the crease ran the
boss's full 14.15 mm height; on the Tray it was exposed from z ≈ 7.5, where the
base taper's fill buries it.

The stations are **not moved**: the corner screws stay where the band joint put
them.

## Decision

- **Each corner station gets a web into the X wall** (`geometry/corner_web.py`,
  pure data). It is a prism from the column's axis to the X wall, as wide as the
  column and **tangent** to it on both sides (`y ± radius`), so it adds no crease
  against the cylinder. It overshoots into the wall by `_WALL_OVER` (0.5) and is
  clipped by the part's `outer` solid, so it can never break the outer skin (the
  cavity's square corner sits on the outer chamfer plane, the ADR-0016 knife
  edge: an unclipped web would sum past it).
- **The column now merges into both walls** and the corner chop is filled by
  material automatically, as if the station stood in a square corner. The web's
  outward side reaches past the chamfer's foot on the X wall
  (`|y_wall| - inner_corner_chamfer`), which `corner_webs` checks with the same
  numbers the cavity is built from; `slide-chassis-joint-corner-web` (HARD)
  fails the data stage otherwise.
- **The web takes `min(radius)` that is tangent over the height it is built on.**
  The Tray uses its widest column radius (`base_boss / 2`, 3.90) so the frustum
  below the access cone's neck never pokes through the web's inboard face; the
  Deck uses its boss radius (`boss / 2`, 3.90).
- **The web's own junction is eased, not left sharp.** The web leaves one
  vertical chord where its inboard face crosses the X wall -- a clean 90° inside
  corner, unlike the gorge it replaces -- and one straight base edge where that
  face meets the Tray's floor / the Deck's ceiling. Both are picked by
  `edge_treatment.web_junction_edges` / `web_base_edges` and eased in **one**
  variable pass (`fillet_junctions`, `column_fillet` on the chord,
  `boss_base_fillet` on the base), because they meet at a vertex.
- **The corner blend's leftover stub is re-rounded.** A 1.5/0.6 variable pass
  consumes the base edge's wall end and can leave a ~0.86 mm sharp stub beside
  it (OCC cannot roll the cove across the blend it just built). It no longer
  shares a vertex with a fresh chord fillet, so `web_base_residual` rolls it
  separately, backing the cove off until it fits; if nothing fits it is skipped
  as a SOFT warning instead of blocking the build.
- **The webs are applied after the wall-merge pass.** The step a web leaves in
  the front/rear wall face crowds the corner column's inboard chord: OCC must
  fillet that chord on the unbroken face first, or it reports "does not fit"
  and skips the very merge this ADR depends on.

## Consequences

- The corner stations' screws, their access cones, the base-taper pads and the
  keyboard plate's notches are untouched: the web grows inboard of the band, in
  the plan cell the derived corner notch already covers.
- `slide-chassis-seat-clear` is unchanged (the web stays clear of the Deck's
  bearing-clamp seat), and no station moves, so the taper's pad geometry and
  every `chassis-taper-*` check read the same numbers as before.
- `tests/test_chassis_joint.py::test_corner_columns_merge_into_both_walls`
  pins it: no web chord or base edge survives in either half, and no vertical
  concave edge is left on the inner chamfer plane beside a corner station.
- The four corner columns gain a short, fully filleted fin into the X wall.
  It sits inside the corner notch of the keyboard plate, so the plate still
  drops in and the Well ring above is unaffected.
