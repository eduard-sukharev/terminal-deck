# Form Factor

Agreed shape of the device. Terms are defined in `/CONTEXT.md`; decisions
with lasting trade-offs are in `docs/adr/`.

## References

* **NEC MobilePro 900** — overall footprint (~243 × 126 mm). Our Envelope is
  display-limited at ~236 × 118 mm, already in that class.
* **Jornada P6** (r/cyberDeck prototype; images in `docs/reference/`) —
  keyboard Well, recessed feet, lid proportions (its printed hinge and
  rounded rear roll gave way to Torque hinges, ADR 0007).
* **Micro Journal Rev.2 ReVamp** — the Visor.

No palm rest. The Micro Journal "large palm rest" requirement is dropped.

## Clamshell

* Symmetric clamshell: the Lid has the same footprint as the Base and is
  thinner.
* Closed, the device is a box (top parallel to bottom). The Deck keeps its
  slope (`config.deck.slope`); the Lid absorbs it with a **Visor**: tapered
  walls on the front and both sides, full height at the front, zero at the
  hinge. Opened, the Visor hoods the top edge of the screen. See
  `docs/reference/visor-side-view.svg`.
* Thickness: strive for thinner, no hard limit. Closed thickness is a GOAL
  metric in the constraint report. Permitted levers: deck slope, keycap
  profile (config), minimal Lid. The buried-SBC layout stays.

The Visor is built by `geometry/visor.py` from `Base.visor_profile()` and
added to the Lid shell: a wall-thick ring on the shell outline, trimmed to a
height that equals the Lid's flat underside plane (through the Deck's highest
point) minus the Deck top. Each run checks `visor-closes-flush`,
`visor-zero-at-hinge` and `visor-non-negative`, and reports closed thickness
(Base to closed Lid top) as a GOAL line in the "closed-device validation".

## Lid

* Display centered in the Lid. The driver board stays directly behind the
  panel (the FPC runs straight; do not move it).
* Bezel held by twelve exposed countersunk M2 screws from the front — a
  design element, not hidden: six per Bezel Section, two at its outer
  corners and four beside the straight centre Seam — two above and two below
  the glass, one next to the display panel and one level with the corner
  screws at the Bezel's edge.

## Base

* Keyboard sits in a **Well**: a rim around it at or below switch-top
  height, so it adds no thickness. The rim is a wall-wide ring around the Deck
  opening, `well.switch_margin` (config) below the switch tops
  (`geometry/well.py`), and is clipped to the closed Lid's underside plane, so
  it tapers away toward the hinge like the Visor.
* Four 15 mm round recesses, 1 mm deep, in the floor for rubber feet. Feet
  and bosses are placed independently — neither positions the other, but no
  screw head may land in a foot recess.
* Tray and Deck meet at the **Parting plane** (ADR 0003): horizontal, at a
  configured fraction of the front wall height clamped to min/max mm, so the
  Deck has a flat face and a wall skirt. The Deck is held by M3 screws from
  below — through counterbored Tray columns into heat-set inserts in Deck
  bosses; nothing stands proud of the Deck under the hands. The Deck Seam
  needs no column of its own (its Sections are pinned, ADR 0006), and no
  column stands in the strip behind the SBC's mini-HDMI plug where its
  ribbon runs to the hinge (`Base.cable_runs`).
* The keyboard plate is held by eight M2 screws on Tray-floor standoffs: four
  at its edges and two per Section within 1u of its Seam, one in the upper
  and one in the lower rows, in row gaps clear of stabilizers. The build fails
  if they don't fit around the parts buried below.
* The rear wall carries a row of vertical 0.8 mm vent slots
  (`geometry/vents.py`). A slot may stand over a connector cutout, starting a
  wall above it (or beside it); it is left out only over the Seam bands and
  what is fused to the wall's inside (merged columns, hinge pads, Deck Seam
  lugs). A wall-thick solid band runs across the Parting plane, so neither
  the Tray's top edge nor the Deck's bed face is a comb, and the slots stop a
  wall below the Base leaf's pocket.
