---
status: superseded by ADR-0033
amends: ADR-0010, ADR-0013
---

# The Bearing clamp is as long as its bearing and prints across its collar

The clamp holds the Linear bearing to the Chassis. It was modelled as a
cylindrical head coaxial with the bearing over a rectangular foot 30 mm long,
and printed as modelled. Two things were wrong with that.

**The layers ran along the slide axis.** The collar's hoop was a stack of layer
joints, so the screen's edge load — a lever on the bearing — split the collar
along the weakest plane. The bore's ceiling was also a 505 mm² bridge at 90°.

**The foot was longer than the bearing.** The screen's edge loads reach the
bearing as a lever; the clamp should spread them over as much bearing length as
there is. It makes no sense to run past the bearing, so the clamp is exactly the
bearing's length. The old 30 mm foot also overhung the 16 mm head by 8 mm each
side, which is why a rotation alone could not put the part on its end.

## Decision

- **The clamp is one square prism, bored through, as long as the bearing**
  (`slide.bearing.length`, 19.00 mm; the foot is the same length, so the two ends
  are coplanar flat faces). It prints **standing on an end face**: the layers
  cross the collar, the bore is a hole in a block, and there is **no overhang**
  in either end orientation. The bed face is 123.5 mm² against the 100 mm²
  minimum.
- **The ends stay flat.** The corner chamfer 2.0 breaks the vertical corners
  only; the end faces remain the flat print bed. There is no top-rim chamfer:
  the foot and body share one silhouette, so there is no exposed top rim.
- **No screw holes in the clamp.** A hole through the block is a horizontal
  tunnel once the part stands on its end — an overhang. The screws are carried
  by the Deck's seat instead: the head sits in the Deck's cavity under the seat
  floor, the shaft passes up through the seat's clearance bore and **self-taps
  into the clamp's foot**. The screw pulls the foot down onto the seat floor;
  the Deck prints face down, so its bores are vertical and safe.
- **The load path is compression.** The lid's weight runs rod → bearing → the
  bore's lower half → the foot → the seat floor. The screws carry only the
  preload and the lift; they are not the load path.
- **The reference's dovetail is not adopted.** A dovetail needs a Deck Seam at
  each clamp; ours has one Seam at `x = −14` (ADR-0015), and the clamp is at
  `±94.98`. The pocket already captures the foot on all four sides and the
  bearing captures it vertically, so the dovetail would buy nothing.

## Consequences

- The rear band loses the seat's former 16 mm of length: the seat is 20 → 25 mm
  long with the longer clamp, but the pocket grows only by the 5 mm the clamp
  gained. The SBC and the cable-chain anchor keep their clearance.
- The clamp's bed face and overhang count are now tested in the same way as the
  Deck's and the Bezel's, so a future change cannot silently rotate the part.
- A future clamp that needs real screw purchase must move the screws into the
  Deck's seat, not into the clamp.
