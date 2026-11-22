---
status: accepted
supersedes: ADR-0032
---

# The Bearing clamp is split on the bearing's axis and bolted through the Deck

The clamp holds the Linear bearing to the Chassis. ADR-0032 made it one prism
printed standing on an end face: the crown came within ~1.6 mm of the FPC
guard, and the fastening was split in two — M2 screws joined the halves while
separate M2.5 screws held the foot from inside the chassis.

## Decision

- **The clamp is two halves split on the bearing's axis** (`rod_raise`). The
  lower half runs from the foot's bottom to the axis (the foot plus the bore's
  belly) and prints **foot-down**; the upper half runs from the axis to the
  crown (the bore's roof) and prints **crown-down**. Both split faces are
  flat, each half's layers run parallel to the split, and the bore is a groove
  open toward the bed in both halves — no bridge and no overhang. The bed is
  the foot's bottom and the crown's top.
- **One screw per side does both jobs.** An M3 pan-head screw (`screw`,
  `screw_length` 18.0) is driven **up from inside the chassis**: its head bears
  on the Deck seat's underside, its shank passes the seat floor and the lower
  half with clearance, and it threads into a heat-set insert in the upper
  half. The two halves and the Deck are one stack in tension, with the seat
  floor compressed between the head and the foot. There is no second fastener
  set, and nothing self-taps.
  - *Head below, not above.* A pan head is 2.4 mm tall and the crown is only
    `crown_wall` = 2.0 mm over the bearing, so a top counterbore would have to
    raise the crown into the display cavity / FPC guard. In the chassis cavity
    the head has ~25 mm of room, and no recess has to eat the 2 mm seat floor.
- **The insert's skirt sits on a seat, not on its knurling.** The upper half's
  hole is `insert` wide (Ø4.4) from the crown down to the **seat**, and only
  the screw's clearance (Ø3.2) below it. The long M3 insert (`insert`,
  library `M3-long`, Ø4.6 × 5.0) is pressed in **from the crown, flush with
  it**, and bottoms on that step, so the joint's preload travels in
  **compression** through the skirt into the upper half instead of hanging on
  the knurling. A tension screw always pulls its threaded element *out* of its
  hole toward the head, whichever side the head is on, so this step is what
  makes the insert strong; the plastic *beyond* the insert does not.
  - *Why not a flange or a nut on the crown.* The crown is the part's **print
    bed** (crown-down), so anything proud of it goes below the bed and any
    pocket in it is a bridge. The step inside the hole is the only shoulder
    available, and it needs no extra height.
  - *The stack*: seat floor 2.0 + foot 4.0 + belly 6.0 = 12.0 to the seat;
    M3 × 18 puts the tip 4.0 mm into the insert, 2.0 mm under the crown. The
    builder checks the engagement (≥ half the insert) and the crown.
- **The span and the body width are derived, not configured.**
  `bearing_clamp_screw_span` = 2 × (bore 6.1 + split chamfer 0.5 + min feature
  0.6 + insert hole radius 2.2) = **18.8**; `bearing_clamp_width` = span +
  2 × (insert radius 2.3 + **2 × min feature**) = **25.8**. The ring around the
  insert is two printable minimums wide because the insert now carries the
  joint's preload through its seat. `rod_x` follows the seat bound inboard
  (92.18 → 90.08); the case width, the Well mounts and the FPC guard's reach do
  not change.
- **The crown uses the budget's own wall.** `crown_wall` 2.0, so the printed
  crown is 9.00 — exactly `head_crown` (bearing's top + 2.0) — and the FPC
  guard sits 2.00 above it. The clamp is 18.0 mm tall.
- **The Deck seat keeps a floor.** `seat_height` is `pocket_depth +
  seat_floor` (26.30–32.30, a 2.00 mm floor under the pocket floor). ADR-0032
  had dropped the floor term, leaving the pocket open into the cavity with the
  foot hanging; with the head below, that floor is the screw head's bearing
  face, so it is also what the screw compresses.
- **The print-layer edges are broken — 0.5 mm at 45° — per half, in one
  variable pass**: the **split line** (the outer perimeter, the corner-relief
  lines and the bore's two long edges) becomes a deliberate V-groove at the
  joint; the **bore's end rims** get a lead-in for the bearing; the **bed
  perimeter** (the foot's bottom, the crown's top) is broken like every
  printed Section (ADR-0030). The vertical corners keep their 2.0 mm relief.
  The insert's seat is the one face left as a counterbore ledge: a load seat,
  0.6 mm wide, printed as a self-supporting inward flange, and the only
  overhang either half is allowed.
- **The fastener policy is written down** (`docs/design_spec.md`, `AGENTS.md`):
  ordinary pan-head Phillips screws in plain counterbores, no countersunk
  heads without a decision record. `HEADS` gains `pan`, `head()` defaults to
  it, and `COUNTERSINKS` / `countersink()` leave the library.

## Assembly

With the Deck off the Tray: press the two inserts into the upper half from the
crown, flush; drop the lower half's foot into the seat pocket; lay the lid's
back panel over its belly (the slot passes over the clamp); place the upper
half on the split face from inside the lid's cavity; drive the two M3 screws
up from under the Deck. Then close the band joint.

## Consequences

- The printed clamp is **18.0 mm tall** and **25.8 mm wide** (was 17.5 × 24.6);
  the back-panel slot grows to 26.3 mm and `rod_x` moves to ±90.08.
- The halves are exported as `bearing_clamp_lower` / `bearing_clamp_upper`;
  `bearing_clamp` is the assembled compound.
- The insert is a separate, longer part (`M3-long`); the seat, not the
  knurling, carries the preload.
- The seat floor under the pocket is restored and guarded: the seat build
  refuses a floor thinner than `minimum_feature`, and a probe test checks the
  material between the seat's underside and the pocket floor.
- Servicing the clamp means opening the chassis: the screws are under the
  Deck, unbolted from the Tray side, after the band joint.
