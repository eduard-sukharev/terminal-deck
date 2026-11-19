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
SBC, the controller, and the bearing-clamp seats. Made of the Tray and the
Deck. The battery and the USB hub are not inside it; they are external
accessories on an Accessory rail.
_Avoid:_ "Base" (retired clamshell term).

**Screen lid** — The upper half that slides: carries the display, its driver,
the guide rods, their Rod clamps and the drag chain. Made of the inverted-tray
Bezel and the flat Back plate, joined at the Band joint.
_Avoid:_ "Lid" alone (ambiguous with the retired clamshell Lid), "cover",
"screen".

**Bezel** — The Screen lid's inverted tray: the front panel with the glass
opening, the display cavity and the prismatic fastening band along its bottom
edge, which holds the heat-set inserts for the Back plate. The display frame
sinks into the `bezel.recess` pocket in the panel's inner face; the remaining
lip retains it.
_Avoid:_ "face" (that is the device plane), "front cover".

**Back plate** — The Screen lid's flat 4 mm plate: faces the keyboard, carries
the two Guide rods and their Rod clamps, the two Clamp slots and the eight
countersunk Band-joint screws. Removable, so the display and the guide
hardware are serviceable from the keyboard side.

**Band joint** — The butt joint where the Bezel's band meets the Back plate at
the Back's inner face. The band is prismatic (the lid only tapers above it), so
the joint sits in straight walls. Ten stations — two per long side, one on each
long side's centreline, one at each corner — take an M3 countersunk screw from
the Back's outer face into a heat-set insert in the band; the four corners use
printed posts outboard of the Rod clamps. The centreline pair is the Seam
interlock (ADR-0015).
_Avoid:_ "flange", "lap" (it is a plain butt joint).

**Face** — The plane carrying the keyboard and the screen. The device is
modelled face-up. The face is flat: the keyboard has no slope, and the build
has no mechanism to tilt it.

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

**Guide rod** — One of the two steel rods the screen lid rides on. It runs in
the Screen lid's open cavity along the back panel's inner face, **under the
display**, held at both ends by two printed Rod clamps.
_Avoid:_ "rail" (an Accessory rail is a different part), "shaft".

**Guide stance** — The pair of X positions the Guide rods occupy
(`rod_x = ±94.98`). Derived from the tightest of three bounds — the lid's band
corner post, the Deck seat against the chassis band's corner boss, and the
moving clamp head staying under the display — less `slide.rod.side_margin`.
The width drives it: ADR-0014's plate is what the case is sized to.
_Avoid:_ "rail spacing", "track width".

**FPC guard** — The printed 1.6 mm grille plate tape-bonded to the Display's
back, where the moving Bearing clamp sweeps the panel's ribbon. Its
**guard channel** is the 0.6 mm recess on its display-facing side that captures
the flat ribbon; the ribbon is taped flat, so there is no folded-loop allowance.
The moving head clears the plate's underside by the component gap plus the sag
allowance, so it can only ever reach the plate, never the ribbon. It is a
separate printed target (`fpc_guard`).
_Avoid:_ "cable cover", "shield" (the Drag chain is a different part).

**Linear bearing** — A purchased LM…LUU ball bushing riding on a Guide rod.
One per rod; its length is part of the Face-height budget.
_Avoid:_ "bushing" when the purchased part is meant.

**Bearing clamp** — The printed clamp on the Chassis that holds a Linear
bearing. Its **cylindrical head** sits inside the Screen lid above the back
panel at the neck width (there is no flange), its neck passes through the
back-panel slot and the joint gap, and its foot is seated in a pocket in the
Chassis Deck. It slides along the slot as the lid moves and is the
load-bearing interface between the halves. The rod passing through the bearing
is what retains the lid against lift-off. The foot is longer than the bearing
and its screws land outboard of it, so the tips cannot reach the bore; its top
face is flush with the Deck top, in the pocket. The foot's vertical corners and
the pocket get a 5 mm relief, and the foot's top rim and the pocket mouth
0.5 mm; the head's circular rims stay as formed.
_Avoid:_ "housing", "bearing block".