* Battery cells lie in printed floor cradles; side-by-side cells' cradles
  meet flush and print as one block.

## Hinge

Two purchased metal Torque hinges (ADR 0007; reference part XK574-6-16,
2 N·m), the left one the mirror of the right about the centerline. The part is
data in the `hinge:` config section: a barrel on the Hinge axis and two
Leaves, each with its offset from the axis, its extent and its holes, all in
the hinge's own frame. Only the right hinge's X is configured (`hinge.x`,
between the hub and the battery, whose cells stand taller than the Base leaf,
and clear of the rear Deck column).

The case adapts to that description (`components/hinge.py`):

* The Hinge axis lies in the closed plane (Lid underside), set back behind
  the rear face by the barrel's or the Cable guard's radius plus a swing
  clearance. With the axis outside the shells the Lid swings through
  `hinge.travel` without a rear roll or notches; the build fails if any
  point of the Lid's side profile or its Leaf would enter the Base.
* Each Leaf lies flat inside its shell: the Base leaf under the Deck slab,
  the Lid leaf against the Lid's back. Each gets a pocket (`hinge.fit` all
  round, through the rear wall) and a pad a wall wider than the Leaf from the
  Leaf to the shell, with an M4 heat-set insert per hole. The build fails if
  an insert has no room, a hole's insert falls outside the case, a Leaf
  leaves its shell, or a component stands in a Leaf's pad.
* The display FPC makes one turn round the Cable guard on the axis, facing
  the driver's HDMI plug: a core (the FPC's minimum bend radius) and a ring,
  part of the Deck through two end discs and arms, inside a Lid ring that
  turns with the Lid. Each ring covers only the angles no cable entry ever
  reaches through the travel. The cable passes through a Cable slot in the
  Deck's and the Lid shell's rear walls. The build fails if the guard
  overlaps a hinge or a Deck Seam.

* The Lid opens to `hinge.travel` (120°, a working angle; the hinge itself
  turns to 196°) and stops there on a rib on the Deck outboard of each
  barrel, behind the rear face, standing on the Parting plane. Its face lies
  on the Lid's rear face at `travel`; the build fails if the Lid meets it
  earlier. Hinge torque ~0.15 N·m each (`hinge.torque`, see ADR 0007): enough
  to hold the Lid, little enough to open it one-handed.

The pads, the stop ribs and the guard are structural features: no Seam may cross them.

Sections of one part are joined for good by Seam lugs (ADR 0006,
`geometry/seam_joint.py`): a lug straddles the Seam, bored through along X
for a length of 1.75 mm filament that is pushed in after the Sections are put
together, glued, and trimmed flush (`seam_pin` in the config). Each Seam of
the Tray and the Lid shell gets two lugs on the floor, the Deck's Seam two
standing on the Parting plane — one in the front skirt under the keyboard
plate, one in the rear skirt. Sites are tried at the
Seam's end segments, then the interior ones, skipping any whose lug would
touch the components inside, a boss, column, cradle, hinge pad or connector
cutout; the build fails if fewer than two clear sites exist on a Seam. Ribs
are laid out between the Seam bands and the lugs. Bezel Sections are joined
through the Lid shell bosses; screws stay wherever one part is held to
another, so the case still opens for service.

Seam defaults are tuned per part: the Tray's sit at ±59 mm (clear of the SBC
bosses, the battery cradles and the rear-wall connector cutouts); the Lid
shell's at ±66 mm (outboard of the hinge pads and the Cable guard). Stepped Seams jog away from the centerline, so the pair
mirrors about it.

Fitting the plate Seam standoffs meant moving the SBC 10.3 mm forward and 2 mm
right in `config/layouts/clamshell.yaml` (and raising the plate by 0.8 mm to
keep the board's clearance): a standoff runs floor to plate and cannot pass
through the board.

## Review renders

Every assembly target is also exported as glTF with one color per component,
and the Base/Lid shells translucent, so the Sections, Seams and internal parts
can be told apart when reviewing a design. New parts (Visor, Torque hinges,
each Section) need their own entry in `utilities/colors.py`.
