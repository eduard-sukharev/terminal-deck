---
status: accepted
amends: ADR-0019, ADR-0021
---

# The base taper runs the full width of the wall, through the long-wall
# stations' cones; only the corners keep a pad

ADR-0019 gave the Tray's front/rear walls a base taper suppressed inside a
pad around **every** wall station, and ADR-0021 cut deep conical access
cavities for the screw heads right beside those walls. Each pad kept the
full face at its cone mouth and swallowed its column -- but a pad per
station breaks the wall's lean into six flat islands, and the floor face
carries a ring of pads instead of one continuous taper.

## Decision

- **The taper runs through the long-wall stations.** At a side station the
  taper's sloped face at the table lies `inset + mouth − margin` = 2.32 mm
  inside the access cone's mouth plan circle, so the opening is the cone
  flared by the taper -- no sliver of floor skin is left to print as a knife
  edge. Higher up the wall's draft (the cut outside, the fill inside)
  restores the pier around the cone in one constant-thickness slope; the
  pier ring at the taper's top is 1.45 mm and only grows with height, so the
  head pocket's seat zone is never thinner than today.
- **Only the corners keep a pad.** The chamfered corner leaves no run to
  open into: the pad there is the rounded stop the wall's taper starts and
  ends on, set off the corner as before (pad Ø7.80, stop Ø13.80, unchanged).
  Each wall is now a single full-width taper run (214.5 mm) between the two
  corner stops.
- **The build order makes this free.** `case.chassis` cuts the taper, then
  unions the columns, then cuts the clearance holes and the deep cones last
  -- so whatever the taper's fill adds inside a cone's plan circle, the cone
  cutter removes afterwards. The corner pads are unchanged: full face at the
  cone mouth, column swallowed by the stop circle.

## Consequences

- `geometry/base_taper.py` pads only the joint's corner stations
  (`_corner_stations`); `BaseTaper.stations` is the four padded corners and
  `segments` is the single run per wall.
- The HARD check `chassis-taper-pad` covers the four corners; a new HARD
  check `chassis-taper-opens` pins the through-opening: the taper face at
  the table must sit inside the cone mouth (`margin − inset − mouth ≤ 0`)
  and the pier ring at the taper's top must be at least two minimum
  features (`margin − pocket ≥ 2 × min_feature`).
- The floor face at a side station is the cone flared by the 15° taper
  (open to the outside below ~8 mm); the pier wall there starts where the
  flare crosses the cone. The corners' floor rings are unchanged.
