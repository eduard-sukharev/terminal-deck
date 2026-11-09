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
| Face height (closed) | **140 mm, HARD** | slide travel + bearing + lid bezel |
| Thickness | ≈ 56 mm, GOAL | keyboard/SBC chassis + screen lid |
| Width | ≈ 260 mm, derived | keyboard 230.15 / panel 231 + two side pods |

The face is the plane carrying the keyboard and the screen. **Face height** is
the extent along the slide; **thickness** is the extent normal to the face.
In the model, the device lies face-up: face height is Y, thickness is Z.

The 140 mm budget, in the order the build computes it:

```
chassis height   = keyboard front offset + keyboard.depth + rear band
travel           = keyboard front offset + keyboard.depth + open clearance  (≈ 93)
guide span       = travel + bearing.length + end supports
closed face      = max(chassis height, guide span) + lid top bezel
```

With the JD40 keyboard at 77.75 mm deep and one LM6LUU (35 mm), the closed
face lands at ≈ 140 mm. A second bearing per rod (95 → 93 + spacing + 35
≈ 160) does not fit; nor does LM8LUU with two bearings. The build fails if the
chosen bearing, travel and margins exceed the face-height limit.

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

**Guide** — two steel rods, one per side, run along the slide **inside the
screen lid's thickness**, at the sides of the panel, in a C-channel in the
lid's side walls. The bearings are clamped in **Bearing Clamps standing on the
chassis deck behind the keyboard**, rising above the base surface; the clamp
enters the lid's C-channel through a slot. Bearings are LM…LUU
(config-selectable, default LM6LUU), **one per rod**.

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
  keyboard Well and the Parting-plane skirt.
* **Keyboard Well** — a recess in the Deck. The keycaps sit flush with, or
  just below, the Deck's top surface, so the lid's flat back can slide over
  them with a 1 mm-class clearance. The Well no longer serves the clamshell's
  "rim adds no closed thickness" trick; it sets the slide clearance.
* **Bearing Clamps** — two blocks on the Deck behind the keyboard, at the
  guide-rod X positions. Each holds one linear bearing and rises above the
  Deck into the lid's side channel. They are the load-bearing interface
  between the halves.
* **Rear band** — the strip of Deck behind the keyboard, between and around
  the Bearing Clamps, carries the **SBC** and the **USB hub** (the externally
  reachable I/O) plus the cable-chain anchor. It is not used for the battery.
* **Battery** — external, on the accessory rail (as the reference). An
  internal pack, ideally a small one that keeps the SBC alive while external
  packs are swapped, is a later option only if the envelope allows.
* **Accessory rails** — picatinny interface, **not modelled**: the side walls
  get square-nut pockets printed in (nuts inserted during a print pause), so
  user-supplied rail sections bolt on. No rail bars in the shell.
* **Well contents** — the keyboard plate and the **RP2040 controller** sit in
  the Well; the controller is under the plate, in the chassis thickness. The
  SBC is in the Rear band, not here. The hub is the only externally reachable
  I/O surface.

## Screen lid

* **Bezel = inverted tray**: the front face carries the glass opening, and its
  walls run back toward the chassis; the panel and the driver sit inside the
  tray. A **flat back panel** closes it. The front stays clean — the back
  panel is fastened from the back into heat-set inserts, and it is the side
  hidden against the chassis when closed.
* **Guide rods** live in the lid's side walls, beside the panel, in C-channels
  open toward the chassis for the Bearing Clamps.
* **Display** centred; the driver stays directly behind the panel (the FPC
  runs straight; do not move it).
* **Glass retention** — the panel is held by the tray's front lip and a
  clamp/retainer, not by a ring of exposed screws.
* **Drag chain** — one channel along the slide, behind the panel, on one side.

## Sections and fastening

* Sections (ADR-0003, ADR-0006) stay: Tray, Deck and screen lid split into two
  along X with stepped Seams; the keyboard plate splits in two at the central
  key-column gap. Every Section must fit the **220 × 220 × 256 mm** build
  volume, rejoin losslessly, have a flat bed face, and be joined by Seam lugs
  (1.75 mm filament) or screws into bosses.
* The lid's back panel is screwed (heat-set inserts); the chassis Tray/Deck
  use the Parting plane and M3 screws from below. Nothing stands proud of the
  keyboard Deck under the hands.
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
be told apart. New parts (Bearing Clamp, guide rod, drag chain, rail pockets)
need their own entry in `utilities/colors.py`.
