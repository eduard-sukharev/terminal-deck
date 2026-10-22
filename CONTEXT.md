# Cyberdeck — Domain Glossary

A symmetric clamshell field terminal for debugging 3D printers. Form-factor
references: NEC MobilePro 900 and HP Jornada (handheld PC class).

## Terms

**Base** — The bottom half of the clamshell: holds the keyboard, SBC,
controller, battery and I/O. Made of the Tray and the Deck.
_Avoid:_ using "base" for any part of the Lid.

**Tray** — The Base's floor and walls (bosses, ribs, vents, cutouts).

**Deck** — The Base's top surface the keyboard sits in; sloped by the deck
slope.

**Lid** — The top half of the clamshell: holds the display and its driver.
Same footprint as the Base, thinner. Made of the Lid shell and the Bezel.

**Visor** — The Lid's outer lip that takes up the Deck's slope, so the closed
clamshell has no wedge-shaped gap. When the Lid is open it sits along the top
edge of the screen (after the Micro Journal Rev.2 ReVamp).

**Well** — The recess in the Deck the keyboard sits in, bounded by a rim.

**Lid shell** — The Lid's rear (outer) tray.
_Avoid:_ lid base.

**Bezel** — The Lid's front plate with the glass opening.

**Envelope** — The outer footprint (width × depth) shared by Base and Lid.

**Rear strip** — The band along the hinge edge of the Base holding the USB
hub and battery.

**Section** — One of the printable pieces a part is split into along X to
fit the build volume: left/right for two-piece parts (Bezel, Deck, keyboard
plate), left/center/right for three-piece parts (Tray, Lid shell), whose two
Seams mirror each other about the centerline. Sections are joined by screws
and bosses.
_Avoid:_ "Half" (a part may have three Sections); "half" for Base vs Lid —
say Base or Lid.

**Seam** — Where two Sections of one part meet. Seams are staggered between
parts screwed to each other (they don't line up) and never cross a structural feature (rib, boss,
standoff, cradle, vent). Outward-facing Seams are stepped lines
(`__--__--__`) seen from above, with plain butt-joint step faces held by
screws and bosses — except the Bezel's and the Deck's, which are straight on
the centerline and echo each other. The Bezel's screws are exposed as a design
element; the Deck's are driven from below so nothing stands proud under the
hands.

**Parting plane** — The horizontal plane where the Deck meets the Tray,
part-way up the Base's walls rather than at the Deck's edge, so the Deck has a
flat face and a skirt of wall below the keyboard surface.
_Avoid:_ "seam" for the Tray/Deck joint — a Seam joins Sections of one part.

**Merged boss** — A boss, column or lug standing close enough to a wall
that it is fused into it instead of standing free; the wall then serves as
part of its sleeve, so its bore may sit closer to the wall than a free boss's.

**Core component** — A purchased hardware item modelled to its measured
size: SBC, USB hub, battery cells, display panel, display driver, controller,
keyboard. Distinct from case parts (Tray, Deck, Lid shell, Bezel, hinge),
which are generated around them.