**Rod clamp** — A printed clamp at one end of a Guide rod, screwed into the
lid back panel across the rod. Two per rod; the screws sit outboard of the
back-panel slot. With the stance under the display (ADR-0013) the clamp sits
under the panel, clear of it in Y, and outboard of it in X only by ~11 mm.

**Clamp slot** — The long through-slot in the Screen lid's back panel between
the two Rod clamps. The Bearing clamp's neck slides along it, **under the
display**; the slot ends at the Rod clamps, and the bearing stops short of each
clamp at the extreme poses. The FPC guard covers the ribbon where the head
sweeps this slot.
_Avoid:_ "C-channel" (the retired first-generation side-wall channel).

**Drag chain** — The articulated cable carrier that lets the display/driver
cable cross the sliding joint. It runs along the slide axis in a channel
behind the screen; its channel and anchors are part of the shell, its links are
a separate printed part.
_Avoid:_ "cable guard" (retired clamshell term), "cable track".

**Accessory rail** — The printed MIL-STD-1913 interface bolted to the Tray's
vertical side walls (ADR-0020). Two M4 stations per wall sit on a printed
washer puck: the puck captures a DIN 562 square nut in a square pocket in the
wall's pad, and the rail blank's counterbored hole comes down on it. The
picatinny profile (slots, hex top) is a later slice; the stance, pad, puck and
screw are settled. The external battery pack and the USB hub hang on rails.

**Rear band** — The strip of Deck behind the keyboard, between the
bearing-clamp seats. Holds the SBC and the drag-chain anchor; not used for the
battery. It runs to the lid's rear edge — the chassis grows to the closed
face — so the bearing-clamp seats sit slightly forward of the rear wall.

**Well** — The walled recess in the Deck the keyboard fits in: a 2 mm ring of
walls around a Cutout, descending from the Deck top to the keyboard plate's top
face. The plate bears flat on the ring's lower faces from below and is screwed
up into bosses on the ring's front and rear walls; the keycaps rise through the
Cutout. The Well is owned by the Deck — the Parting plane never cuts its walls.
_Avoid:_ "pocket", "basin", "opening".

**Well wall** — One wall of the Well's ring, 2 mm thick, descending from the
Deck top to the plate. The plate is screwed up against its lower face; the front
and rear walls carry the plate's fastening bosses, the X walls only locate the
plate.
_Avoid:_ "skirt", "rim".

**Cutout** — The rectangular opening bounded by the Well walls. Sized to the
keycap footprint plus a `wobble` allowance (0.6 mm per side), so a rocking
keycap never strikes a wall — not to the plate, and not by `clearance.shell`.

**Plate ear** — A 5.20 × 5.20 mm, r2.0 filleted tab protruding past the keyboard
plate's outline where its edge border cannot hold a fastening boss; it carries
the M2 screw up into the Well wall.
_Avoid:_ "tab".

