---
status: accepted
amends: ADR-0003, ADR-0005
amended_by: ADR-0015
---

# Sections joined for good by glued filament pins

ADR 0003 held the Sections of the Tray and the Lid shell together with Seam
lugs carrying a horizontal M2 screw into a heat-set insert, and ADR 0005 gave
the Deck one such lug. Those screws are never meant to come out, and they run
along X a few millimetres above a floor or a Parting plane, where neither a
hand nor a screwdriver can get at them. The M2 insert also sets the lug's size
(5.4 mm square): too tall for the Deck's front skirt, which has 4.5 mm between
the Parting plane and the keyboard plate, so the Deck Seam had only its rear
lug.

**Revised by ADR-0015; see "The fin-pair retainer" below: the lug and its
bore are gone.** A pin no longer needs a drilled block: it needs two walls to
sit between. Every Seam now carries **two pairs of parallel fins** that
straddle it, with a slot between the fins of each pair. A length of 1.75 mm
filament is glued into each slot while the Sections are put together. The pin
therefore *aligns* the two Sections and holds them while the screws that cross
the Seam are still out (they can be glued before the other half of the case
exists), and it adds a little stiffness afterwards; it is not the structural
joint. Fin thickness, slot, height, length and the outer chamfer are the
`seam_pin:` config section; where each pair goes is `slide.seam_pin_sites`
(it depends on what the part holds inside, so it is a placement, not a
formula).

## The fin-pair retainer

- **Two fins, one slot.** A pair is two walls `fin` (1.4 mm) thick, `gap`
  (2.0 mm) apart, `height` (2.0 mm) tall above the surface they grow from, and
  `length` (10 mm) long across the Seam, so each Section prints **5 mm** of
  every fin. The pin is a filament offcut glued into the 2.0 mm slot: 0.25 mm
  of total clearance is glue room and print tolerance, where the old bore was a
  0.15 mm fit that had nowhere for the glue to go.
- **The slot faces stay square.** They are what locates the pin, so they are
  untouched. The **outer top edge** of each fin takes a 45 degree `chamfer`
  (1 mm), which keeps the fin from ending in a sharp 1.4 mm knife and prints
  without support; nothing is chamfered between the walls.
- **Fins grow from what the part already has.** They stand on the Tray's
  floor (up), hang from the Deck's top skin and the Bezel's front panel
  (down), and stand on the Back plate's inner face (up).
  `geometry.seam_joint.pin_planes` is the single source for those four
  surfaces; the case builders read it through the frame and the validation
  recomputes it from the budget, and the frame fails the build if the two
  disagree.
- **Pins are added to the whole part, then the Seam is cut.** The split saws
  every fin in half, so each Section gets its own half with no extra feature
  and the Sections still rejoin losslessly.
- **No ledges, no bores, no sleeves, no cubes.** The retainer is the two
  printed walls; a pin that has to be fed through a bore is exactly the
  unreachable screw this ADR retired.

## Why the Seams need them

The Seams themselves already interlock in plan: the Tray's (and Back plate's)
45 degree trapezoid cannot slide, and the band screws clamp the shell down.
But a **straight** Seam -- the Deck's and the Bezel's -- has no key at all, and
even a keyed Seam gives nothing while the part is being put together. The fins
are the registration: two pins fix the relative position in X, Y and rotation,
which is what an assembler has to hold by hand otherwise while reaching for the
screws. That is why there are two pairs per Seam and why the sites are chosen
in the part's *free* interior (the checked list is in `slide.yaml`).

## Considered Options

- Keep the M2 screw/insert lugs: rejected -- unreachable to drive, never
  undone, and too big for the Deck's front skirt.
- A drilled lug with a glued-in pin (this ADR's earlier form): rejected --
  the block is more material and more print time than two fins for the same
  alignment, and the bore is a tolerance on two axes instead of one slot.
- Blind holes with a dowel glued in: rejected -- the dowel has to be cut to
  length beforehand; the open slot takes an offcut and any length.
- A ledge or a cap over the slot: rejected -- it retains the pin without glue
  but adds an overhang and a second contact face for no alignment gain.

## Consequences

- Tray, Deck and Lid shell can't be taken apart into Sections again without
  cutting the pins or breaking the glue; a broken Section means reprinting and
  re-gluing.
- Each slot must stay open and reachable from the cavity side while the pin is
  glued: the Tray's pins go in before the Deck, the Deck's and Bezel's before
  the part is closed, the Back plate's before it is screwed on.
- The fins are small printed features, so they are checked: `slide-seam-pin-fit`
  (pin in slot with glue room, fin at the printable minimum, 5 mm engagement)
  and `slide-seam-pin-clear` (every site on a straight run of the Seam, two per
  Seam, and clear of the band stations and the components' own solid volumes).
- Screws remain wherever one part is held to another (Deck columns, Bezel,
  keyboard plate, hinge), so the case still opens for service; only the
  Sections of one part become one piece once assembled.
