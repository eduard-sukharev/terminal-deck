---
status: accepted
amends: ADR-0004
amended_by: ADR-0006
---

# Base knuckle seated in the Deck; end cheeks fused to the Deck; Deck Seam lug

ADR 0004 screwed the Base knuckle to the Tray from below, through a flange
under the floor and a web behind the rear wall that also tied the end cheeks
to the bar. The Tray's rear wall stops at the Parting plane and the hub and
battery stand against it, so only the centre Tray Section could take a floor
screw; the other Sections were reached by horizontal screws through the web
into the Deck's rear skirt. The result was a bracket over every rear-wall port
and a step under the floor.

The Base knuckle is now the bar alone (D-profile, cable tunnel, bolt lands,
nut pockets) and sits in a pocket in the Deck's rear edge, its flat against
the Deck. The end cheeks are fused to the Deck, one per Deck Section, so each
friction bolt runs from a Deck cheek through the Lid knuckle into a nut in the
bar: the bar is held axially by the two bolts and ties the two Deck Sections
together. A saddle block on the inside of the Deck's rear skirt backs the
bar's flat at each land, from the Parting plane up to the Deck roof, and takes
the friction torque; the tunnel's middle stays open for the display cable.
Nothing of the hinge reaches below the Parting plane, so the Tray's rear wall
and its ports are clear.

The Deck Sections are also joined to each other by a Seam lug on the Seam
(the same horizontal M2 lug as the Tray's), where the Seam has room above the
Parting plane — at the rear skirt in the current layout; the keyboard fills
the front skirt.

## Considered Options

- Keep the Tray mounting with the flange moved inside onto the floor:
  rejected — the hub and battery still leave no room for bosses on the side
  Tray Sections.
- Screws into the bar (from below or through the saddle block into inserts in
  the lands): rejected at the 13 mm knuckle diameter — an M3 insert either
  meets the bolt bore or breaks out of the round. A larger `hinge.diameter`
  would allow it at the cost of thickness.
- A thin spine from cheek to cheek under the Lid knuckles' swing, inset into
  the rear skirt: rejected — keeps the part in one piece but needs a slot in
  the Deck and still has nothing to screw into.

## Consequences

- The Deck prints Parting face down with supports under the cheeks' lower
  halves, which stand behind the rear wall (as under its sloped roof).
- The Base knuckle can only be removed with the Deck off; the friction is
  still set from outside under the service caps.
- Supersedes ADR 0004's "screwed from below to each Tray Section" and the
  web/flange; the rest of ADR 0004 stands.
