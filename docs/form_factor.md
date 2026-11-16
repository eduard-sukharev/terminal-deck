# Form Factor

Agreed shape of the device. Terms are defined in `/CONTEXT.md`; decisions
with lasting trade-offs are in `docs/adr/`.

The device is a **slider**: a field terminal whose screen lid slides along the
face to reveal a 40% keyboard. The screen stays visible with the device closed,
so it reads as a tablet with a slide-out keyboard. This replaces the clamshell
(ADR-0009).

## References

* **Central unit** (`central-unit.step`) — the form and the slide mechanism:
  two guide rods, bearing clamps, a screen lid sliding over a chassis. Not
  copied: its 335 × 80.6 mm envelope is decorative/accessory volume.
* The earlier clamshell references (NEC MobilePro 900, HP Jornada P6, Micro
  Journal Rev.2 ReVamp) are **retired** with the clamshell. Only their
  handheld-PC size class remains relevant.

No palm rest. No decorative rails, antennas or greebles; the picatinny
interface is functional (accessories) and is not part of the printed shell.

## Envelope

| Dimension | Target | Driver |
|---|---|---|
| Face height (closed) | **140.00 mm, HARD** | travel + bearing + rod clamps + lid bezel |
| Thickness | **57.75 mm, derived** | keyboard/SBC chassis + lid (head + guard + panel + driver) |
| Width | **241.17 mm, derived** | keyboard plate 233.25 + the lid's drafted side wall each side |

The thickness and width were revised by ADR-0013: the guide rods moved under the
display, which removed the side pods (292.39 → 238.92) and added the moving
head and its FPC guard to the lid (50.15 → 57.75). ADR-0014 then grew the
keyboard plate to bear on the Well ring (230.15 → 233.25 wide), so the plate —
not the 231 mm panel — is the width driver and the case is 238.92 → 241.17 mm.
Face height did not move.

The face is the plane carrying the keyboard and the screen. **Face height** is
the extent along the slide; **thickness** is the extent normal to the face.
In the model, the device lies face-up: face height is Y, thickness is Z.

The 140 mm budget, in the order the build computes it:

```
plate depth      = keycap footprint + 2 * (wobble + wall)                 (80.85)
lid stack        = open clearance + bearing + 2 * (Rod clamp + gap)
                   + 2 * end support + lid top bezel                      (51.50)
front margin     = face limit − lid stack − plate depth                    (7.65)
                   floored by wall + the front lip an M2 boss needs (7.00)
keycap top       = front margin + plate depth                              (88.50)
travel           = keycap top + open clearance                             (93.50)
rod span         = travel + bearing.length + 2 * (Rod clamp + clearance)
guide span       = rod span + end supports                                 (137.50)
closed face      = guide span + lid top bezel                              (140.00)
chassis height   = max(keycap top + rear band, closed face)                (140.00)
```

