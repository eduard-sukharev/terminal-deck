---
status: accepted
amends: ADR-0015, ADR-0025
---

# The printed Section's bed edge is broken, and the visible Seam is a V-groove

ADR-0025 settled the *treatments*: a convex edge is chamfered, a concave one
filleted. It left the *bed* edge — the outer boundary of the face a Section
prints on — mostly untreated. `edge_treatment.bed_chamfer` existed and was
documented as "each Section's bed-face outer edge", but no builder ever called
it: the Tray's floor and the Deck's closed face kept a razor edge, and the
Seam, being a plain butt joint, showed as a hairline that cannot be hidden.

The Seam is worse than a hairline. The Tray (and the Back plate) split on a
**trapezoid** (ADR-0015): a 45 degree jog in the middle of the part is a *bent*
line on the visible face, and no amount of fit tolerance makes it read as a
design feature. A deliberate 45 degree V-groove does.

## Decision

- **Break every printed Section's bed edge at `edges.bed_chamfer` (0.5 mm), per
  Section.** The Tray prints floor down, so its bed face is the floor; the Deck
  and the Bezel print face down, so theirs is the closed face. The break is
  applied *after* the split (`edge_treatment.chamfer_sections`), which is the
  whole point: on a Section the Seam is part of the bed face boundary, so each
  half gets a 0.5 mm bevel along it and the joined halves show a 1 mm wide,
  0.5 mm deep V-groove exactly on the Seam. No extra knob: the same break that
  fights the elephant's foot also makes the Seam deliberate.
- **The whole reference part is the union of the treated Sections.** The
  exported `chassis_*`/`screen_lid_*` whole, the assembly and the glTF must
  show the same edges as the printed pieces, so `build_tray`/`build_deck`/
  `build_bezel` split, break and rejoin. The re-split in `main.sections_of` is
  lossless because the V-groove apex lies on the Seam plane.
- **Only a near-vertical wall takes the break.** A symmetric chamfer on a wall
  that flares outward going up is no longer a 45 degree bevel but a shallower,
  unsupported overhang, and OCC mis-trims it — on the Tray's tapered base foot
  it grows a spurious wedge below the bed instead of losing the corner.
  `edge_treatment.bed_edges` therefore drops a bed edge whose other face is
  more than ~11.5 degrees off vertical (`_SLOPED_BED`). On the Tray that leaves
  the *X-wall* floor edges, the corner chops and the corner-pad stop arcs; the
  tapered front/rear foot keeps the base taper itself as its break. The Deck's
  and the Bezel's walls are vertical or drafted 5-10 degrees, so they keep the
  full perimeter.
- **The Bezel's face perimeter is the one accepted overhang.** Its side walls
  are drafted, so the symmetric chamfer is a ~48.5 degree bevel — just over the
  45 degree rule, but a 0.5 mm first-layer bridge, the same class as the Tray's
  elephant's-foot break. `test_the_bezel_has_no_overhang_where_it_prints_face_down`
  ignores faces inside `2 * bed_chamfer` of the bed plane and still forbids any
  ledge on the band posts.
- **The access-cone mouths keep their own break.** `chamfer_cone_cut` grows
  each mouth to `mouth_radius + 0.5`, and the through-stations' half-rims sit
  on the Tray floor's outer wire. `bed_edges` skips them by the station discs
  (`mouth_radius + size`), or a second bevel would eat the corner pads' ring
  that `chassis-taper-pad` checks. `chassis-taper-*` are unchanged.
- **OCC lies.** `cad_helpers._assert_inside` rejects any edge treatment whose
  result leaves the input's bounding box (a chamfer/fillet can only round in
  place; a concave fillet grows the volume *inside* the box). Without it the
  tapered-foot corruption above was exported as valid geometry.

## Consequences

- `main.sections_of` and `Chassis.tray_sections`/`deck_sections` re-split the
  treated union; the Sections are the same beveled pieces.
- `_SLOPED_BED` is the seam between "OCC can" and "the bevel is honest": the
  Tray's 18.9 degree foot is out, the Bezel's 5-10 degree draft is in.
- A future fully-chamfered Tray foot needs a boolean bevel along the taper, not
  a `chamfer_edges` call; the taper's own slope is the current break.
