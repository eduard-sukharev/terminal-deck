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
the joint sits in straight walls. Eight stations — two per long side, one at
each corner — take an M3 countersunk screw from the Back's outer face into a
heat-set insert in the band; the four corners use printed posts outboard of the
Rod clamps.
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
(`rod_x = ±93.86`). Derived from the tightest of three bounds — the lid's band
corner post, the Deck seat against the chassis band's corner boss, and the
moving clamp head staying under the display — less `slide.rod.side_margin`.
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

**Accessory rail** — The picatinny-style mounting interface on the Chassis's
side walls. The shell carries square-nut pockets (nuts inserted during a print
pause); the rail bars themselves are user-supplied accessories, not printed
shell parts. The external battery pack hangs on one.

**Rear band** — The strip of Deck behind the keyboard, between the
bearing-clamp seats. Holds the SBC and the drag-chain anchor; not used for the
battery. It runs to the lid's rear edge — the chassis grows to the closed
face — so the bearing-clamp seats sit slightly forward of the rear wall.

**Well** — The walled recess in the Deck the keyboard fits in: a ring of walls
around a Cutout, descending from the Deck top to the keyboard plate. The plate
bears flat on the walls' lower faces from below; the keycaps rise through the
Cutout. The Well is owned by the Deck — the Parting plane never cuts its walls.
_Avoid:_ "pocket", "basin".

**Well wall** — One wall of the Well's ring, 2 mm thick, descending from the
Deck top to the plate. The plate is screwed against its lower face; the front
and rear walls carry the plate's fastening bosses, the X walls only locate the
plate.
_Avoid:_ "skirt", "rim".

**Cutout** — The rectangular opening bounded by the Well walls. Sized to the
keycap footprint plus a `wobble` allowance (0.6 mm), so a rocking keycap never
strikes a wall — not to the plate, and not by `clearance.shell`.

**Plate ear** — A rectangular, filleted tab protruding past the keyboard
plate's outline where its edge border cannot hold a fastening boss; it carries
the screw up into the Well wall.
_Avoid:_ "tab".

**Tray** — The Chassis's floor and walls (bosses, ribs, vents, cutouts) below
the Parting plane: drafted from its base up to `band_z0`, then a prismatic
half-band to the plane. Carries the ten frustum columns the Deck's screws pass
through into the Deck's insert bosses.
_Avoid:_ "base" (retired clamshell term).

**Deck** — The Chassis's purely prismatic top half: the keyboard Well, the
bearing-clamp seats and the Rear band sit on it; its skirt meets the Tray at
the Parting plane and holds the ten heat-set inserts in the band's insert
bosses.

**Parting plane** — The horizontal plane where the Deck meets the Tray,
part-way up the Chassis walls, so the Deck has a flat face and a wall skirt.
Across it a prismatic 6 mm band carries the joint, split 3 mm on each half:
the side draft continues only below the Tray's half-band (the Deck is purely
prismatic). Ten M3 countersunk screws come up from below.
_Avoid:_ "seam" for the Tray/Deck joint — a Seam joins Sections of one part.

**Scallop** — A shallow (10 × 0.8 mm) relief cut into the outside wall at
every Tray/Deck fastener station, 3 mm on each half across the Parting plane.
A visual/indexing notch, never a structural feature.

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

**Chamfer** — The default edge treatment: a 45 degree cut on an outside corner
or inside joint. It gives the case its chopped, brutal hi-tech look and prints
without support. Outside edges are chamfered, never filleted.

**Fillet** — A rounded edge. Allowed only sparingly on hidden inside joints
(the vertical concave relief and the Seam tab corners that nest in it), never
on an outside face. See `docs/design_spec.md` (Edge Treatment).

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
