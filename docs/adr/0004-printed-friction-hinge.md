---
status: superseded
superseded_by: ADR-0007
amended_by: ADR-0005
---

# Printed friction hinge with a separate Base knuckle

The Jornada-style pin hinge fused into the Deck and Lid shell can no longer
work: the long Base knuckle (~185 mm) and the Lid roll cross every Seam, and
a 0.2 mm-clearance pin does not hold the screen angle in the field. The hinge
stays printed, with friction from an M3 bolt clamping each corner Lid knuckle
between the Base knuckle and an outer Base end cheek (bolt head and captive
nyloc nut both on the stationary Base side, steel + spring washers between
the rubbing faces, head under the service cap). The Base knuckle becomes a
separate D-profile part with a flat mounting flange, screwed from below to
each Tray Section — a rear bridge across both Tray Seams — and keeps the
display cable tunnel. Lid knuckles stay fused to the Lid shell's side
Sections; the Lid roll is treated as wall and Seams pass through it.

## Considered Options

- Purchased torque/friction hinges: rejected — commercial parts vary too
  much in size, hole pattern, orientation and torque to design around without
  a specific part chosen.
- Bolt head on the Lid side, nut on the Base: rejected — opening the Lid
  turns the bolt and walks the nut, so the friction drifts.
- Short Base knuckles fused to the Tray side Sections plus a separate cable
  sleeve: rejected — loses the rear bridge across the Seams and needs a new
  tunnel part.
