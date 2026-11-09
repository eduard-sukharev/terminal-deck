# Cyberdeck — Domain Glossary

A **slider** field terminal for debugging 3D printers: the screen lid slides
along the face to reveal a 40% keyboard, so the screen stays visible when the
device is closed. Form reference: the central-unit slider
(`central-unit.step`). Decisions with lasting trade-offs are in `docs/adr/`.

## Terms

**Slider** — The device's form: two halves stacked on the face, the upper one
sliding along the face to expose the keyboard. Replaces the clamshell
(ADR-0009).
_Avoid:_ "clamshell", "laptop".

**Chassis** — The lower half that rests on the table: holds the keyboard, the
SBC, the controller, the USB hub, and the Bearing clamps. Made of the Tray and
the Deck. The battery is not inside it; it hangs on an Accessory rail.
_Avoid:_ "Base" (retired clamshell term).

**Screen lid** — The upper half that slides: carries the display, its driver,
the guide rods and the drag chain. Made of the inverted-tray Bezel and the
flat back panel.
_Avoid:_ "Lid" alone (ambiguous with the retired clamshell Lid), "cover",
"screen".

**Face** — The plane carrying the keyboard and the screen. The device is
modelled face-up.

**Face height** — The device's extent along the slide (the closed device's
long side, 140 mm target). One of the two in-plane dimensions; the other is
width (X).
_Avoid:_ "depth" (means the same as thickness in some contexts), "Z" in prose
(the model's Z is thickness).

**Thickness** — The extent normal to the face: chassis plus screen lid.

**Closed pose** — The pose the device is carried in: the screen lid covers the
whole Chassis, the keyboard is hidden, and the device reads as one screen
panel.

**Open pose** — The pose the device is typed in: the screen lid has slid by
the Slide travel and the keyboard is fully exposed. The open face height is
larger than the closed one.

**Slide travel** — How far the screen lid moves to go from the closed to the
open pose. Set by the keyboard's position and depth plus clearance, because
the lid's lower edge must pass the keyboard's upper edge — not by the
keyboard's depth alone.
_Avoid:_ "stroke", "throw".

**Guide rod** — One of the two steel rods the screen lid rides on. It runs
inside the Screen lid's thickness, beside the panel, in a C-channel in the
lid's side wall.
_Avoid:_ "rail" (an Accessory rail is a different part), "shaft".

**Linear bearing** — A purchased LM…LUU ball bushing riding on a Guide rod.
One per rod; its length is part of the Face-height budget.
_Avoid:_ "bushing" when the purchased part is meant.

**Bearing clamp** — The block on the Chassis Deck behind the keyboard that
holds a Linear bearing and rises above the base surface; it enters the Screen
lid's C-channel through a slot and is the load-bearing interface between the
halves.
_Avoid:_ "housing", "bearing block".

**C-channel** — The slot in the Screen lid's side wall that contains the Guide
rod and lets the Bearing clamp reach it. Open toward the Chassis.

**Drag chain** — The articulated cable carrier that lets the display/driver
cable cross the sliding joint. It runs along the slide axis in a channel
behind the screen; its channel and anchors are part of the shell, its links are
a separate printed part.
_Avoid:_ "cable guard" (retired clamshell term), "cable track".

**Accessory rail** — The picatinny-style mounting interface on the Chassis's
side walls. The shell carries square-nut pockets (nuts inserted during a print
pause); the rail bars themselves are user-supplied accessories, not printed
shell parts. The external battery pack hangs on one.

**Rear band** — The strip of Deck behind the keyboard, between and around the
Bearing clamps. Holds the USB hub and the drag-chain anchor; not used for the
battery.

**Well** — The recess in the Deck the keyboard sits in. In the slider it sets
the clearance under the Screen lid's flat back; the keycaps sit flush with, or
just below, the Deck's top surface.
_Avoid:_ "pocket".

**Tray** — The Chassis's floor and walls (bosses, ribs, vents, cutouts); the
lower part of the Parting plane.

**Deck** — The Chassis's top surface: the keyboard Well, the Bearing clamps and
the Rear band sit on it; its skirt meets the Tray at the Parting plane.

**Parting plane** — The horizontal plane where the Deck meets the Tray,
part-way up the Chassis walls, so the Deck has a flat face and a wall skirt.
_Avoid:_ "seam" for the Tray/Deck joint — a Seam joins Sections of one part.

**Envelope** — The closed device's outer dimensions (width × face height ×
thickness), the number the design minimises.

**Section** — One of the printable pieces a part is split into to fit the
build volume. Wide parts split into two along X; the keyboard plate splits at
the central key-column gap. Sections of one part are joined by Seam lugs;
thin plates are held by screws into the part behind them.
_Avoid:_ "half" (a part has Sections, not halves).

**Seam** — Where two Sections of one part meet. Seams are staggered between
parts screwed to each other and never cross a structural feature (rib, boss,
standoff, clamp, guide channel, rail pocket, vent).

**Seam lug** — A pinned joint straddling a Seam: a block shared by the two
Sections with a glued filament pin through both. Joins Sections of one part for
good, as opposed to screws, which come apart for service.

**Merged boss** — A boss, column or lug standing close enough to a wall that it
is fused into it instead of standing free; the wall then serves as part of its
sleeve.

**Core component** — A purchased hardware item modelled to its measured size:
SBC, USB hub, battery pack, display panel, display driver, controller,
keyboard. Distinct from case parts (Tray, Deck, Bezel, back panel, Bearing
clamp), which are generated around them.

## Retired (clamshell)

These terms belong to the clamshell (ADR-0009) and are **not** used for the
slider. They are kept here only to read old decisions and commit messages:
**Base**, **Lid**, **Visor**, **Closed plane**, **Torque hinge**, **Leaf**,
**Hinge axis**, **Travel stop**, **Cable slot**, **Cable guard**, **Base
knuckle**, **End cheek**, **Saddle**. Their ADRs (0004, 0005, 0007) are
superseded; the SolidCraft stream (ADR-0008) is deprecated.
