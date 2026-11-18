---
status: accepted
amends: ADR-0019, ADR-0022
---

# The access cones' outside edges carry the case's one fillet; the walls'
# edges with the floor stay sharp

ADR-0019's base taper and ADR-0022's through-station flare leave the Tray's
lowest band of outside edges sharp: where the access cone leaves the floor
face (the mouth ring), where the taper's slice flares a cone open (the lip),
and along the whole length of both walls where they meet the floor. A row of
knife edges at the part most handled and most visible.

## Decision

- **Fillet the cones' own outside edges, nothing else.** The fillet lives on
  exactly two edge classes, selected by adjacency (a conical face against a
  plane of the right attitude), never by a swept region: the **mouth rims**,
  where an access cone or a column frustum leaves the floor face (a
  horizontal plane at the bed), and the **lips**, where the taper's *outer*
  sloped face flares a cone open (a plane tilted `taper_angle` with a
  downward normal). `geometry.edge_treatment.cone_cut_edges` is the single
  selector; the long edges where the front/rear walls meet the floor are
  straight lines and can never match it.
- **Rims at `chassis_joint.taper_fillet` (1.0 mm), lips radius-limited.**
  The rim is a near-90° edge, so an r fillet runs only ~1.02 mm along the
  bed, leaving 1.30 mm of the tightest landing strip (a through-station's,
  2.32 mm wide). The lip is a shallow ~13.9° dihedral (the taper minus the
  cone's half-angle), so an r fillet climbs the cone by `r × cot(6.95°)` ≈
  8.2×r: the largest radius that stops one minimum feature below the head
  pocket's neck (z 12.50) is **0.47 mm**, and that is what the lips take.
  Filleting a lip at the rim radius would seal the driver cone against the
  pocket.
- **Everything interior stays sharp.** The rings where a cone breaks the
  cavity floor (z = wall), the flares against the cavity-side draft (their
  slope faces up, `nz > 0`), the pocket's neck rings and the clearance holes
  are none of them selected. The case stays chamfer-first: this fillet is
  the one fillet on an outside face, allowed because a chamfer there would
  read as a second, wider taper.
- **The bed is re-trimmed to z = 0 after the fillet**, in case a fillet
  surface wanders a hair below the plane (a bspline face's control hull can
  overshoot the surface); the trim guarantees the printed bed is exact.

## Consequences

- `config.chassis_joint.taper_fillet` (1.0 mm) sizes the rims; the applied
  lip radius is derived (`geometry.base_taper.lip_fillet_limit`) and reported
  as the GOAL `taper-lip-fillet-radius`, with a SOFT warning when it clamps
  the configured radius.
- The HARD check `chassis-taper-fillet` pins the rim fit (tangent run plus
  one minimum feature inside the through-stations' landing strip) and that
  the lip admits a token fillet below the pocket's neck.
- A failing edge is skipped with a SOFT warning by the same isolated,
  divide-and-conquer treatment as the other edge treatments -- the build
  never blocks on a fillet.
