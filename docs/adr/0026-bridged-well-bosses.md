---
status: accepted
amends: ADR-0014, ADR-0024, ADR-0025
---

# A tight-lip Well boss bridges into the facing wall as a rectangle

The keyboard plate's M2 bosses sit on the Well ring's front and rear lips. The
rear lip is deep enough for the boss to merge only into the ring. The front lip
is not: the boss's 7.00 mm disc sits in a 5.65 mm lip, so it merges into the
ring on one side and leaves a sliver to the facing chassis wall on the other.
A sliver that thin does not print, and the boss is then held by one wall only.

The fix is geometric, not a new fastener. A boss whose lip is narrower than one
wall (`gap < wall`) is grown outboard as a **rectangle**: its inboard end sits
`material.minimum_feature` inside the ring, its outboard end
`material.minimum_feature` inside the facing wall, and its flat sides carry the
wall fillets. The boss then merges with both walls. A boss with a deep lip stays
a plain cylinder.

The bridge stays local to the boss: it does not move the mount, the insert
bore, or the ring. The rectangle's plan is centred on the mount's X and is as
wide as the widened boss, so the Well's plan and the plate's mounting pattern
are untouched.

## Widening

The same change grows every Well M2 boss by `keyboard.mounting.boss_widen`
(1.00 mm, 0.50 mm per side) over the bare insert hole + two `boss_margin`s.
The boss is a structural post, not a bare insert wall. The front lip grows by
half that (`boss_lip_required`) and still fits the 5.65 mm derived front lip.

## Ordering the treatments

A rectangle's vertical wall chords and its base edges meet at vertices, so its
whole junction is eased in one variable pass (`fillet_junctions`). The order
across families is what the crowded geometry allows:

1. The band columns' cavity-wall chords first. They are the HARD joint, and
   their beads bury a bridged rectangle's wall-side chord where the two crowd
   one wall face.
2. Each bridged rectangle's ring-side chord, wall-side chord (where the band's
   bead has not buried it) and base edges together. Both take
   `boss_base_fillet`: the rectangle's chords sit close to the band columns'
   beads, so the larger `column_fillet` would not roll between them.
3. The plain Well bosses' chords and bases, then the band bases.

A crowded edge that OCC cannot roll stays sharp and is reported as a SOFT
warning; it never blocks the build. The HARD checks still require the band
columns' and the plain Well bosses' chords to be filleted.

## Consequences

- Every tight-lip M2 boss merges with both the Well ring and the facing chassis
  wall as one continuous solid, not a sliver. The bridge is a rectangle, so its
  wall intersections are straight vertical chords.
- The rectangle's chords and base edges are selected from its plan rectangle by
  `rect_junction_edges` / `rect_base_edges`; the geometry is not hardcoded in
  the case builder.
- The base round (`boss_base_fillet`, 0.6 mm) is attempted on every rectangle
  and band base; the few edges crowded by a neighbouring bead are skipped with
  a SOFT warning.
- A `boss_widen` of 0 grows the boss only to the bare insert + margin; the
  config key is the single knob for the structural allowance.
