---
status: superseded
superseded_by: ADR-0009
supersedes: ADR-0004, ADR-0005
---

# Purchased torque hinges described in config; the case adapts to them

> Superseded by ADR-0009: the slider replaces the clamshell and has no hinge.
> This record is kept for the case-adapts-to-purchased-hardware pattern, which
> the slide guide reuses.

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
- The Lid opens to a comfortable `travel` (120 deg), not the hinge's own
  196 deg: a travel stop rib on the Deck outboard of each barrel, standing
  on the Parting plane behind the rear face, takes the Lid's rear face at
  `travel`. It fills the region the Lid never passes before `travel` (all of
  it inside `setback` of the axis), so it needs no notch in the Lid; a HARD
  check fails if the Lid meets a rib early. Rejected: a hinge with a built-in
  stop (ties the case to one catalogue part) and a tooth in the Cable guard
  (an ~8 mm lever loads the guard, which must stay load-free).
- Hinge torque is sized to the light Lid, not to the part's 2 N·m. Lid
  ~380 g: printed shell and Bezel ~127 g (PETG), panel ~217 g taken as
  mostly glass (231.75 × 64.5 × 6.5 mm, 80 % glass at 2.5 g/cm³, the rest
  ~1.2 g/cm³; unweighed), driver and cable ~35 g. Its centre of mass ~69 mm
  from the axis needs ~0.26 N·m to hold level (~0.13 N·m at the 120 deg
  stop). The Base (~510 g, centre ~60 mm ahead of the rear edge) lifts off
  the table above ~0.30 N·m. So ~0.15 N·m per hinge (`hinge.torque`);
  2 × 0.7 N·m would need the Base held down.
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