The front margin is a **derived remainder**, not a configured value: ADR-0014's
plate (80.85 mm deep, against the keyboard's 77.75) is what the limit has left
after the lid stack. With the old 77.75 mm plate and a 139.25 face it was
10.00 mm; the plate took 3.10 and the face gave back 0.75, so it is 7.65 mm
(and must stay ≥ 7.00 to host the plate's front M2 boss).

The lid's guide span is fixed by the purchased bearing and the end clamps; it
is the larger half, so the chassis grows to the closed face instead of the lid
overhanging the chassis at the rear. The extra rear band is empty behind the
Bearing-clamp seat (which stays slightly forward of the rear wall), leaving
room for the drag chain.

With the JD40 keyboard on its 80.85 mm plate, one short LM6UU (19 mm) and two
9 mm Rod clamps per rod, the closed face lands at exactly **140.00 mm** — the
limit — and both halves are that deep. The long LM6LUU
(35 mm) does not fit together with the end clamps: the bearing would run under
them at the two extreme poses. A second bearing per rod (≈ 160) does not fit
either. The build fails if the chosen bearing, rod clamps, travel and margins
exceed the face-height limit.

## Poses and kinematics

**Closed pose** — the screen lid covers the whole chassis; the keyboard is
hidden under the lid's flat back. The device reads as one screen panel.

**Open pose** — the lid slides **+Y** (toward the screen end, away from the
user) by the slide travel; the keyboard is fully exposed. The open face height
is `closed face + travel` (≈ 233), and the lid still overlaps the chassis by
the bearing zone, so it cannot come off.

**Slide travel** — the distance the lid moves: keyboard front offset +
keyboard depth + clearance. It is computed, never a constant. The lid's lower
edge must pass the keyboard's *upper* edge, which is why the travel is ≈ 93 mm
and not the keyboard's 77.75 mm depth.

**Retention and stops** — the guide span covers the bearing at both poses (no
exposed rods outside the envelope). A hard stop at each end of the travel;
no detent in v1.

**Guide** — two steel rods, one per side, run along the slide in the screen
lid's open cavity, on the **back panel's inner face**, at the sides of the
display. Each rod is held at both ends by two printed **Rod clamps** screwed
into the back panel. Between the clamps a long **through-slot** in the back
panel lets the **Bearing clamps** — printed clamps that straddle the panel —
slide as the lid moves; the clamp's **cylindrical head** sits above the panel
(inside the lid) at the neck width, its neck passes through the slot and the
joint gap, and its foot is seated in a pocket in the Chassis Deck. The head
does not overhang the slot: the **rod passing through the bearing** is what
retains the lid. Bearings are LM…LUU (config-selectable, default LM6UU,
19 mm), **one per rod**.

**Drag chain** — the display/driver cable crosses the sliding joint in a
drag chain running along the slide axis in a channel behind the screen (one
side, hidden from the keyboard). The channel and its two anchors are reserved
and checked over the whole travel; the chain links are a separate printable
part, not part of the enclosure build.

## Chassis

The chassis is the half that stays on the table. It slides under the lid, so
its top (Deck) is a flat keyboard surface, not a lid. **The face is flat: the
keyboard has no slope, and neither the config nor the build has a mechanism
to tilt it.**

* **Tray + Deck** at a horizontal Parting plane (ADR-0003): Tray = floor,
  walls, ribs, vents, connector cutouts; Deck = the top surface with the
  keyboard Well. The 6 mm joint band is split 3 mm on each half.
* **Vertical Tray walls, drafted lid** — the **Tray's X side walls are
  vertical** (ADR-0019: the accessory rail bolts to a flat, square face), and
  so is the **Deck** all the way to the closed face, so the chassis is one
  width from the table up. The lid is the half that tapers: prismatic at its
  back panel and band, and drafted at `draft.lid` (5–10°) only above them
  toward the face panel, so the two halves meet at the closed face at the full
  width. The front/rear end walls stay vertical on both halves: the guide span
  and rod end clamps are pinned to the 140 mm face budget. The Tray's end walls
  still read as a taper — a 15° base taper that runs from the table up to the
  band's bottom, as a draft (the cavity follows, so the wall keeps its
  thickness), dying into a pad at every band station
  (`geometry/base_taper.py`).
* **Keyboard Well** — a walled recess in the Deck: a 2.0 mm-thick ring of
  walls around a rectangular **Cutout**, descending from the Deck's top face
  (32.30) to the plate's top face (17.80), a 14.50 mm-deep Well. The keycaps
  rise through the Cutout and sit flush with the Deck top; the lid's flat back
  slides 1.00 mm above them. The Cutout is sized by the **keycap footprint
  plus a `wobble` allowance** (0.60 per side): 228.05 × 75.65 → 229.25 ×
  76.85 mm. It is not sized by the plate, and `clearance.shell` no longer
  enters it (ADR-0014).
* **Keyboard plate** — a flat 233.25 × 80.85 × 1.5 mm sheet at z 16.30 (top
  17.80), i.e. the Cutout plus one wall on every side. It **bears on the ring's
  lower faces from below**; there is no floor under it and no floor standoff.
  Its switch-free border is derived, not chosen: 4.05 mm left/right, 4.85 mm
  at the rear edge and 3.88 mm at the spacebar (front) edge, the minimum.
* **Plate fastening** — eight **M2 × 4** screws come up **from below** through
  Ø2.20 clearance holes into heat-set inserts (Ø3.00 × 3.0 deep) in Ø6.00 bosses
  merged to the ring's outer face on the **front and rear
  lips** — four per Section: front-outer, front-at-Seam, rear-at-Seam,
  rear-outer. The boss runs from the plate's top face (17.80) to the Deck's
  inner ceiling (30.30), 12.50 mm: the Deck prints face down, so a boss that
  stopped at the insert would overhang off the ring. The length is derived from
  the 1.5 mm plate grip and the insert;
  the M2 head (Ø3.80 × 2.00) cannot be recessed, so it spans 14.30–16.30 and
  dips 1.85 mm into the Tray, 1.75 mm clear of its inner walls. The front lip is
  5.65 mm for a 5.00 mm boss requirement. The X
  sides have only ~2 mm of Deck rim, so a station that cannot fit the border
  gets a 5.20 × 5.20 mm, r2.0 filleted **Plate ear** protruding past the
  outline; **five Plate notches** (5.30 × 1.45, 1.10 mm bite) yield the front
  border where a Tray/Deck band column reaches into it — the ADR-0015
  centreline column added the fifth, leaving 0.90 mm of border.
* **Plate assembly order** — the plate is screwed to the Deck **before** the
  Tray/Deck join and stays captive after it. Servicing the plate or the
  controller under it means splitting the Tray/Deck joint. The Parting plane
  (16.15) stays below the plate, so it never cuts the Well.
* **Bearing-clamp seats** — a merged seat block with a pocket in the Deck
  behind the keyboard, at each guide-rod X position. The Bearing clamp's foot
  is located in the pocket and bolted from inside the chassis; the clamp's
  cylindrical head rises through the lid's back-panel slot. They are the
  load-bearing interface between the halves.
* **Rear band** — the strip of Deck behind the keyboard, between and around
  the Bearing Clamps, carries the **SBC** plus the cable-chain anchor. It is
  not used for the battery or the USB hub: both are external accessories on
  the rail.
* **Battery** — external, on the accessory rail (as the reference). An
  internal pack, ideally a small one that keeps the SBC alive while external
  packs are swapped, is a later option only if the envelope allows.
* **Accessory rails** — picatinny interface, **not modelled**: the side walls
  get square-nut pockets printed in (nuts inserted during a print pause), so
  user-supplied rail sections bolt on. No rail bars in the shell.
* **Well contents** — the keyboard plate closes the Well from below; the
  **RP2040 controller** sits under the plate, in the chassis thickness. The
  cavity there is clear end-to-end (the only things that cross the Parting
  plane are the joint screws and the eight plate-screw heads). The SBC is in the
  Rear band, not here. The externally
  reachable I/O is the accessory-rail USB-hub module, not a face cutout in the
  chassis.

## Screen lid

* **Bezel + Back plate** (ADR-0011): the lid is two printed parts. The
  **Bezel** is the inverted tray — the front face carries the glass opening and
  the display frame's recess pocket, and its walls run back toward the chassis;
  the panel and the driver sit inside the tray. The **Back plate** is a flat
  4 mm plate that closes it. They butt at the Back's inner face in a
  **prismatic 6 mm band**: the lid only tapers above the band, so the joint
  sits in straight walls. Ten M3 countersunk screws drive from the Back's
  outer face into heat-set inserts in the band — two per long side, one on each
  long side's centreline and one at each corner, the corners on printed posts
  outboard of the Rod clamps. The centreline pair is the Section interlock
  (ADR-0015). The
  front stays clean: all ten fasteners are on the side hidden against the
  chassis when closed, and removing the Back exposes the display and the
  guide hardware.
* **Lid thickness** is the display (6.5) + driver (4.6) stack plus the moving
  head's crown (9.0), the component gap (1.5), the sag allowance (0.5) and the
  FPC guard (1.6): 24.45 mm, leaving the device 57.75 mm thick. It is not set
  by the Rod clamp (ADR-0013).
* **Guide rods** run in the open cavity along the back panel's inner face,
  **under the display**, at `x = ±94.98`. Two Rod clamps hold each rod to the
  panel; the panel's long through-slot between them is the Bearing clamp's
  track. The stance is derived from the lid's band post, the Deck seat and the
  head staying under the panel.
* **FPC guard** — a printed 1.6 mm grille plate tape-bonded to the display's
  back where the moving head sweeps the panel's ribbon: a 0.6 mm channel for the
  flat ribbon over a 1.0 mm grille floor, open at both ends. The head clears its
  underside by the component gap plus the sag allowance, so a deflecting clamp
  can only ever reach the plate.
* **Display** centred. The driver follows the panel: it sits 0.4 mm under the
  display's back (`slide.driver_gap`), inside the 12.6 mm cavity. The ribbon
  runs flat in the guard channel and drops to the driver's FPC connector at the
  guard's west end; do not move the driver off the panel's back.
* **Glass retention** — the panel is held by the tray's front lip and a
  clamp/retainer, not by a ring of exposed screws.
* **Drag chain** — one channel along the slide, behind the panel, on one side.

## Sections and fastening

* Sections (ADR-0003, ADR-0006, ADR-0015) stay: Tray, Deck, Bezel and Back
  plate each split into two, but **each piece has its own Seam**: the Deck and
  the Bezel straight at `x = −14`, the Tray and the Back plate a 45° trapezoid
  at `+10` across the middle and `+18` at the end walls. The keyboard plate
  splits in two along its **Plate Seam** — the row-jogging path between key
  columns (four bands, ends at plate-local x = 0 and x = −50.584, the latter on
  the spacebar side), not the straight cut that passed through switch cutouts.
  Every Section must fit the **220 × 220 × 256 mm** build volume, rejoin
  losslessly, have a flat bed face, and register on its Seam by two **fin-pair
  filament pins** (two printed fins `1.4` thick, `2.0` apart, `2.0` tall,
  `10` long across the Seam, a 45° `1.0` chamfer on the fins' outer top edge; a
  1.75 mm filament offcut glued into the slot — ADR-0006).
* The lid's Back plate is screwed into the Bezel's band (ten countersunk
  M3 from the Back's outer face into heat-set inserts). The chassis splits the
  same way (ADR-0012): at the Parting plane a **prismatic band** carries the
  joint, split 3 mm on each half. Both halves are prismatic (ADR-0019; the
  Tray's end walls carry a base taper only), and twelve
  countersunk M3 × 18 from below thread into heat-set inserts in the Deck's
  band bosses (four corners, three per long side incl. one on the centreline,
  one per short side). The outer band is plain — no relief is cut into it
  (ADR-0016). Nothing stands proud of the keyboard Deck under the hands.
* The two **centreline** long-wall stations sit between the Tray's and the
  Deck's staggered Seams, so each screw clamps a Deck Section to the other Tray
  Section — that is the interlock that keeps the lapped shell from hinging. The
  front centreline column is the fifth Plate notch. The lid carries the same
  centreline pair, so each lid Section keeps four or six of the ten stations.
* The lid's four corner stations sit on posts **inboard of the cavity wall**,
  following the Rod clamp's outer edge (`post_inner = rod_x + rod_clamp.width/2
  + corner_clearance`); nothing widens the case for them any more
  (ADR-0013 retired `slide.joint.corner_post`).
* Seams are staggered between parts screwed to each other — a screwed pair
  laps 24 mm (Tray/Deck, Bezel/Back) or 9.24 mm (Deck/plate) — and never cross a
  structural feature (rib, boss, standoff, clamp, guide channel, rail pocket,
  vent, connector cutout).

## Validation

HARD (the build fails):

* `slide-travel-clears-keyboard` — travel exposes the full keyboard plus
  clearance in the open pose.
* `closed-covers-chassis` — in the closed pose the lid covers the complete
  chassis outline (no internals visible).
* `slide-sweep-clear` — no collision between lid, chassis and components over
  the whole travel.
* `guide-span` — every bearing stays on its rod at both poses, with end
  supports inside the shell; no rod protrudes beyond the closed envelope.
* `clamp-slot-fits` — the back-panel slot contains the Bearing clamp over the
  whole travel.
* `bearing-fits-height` — travel + bearing + supports + bezel ≤ face-height
  limit.
* `chain-path-clear` — the drag chain stays inside its channel and its
  minimum bend radius over the travel.
* `lid-retention` — the lid keeps its bearing overlap in the open pose.
* `section-fits-volume`, `section-rejoins`, `section-bed-face` — unchanged.
* `keys-clear-lid` — keycaps clear the lid's flat back with the configured
  clearance.
* `keyboard-well-parting`, `keyboard-well-ring`, `keyboard-well-cutout` — the
  Parting plane stays below the plate (it never cuts the Well), the ring is one
  wall thick on all four sides, and the Cutout is the keycap footprint plus
  2 × wobble.
* `keyboard-plate-overhang`, `keyboard-plate-border` — the plate reaches one
  wall past the Cutout on every side, and no switch or stabilizer cutout enters
  that bearing border.
* `keyboard-plate-seam`, `keyboard-plate-sections` — the Plate Seam crosses no
  switch/stabilizer cutout and splits the plate into two build-volume Sections.
* `keyboard-mounts-stations`, `keyboard-mounts-fit`, `keyboard-mounts-screw`,
  `keyboard-mounts-head`, `keyboard-mounts-parting` — eight stations, four per
  Section; they fit the lips, the Seam clearance and the ears/notches; the
  stock screw (M2×4) reaches the insert without bottoming out; the screw heads'
  dip below the Parting plane clears the Tray walls and every placed part; and
  no printed plate fastener column crosses the Parting plane (zero floor
  standoffs). `slide-chassis-joint-clear` measures the joint
  stations against the plate's **notched** footprint, not its bounding box.
* `slide-seam-offset`, `slide-seam-stagger`, `slide-seam-clear`,
  `slide-seam-interlock`, `slide-seam-stations` — every Seam stays 10–20 mm off
  the centreline; the Tray/Deck, Bezel/Back and Deck/plate Seams stay at least
  one wall apart over their shared depth; no Seam crosses a band station, a Well
  M2 boss or a bearing seat; a band station on each long wall sits between the
  Tray's and the Deck's Seam; and each Section of each piece keeps at least two
  stations of its joint.
* `slide-seam-pin-fit`, `slide-seam-pin-clear` — the 1.75 mm filament fits the
  2.0 mm slot with glue room, each fin is at the printable minimum and reaches
  5 mm into its Section; every pin site sits on a straight run of its Seam (two
  per Seam) and clears the band stations and the components' solid sub-volumes.

GOAL (reported, not fatal): closed face height, thickness, mass, open pose
height.

## Review renders

Every assembly target is also exported as glTF with one colour per component
and the chassis/lid shells translucent, so Sections, Seams and internals can
be told apart. New parts (Bearing clamp, Rod clamp, guide rod, drag chain, rail pockets)
need their own entry in `utilities/colors.py`.
