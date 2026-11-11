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
| Face height (closed) | **140 mm, HARD** | travel + bearing + rod clamps + lid bezel |
| Thickness | **57.75 mm, derived** | keyboard/SBC chassis + lid (head + guard + panel + driver) |
| Width | **238.92 mm, derived** | panel 231 + a drafted side wall each side (nothing else) |

The thickness and width were revised by ADR-0013: the guide rods moved under the
display, which removed the side pods (292.39 → 238.92) and added the moving
head and its FPC guard to the lid (50.15 → 57.75). Face height did not move.

The face is the plane carrying the keyboard and the screen. **Face height** is
the extent along the slide; **thickness** is the extent normal to the face.
In the model, the device lies face-up: face height is Y, thickness is Z.

The 140 mm budget, in the order the build computes it:

```
travel           = keyboard front offset + keyboard.depth + open clearance  (≈ 93)
rod span         = travel + bearing.length + 2 * (rod clamp + clearance)
guide span       = rod span + end supports
closed face      = guide span + lid top bezel                               (≈ 139)
chassis height   = max(keyboard front offset + keyboard.depth + rear band,
                       closed face)
```

The lid's guide span is fixed by the purchased bearing and the end clamps; it
is the larger half, so the chassis grows to the closed face instead of the lid
overhanging the chassis at the rear. The extra rear band is empty behind the
Bearing-clamp seat (which stays slightly forward of the rear wall), leaving
room for the drag chain.

With the JD40 keyboard at 77.75 mm deep, one short LM6UU (19 mm) and two 9 mm
Rod clamps per rod, the closed face lands at ≈ 139.3 mm and both halves are
that deep. The long LM6LUU
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
* **Drafted side walls** — the X side walls taper at `draft.angle` (5–10°),
  but only in the **Tray**, from its base up to `band_z0` (≈ 13 mm). The Tray
  is prismatic from `band_z0` to the Parting plane, and the **Deck is purely
  prismatic** all the way to the closed face, so the upper silhouette stays
  straight. The lid is prismatic at its back panel and band, and tapers only
  above them toward the face panel, so the two halves meet at the closed face
  at the full width. The front/rear end walls stay vertical: the guide span
  and rod end clamps are pinned to the 140 mm face budget.
* **Keyboard Well** — a recess in the Deck. The keycaps sit flush with, or
  just below, the Deck's top surface, so the lid's flat back can slide over
  them with a 1 mm-class clearance. The Well no longer serves the clamshell's
  "rim adds no closed thickness" trick; it sets the slide clearance.
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
* **Well contents** — the keyboard plate and the **RP2040 controller** sit in
  the Well; the controller is under the plate, in the chassis thickness. The
  SBC is in the Rear band, not here. The externally reachable I/O is the
  accessory-rail USB-hub module, not a face cutout in the chassis.

## Screen lid

* **Bezel + Back plate** (ADR-0011): the lid is two printed parts. The
  **Bezel** is the inverted tray — the front face carries the glass opening and
  the display frame's recess pocket, and its walls run back toward the chassis;
  the panel and the driver sit inside the tray. The **Back plate** is a flat
  4 mm plate that closes it. They butt at the Back's inner face in a
  **prismatic 6 mm band**: the lid only tapers above the band, so the joint
  sits in straight walls. Eight M3 countersunk screws drive from the Back's
  outer face into heat-set inserts in the band — two per long side and one at
  each corner, on printed posts outboard of the Rod clamps. The
  front stays clean: all eight fasteners are on the side hidden against the
  chassis when closed, and removing the Back exposes the display and the
  guide hardware.
* **Lid thickness** is the display (6.5) + driver (4.6) stack plus the moving
  head's crown (9.0), the component gap (1.5), the sag allowance (0.5) and the
  FPC guard (1.6): 24.45 mm, leaving the device 57.75 mm thick. It is not set
  by the Rod clamp (ADR-0013).
* **Guide rods** run in the open cavity along the back panel's inner face,
  **under the display**, at `x = ±93.86`. Two Rod clamps hold each rod to the
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

* Sections (ADR-0003, ADR-0006) stay: Tray, Deck and screen lid split into two
  along X with stepped Seams; the keyboard plate splits in two at the central
  key-column gap. Every Section must fit the **220 × 220 × 256 mm** build
  volume, rejoin losslessly, have a flat bed face, and be joined by Seam lugs
  (1.75 mm filament) or screws into bosses.
* The lid's Back plate is screwed into the Bezel's band (eight countersunk
  M3 from the Back's outer face into heat-set inserts). The chassis splits the
  same way (ADR-0012): at the Parting plane a **prismatic band** carries the
  joint, split 3 mm on each half. Only the Tray below `band_z0` is drafted
  (7°); the Tray's half-band and the whole Deck are prismatic, and ten
  countersunk M3 × 18 from below thread into heat-set inserts in the Deck's
  band bosses (four corners, two per long side, one per short side). Both
  halves carry a 10 × 0.8 mm scallop at each station, straddling the seam.
  Nothing stands proud of the keyboard Deck under the hands.
* The lid's four corner stations sit on posts **inboard of the cavity wall**,
  following the Rod clamp's outer edge (`post_inner = rod_x + rod_clamp.width/2
  + corner_clearance`); nothing widens the case for them any more
  (ADR-0013 retired `slide.joint.corner_post`).
* Seams are staggered between parts screwed to each other and never cross a
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

GOAL (reported, not fatal): closed face height, thickness, mass, open pose
height.

## Review renders

Every assembly target is also exported as glTF with one colour per component
and the chassis/lid shells translucent, so Sections, Seams and internals can
be told apart. New parts (Bearing clamp, Rod clamp, guide rod, drag chain, rail pockets)
need their own entry in `utilities/colors.py`.
