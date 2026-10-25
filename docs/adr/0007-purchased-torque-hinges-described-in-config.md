---
status: accepted
supersedes: ADR-0004, ADR-0005
---

# Purchased torque hinges described in config; the case adapts to them

The printed friction hinge (ADR 0004/0005) looks fragile for field use. The
hinge becomes two purchased metal Torque hinges (reference part:
XK574-6-16, 2 N·m, `docs/reference/torque_hinge_xk574-6-16.avif`). ADR 0004
rejected purchased hinges because their sizes, hole patterns and orientation
vary too much to design around; that objection is answered by describing the
hinge as data and making the case adapt to it:

- A Torque hinge is a Hinge axis plus two Leaves (Base, Lid). Each Leaf has a
  plane (offset/normal from the axis) and holes `(u, v, diameter)` in that
  plane, in the hinge's own frame. A filled-in preset for the reference part
  ships in config.
- Two instances; `x` is configured for one, the other is always mirrored
  about the case centerline.
- The Hinge axis position is derived, not configured: it lies in the closed
  plane, set back behind the rear face by the barrel's or the Cable guard's
  radius plus a swing clearance. On the rear face the Lid's rear edge would
  swing into the Base past 180 deg and the Lid leaf would reach the display;
  set back, the Lid swings clear with no rear roll or notches. Both Leaves
  lie flat inside their shells (Base leaf under the Deck, Lid leaf against
  the Lid's back) — no angled pads.
- Leaves fasten with M4 heat-set inserts in generated bosses (fastener from
  `utilities/fasteners.py`). The case cuts a pocket per Leaf and grows
  bosses per hole.
- HARD checks: every hole lands in material with edge distance, no Leaf or
  hole crosses a Seam (no automatic Seam shift — move `x` or the Seam), the
  Lid's travel does not hit the hinge body.
- The display cable makes one turn around a Cable guard on the Hinge axis,
  facing the HDMI connector: a core sized by the cable's minimum bend radius
  and a ring, part of the Deck, inside a ring that turns with the Lid. Each
  ring covers only the angles no cable entry reaches through the travel, so
  the cover is open at the rear. It carries no load and must not overlap a
  Torque hinge or a Deck Seam.
- The printed hinge (Lid knuckles, Base knuckle, End cheeks, Saddles,
  friction bolt, service caps) is removed, not kept as an option.

## Considered Options

- Keep the printed friction hinge: rejected — fragile.
- Model one specific purchased part: rejected — the next part ordered would
  need a redesign; data description costs little more.
- Captive nuts instead of heat-set inserts: rejected — 2 N·m spread over two
  screws per Leaf (and usually adjusted lower) is within an insert's hold.
- Angled pads matching the hinge's closed angle: rejected — the reference
  hinge travels 196° and mounts flat.
- Keeping `hinge.type: printed` as an alternative: rejected — doubles the
  checks for a variant nobody wants.
