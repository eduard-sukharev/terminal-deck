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

**Closed plane** — The plane the Lid's glass side lies on when closed: the
top of the Base's walls at the rear, a clearance above the highest keycap.
The Hinge axis lies in it.

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
Seams mirror each other about the centerline. Tray, Deck and Lid shell
Sections are joined for good by Seam lugs; the thin plates' Sections (Bezel,
keyboard plate) are held by screws into the part behind them.
_Avoid:_ "Half" (a part may have three Sections); "half" for Base vs Lid —
say Base or Lid.

**Seam** — Where two Sections of one part meet. Seams are staggered between
parts screwed to each other (they don't line up) and never cross a structural feature (rib, boss,
standoff, cradle, vent). Outward-facing Seams are stepped lines
(`__--__--__`) seen from above, with plain butt-joint step faces held by
Seam lugs — except the Bezel's and the Deck's, which are straight on
the centerline and echo each other. The Bezel's screws are exposed as a design
element; the Deck's are driven from below so nothing stands proud under the
hands.

**Parting plane** — The horizontal plane where the Deck meets the Tray,
part-way up the Base's walls rather than at the Deck's edge, so the Deck has a
flat face and a skirt of wall below the keyboard surface.
_Avoid:_ "seam" for the Tray/Deck joint — a Seam joins Sections of one part.

**Seam lug** — A pinned joint straddling a Seam: a block shared by the two
Sections with a glued filament pin along X through both. Joins Sections of
one part for good, as opposed to screws holding one part to another, which
come apart for service.

**Torque hinge** — A purchased metal friction hinge joining Base and Lid,
one at each rear corner (the second always mirrored about the case
centerline). Described by its Hinge axis and two Leaves; the case adapts to
that description, not the other way round.
_Avoid:_ "knuckle" for any part of it.

**Leaf** — One flat mounting plate of a Torque hinge: the Base leaf screws
to the Base, the Lid leaf to the Lid. Its screw holes are given in the
Leaf's own plane, relative to the Hinge axis.
_Avoid:_ "wing", "flange".

**Hinge axis** — The line the Lid turns about; the origin a Torque hinge's
Leaves and holes are described from.

**Travel stop** — The printed rib on the Deck, behind each Torque hinge,
that the Lid's rear face lands on at its working angle; the hinge itself
would turn further.

**Cable slot** — The opening in the Deck and the Lid shell, near the
display's HDMI connector, that the display cable passes through between
Base and Lid.

**Cable guard** — A printed, load-free sleeve on the Hinge axis, facing the
display's HDMI connector: a core setting the display cable's minimum bend
radius, wrapped by one turn of the cable, inside a ring that is part of the
Deck and a ring outside it that is part of the Lid shell and turns with it.

**Base knuckle** — (superseded by Torque hinge) The long middle knuckle of the hinge: a separate printed
bar on the Base side, seated in the Deck's rear edge, carrying the display
cable through its hollow middle.
_Avoid:_ "bracket", "Base knuckle part" (it no longer includes the cheeks).

**End cheek** — (superseded by Torque hinge) The fixed block at each end of the hinge, outboard of a Lid
knuckle, holding the friction bolt's head. Part of the Deck.

**Saddle** — (superseded by Torque hinge) The block inside the Deck's rear skirt that the Base knuckle's
flat bears against, one at each end of the bar.

**Merged boss** — A boss, column or lug standing close enough to a wall
that it is fused into it instead of standing free; the wall then serves as
part of its sleeve, so its bore may sit closer to the wall than a free boss's.

**Core component** — A purchased hardware item modelled to its measured
size: SBC, USB hub, battery cells, display panel, display driver, controller,
keyboard. Distinct from case parts (Tray, Deck, Lid shell, Bezel, hinge),
which are generated around them.