**Plate notch** — A 5.30 × 1.45 mm rectangle (1.10 mm bite) the chassis forces
the plate's front border to yield where a Tray/Deck band column reaches into it.
Five of them (ADR-0015 added the centreline column). A plain polygon
subtraction, as the Plate ear is an addition.
_Avoid:_ "Cutout" (that is the Well's opening).

**Plate Seam** — The keyboard plate's split between key columns: a row-jogging
path (four bands on the JD40) through the clear gap between rows, never the
straight `x = 0` cut through switch cutouts. In the plate's own frame its ends
are at x = 0 and x = −50.584 (the latter on the spacebar side); each Section
carries four of the plate's eight M2 stations.
_Avoid:_ "centre cut", "straight split".

**Tray** — The Chassis's floor and walls (bosses, ribs, vents, cutouts) below
the Parting plane: prismatic from its base to the plane (ADR-0019), with its
vertical end walls leaving the table in a 15° base taper. Carries the twelve
straight columns the Deck's screws pass through into the Deck's insert bosses.
_Avoid:_ "base" (retired clamshell term).

**Deck** — The Chassis's purely prismatic top half: the keyboard Well, the
bearing-clamp seats and the Rear band sit on it; its skirt meets the Tray at
the Parting plane and holds the twelve heat-set inserts in the band's insert
bosses.

**Parting plane** — The horizontal plane where the Deck meets the Tray,
part-way up the Chassis walls, so the Deck has a flat face and a wall skirt.
Across it a prismatic 6 mm band carries the joint, split 3 mm on each half:
both halves are prismatic (ADR-0019). Twelve M3 countersunk screws come up from
below.
_Avoid:_ "seam" for the Tray/Deck joint — a Seam joins Sections of one part.

**Scallop** — A shallow (10 × 0.8 mm) relief cut into the outside wall at
every Tray/Deck fastener station, 3 mm on each half across the Parting plane.
A visual/indexing notch, never a structural feature.

**Envelope** — The closed device's outer dimensions (width × face height ×
thickness), the number the design minimises.

**Section** — One of the printable pieces a part is split into to fit the
build volume. Wide parts split into two along X; the keyboard plate splits
along its Plate Seam. Each shell piece is cut on **its own** Seam (ADR-0015),
not a shared `x = 0` line. Sections of one part are registered by Seam pins;
thin plates are held by screws into the part they bear on (the keyboard plate
up into the Deck's Well walls).
_Avoid:_ "half" (a part has Sections, not halves).

**Seam** — Where two Sections of one part meet: a **plan polyline**, not a
single X — straight (Deck and Bezel at `x = −14`), square-stepped, or a 45°
trapezoid (Tray and Back plate at `+10` middle, `+18` at the end walls). Seams
are staggered between parts screwed to each other, so a Tray/Deck (or
Bezel/Back) pair laps instead of sharing a cut line, and a band station in the
lap cross-ties it. A Seam never crosses a structural feature (rib, boss,
standoff, clamp, guide channel, rail pocket, vent).

**Seam pin** — The glued filament that registers two Sections of one part:
two parallel printed **fins** straddle the Seam and leave a slot between them,
and a 1.75 mm filament offcut is glued into the slot during assembly. An
alignment feature plus a little early strength, not a structural member; two
pairs per Seam.
_Avoid:_ "Seam lug" (the retired drilled block with a bore).

**Merged boss** — A boss, column or lug standing close enough to a wall that it
is fused into it instead of standing free; the wall then serves as part of its
sleeve.

**Chamfer** — A 45 degree cut on a convex (outside) edge, where the two faces
meet at `<= 90` degrees through the material. Outside edges are chamfered,
never filleted. A concave joint that opens toward the bed *of the part's own
print orientation* also keeps a chamfer: a round there prints as a curved
overhang.

**Fillet** — A rounded edge on a concave (inside) edge, where the two faces
meet at `>= 270` degrees through the material (`<= 90` through the void). Every
boss base and every sharp inside corner of the shell is filleted; never on an
outside face. A fillet must run so it prints without support. See ADR-0025 and
`docs/design_spec.md` (Edge Treatment).

**Core component** — A purchased hardware item modelled to its measured size:
SBC, USB hub, battery pack, display panel, display driver, controller,
keyboard. Distinct from case parts (Tray, Deck, Bezel, Back plate, Bearing
clamp), which are generated around them.

## Retired (clamshell)

These terms belong to the clamshell (ADR-0009) and are **not** used for the
slider. They are kept here only to read old decisions and commit messages:
**Base**, **Lid**, **Visor**, **Closed plane**, **Torque hinge**, **Leaf**,
**Hinge axis**, **Travel stop**, **Cable slot**, **Cable guard**, **Base
knuckle**, **End cheek**, **Saddle**. Their ADRs (0004, 0005, 0007) are
superseded; the SolidCraft stream (ADR-0008) is deprecated.
