---
status: accepted
supersedes: ADR-0001
amended_by: ADR-0006, ADR-0012
---

# Split parts into Sections with symmetric Seams; horizontal Parting plane; Deck screwed from below

ADR 0001's two-Half split left the thin plates (Bezel, keyboard plate) as
butt-jointed strips that sag and crack at the Seam, ran the Tray Seam through
a floor rib, and gave the Deck no flat face to print on. We now split parts
into Sections: Tray and Lid shell into three (left/center/right, stepped Seams
mirrored about the centerline, ≈±40 mm); Bezel and Deck into two along a
straight Seam at x=0 that reads as a deliberate design line; the keyboard
plate into two at the central key-column gap. Seams are staggered only
between parts screwed to each other (Base and Lid may coincide in X), and a
Seam may never cross a structural feature (rib, boss, standoff, column,
cradle, vent, lug) — derived features (ribs) move to clear it, and the build
fails otherwise.

Thin plates are held at the Seam by extra screws into solid bosses rather
than stiffened: the keyboard plate gets 8 M2 screws on Tray-floor standoffs
(4 at the edges, 2 per Section within 1u of the Seam); the Bezel 8 exposed
countersunk M2 screws (4 corners, one above and one below the glass on each
side of the Seam).

The Tray/Deck joint moves down from the Deck's edge to a horizontal Parting
plane at a configured fraction of the front wall height (clamped to min/max
mm), so the Deck has a flat print face and a wall skirt. The Deck is held by
M3 screws driven from below through counterbored Tray columns into heat-set
inserts in Deck bosses (at least one per Section near the Seam), so no screw
head sits under the hands; this replaces the M2.5 deck standoffs.

## Considered Options

- Ribs/stiffeners on the thin plates: rejected — they add thickness and still
  leave a butt joint carrying the load; screws into the bosses beneath are
  already there.
- Countersunk Deck screws from above: rejected — heads under the palms, and
  the Deck frame would need to be thick enough to take the countersink.
- Two Sections for Tray and Lid shell: rejected — a single centre Seam with
  long cantilevered Halves; three Sections keep each Seam short-spanned and
  the layout symmetric.

## Consequences

- Build targets become `<part>_left` / `_center` / `_right`.
- Every Section must have a flat bed face and a declared print orientation
  (HARD); overhangs beyond 45° are reported (SOFT) — the Deck prints Parting
  face down with supports under its sloped roof.
