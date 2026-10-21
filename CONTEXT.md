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

**Half** — One of the left/right printable pieces a part is split into along
X to fit the build volume; Halves are joined by screws and bosses.
_Avoid:_ "half" for Base vs Lid — say Base or Lid.

**Seam** — Where two Halves of one part meet. Seams are staggered between
parts (they don't line up), and every outward-facing Seam is a stepped line
(`__--__--__`) seen from above, not a straight cut; the step faces are
plain butt joints held by screws and bosses.

**Core component** — A purchased hardware item modelled to its measured
size: SBC, USB hub, battery cells, display panel, display driver, controller,
keyboard. Distinct from case parts (Tray, Deck, Lid shell, Bezel, hinge),
which are generated around them.
