# Form Factor

Agreed shape of the device. Terms are defined in `/CONTEXT.md`; decisions
with lasting trade-offs are in `docs/adr/`.

## References

* **NEC MobilePro 900** — overall footprint (~243 × 126 mm). Our Envelope is
  display-limited at ~236 × 118 mm, already in that class.
* **Jornada P6** (r/cyberDeck prototype; images in `docs/reference/`) —
  hinge, rounded rear roll, keyboard Well, recessed feet, lid proportions.
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
  what is fused to the wall's inside (merged columns, saddles, Deck Seam
  lugs). A wall-thick solid band runs across the Parting plane, so neither
  the Tray's top edge nor the Deck's bed face is a comb, and the slots stop a
  wall below the hinge pocket.
* Battery cells lie in printed floor cradles; side-by-side cells' cradles
  meet flush and print as one block.

## Hinge

Printed friction hinge (ADR 0004, amended by ADR 0005), Jornada P6 layout: a
Lid knuckle at each corner and one long Base knuckle in the middle. Each Lid
knuckle is clamped between the Base knuckle and an outer end cheek by an M3
bolt whose head and captive nyloc nut are both on the stationary Base side,
with steel and spring washers between the rubbing faces; the head sits under a
removable service cap and tightening it sets the friction. The end cheeks are
fused to the Deck, one per Deck Section. The Base knuckle is a separate
D-profile bar, hollow between its lands (the display cable tunnel,
`hinge.wire_tunnel`), that sits in a pocket in the Deck's rear edge with its
flat against the Deck: the two friction bolts hold it along the axis and tie
the Deck Sections together, and a saddle block on the inside of the rear skirt
backs its flat at each land, from the Parting plane up to the Deck roof (as
deep as `hinge.saddle`, less where a component stands closer; the build fails
if a saddle is thinner than a wall). Nothing of the hinge reaches below the
Parting plane, so the Tray's rear wall and its ports stay clear. Knuckle
diameter must leave at least `wall.thickness` around the tunnel. The Lid
knuckles are fused to the Lid shell's side Sections (no Seam crosses them);
the Lid's rear edge is rolled (`Hinge.build_lid_roll`) and the roll counts as
wall, so Lid shell Seams pass through it. All dimensions are in the `hinge:`
config section and the layout math stays in `components/hinge.py`.

## Printing

Every wide part is split into Sections (ADR 0003): Tray and Lid shell into
three, with stepped Seams (`__--__--__`) mirrored about the centerline; Bezel
and Deck into two along a straight Seam at x=0; the keyboard plate into two at
the key-column gap nearest the center. Seams are staggered between parts
screwed to each other, and no Seam (with its steps and a wall of margin)
crosses a rib, boss, standoff, column, cradle, vent or lug — derived features
such as ribs are laid out to clear it, and the build fails otherwise. Seam
positions and step sizes come from config, per part.

Each Section has a flat bed face and a declared print orientation (HARD);
overhangs steeper than 45° are reported (SOFT) as needing support. The Deck
prints Parting face down with supports under its sloped roof.

A boss, column, standoff or lug closer than `2·wall` to a wall becomes a
**Merged boss**: the gap is filled (hull to the wall, both walls in a
corner), and its bore may move toward the wall as long as at least
`wall.thickness + 0.5` mm remains between bore and outer skin. Battery cradles
are exempt.

Concave joints (wall–floor, boss–wall, boss–floor, rib–floor, Merged
boss–wall) get a stress-relief edge of `0.5·wall` by default: a 45° chamfer
where the edge is horizontal in print orientation, a fillet allowed where it
runs along print Z. A stepped Seam's notch corner gets that fillet like any
other, so the tab corner of the neighbouring Section that fits into it is
rounded too, `edges.seam_convex_extra` (0.5 mm) larger, and the two still
mate. The bed-face outer edge gets a 0.5 mm chamfer against elephant's foot.
Where an edge treatment doesn't fit it is skipped with a SOFT warning.

Sections of one part are joined for good by Seam lugs (ADR 0006,
`geometry/seam_joint.py`): a lug straddles the Seam, bored through along X
for a length of 1.75 mm filament that is pushed in after the Sections are put
together, glued, and trimmed flush (`seam_pin` in the config). Each Seam of
the Tray and the Lid shell gets two lugs on the floor, the Deck's Seam two
standing on the Parting plane — one in the front skirt under the keyboard
plate, one in the rear skirt under the Base knuckle. Sites are tried at the
Seam's end segments, then the interior ones, skipping any whose lug would
touch the components inside, a boss, column, cradle, saddle or connector
cutout; the build fails if fewer than two clear sites exist on a Seam. Ribs
are laid out between the Seam bands and the lugs. Bezel Sections are joined
through the Lid shell bosses; screws stay wherever one part is held to
another, so the case still opens for service.

Seam defaults are tuned per part: the Tray's sit at ±59 mm (clear of the SBC
bosses, the battery cradles and the rear-wall connector cutouts); the Lid
shell's at ±40 mm. Stepped Seams jog away from the centerline, so the pair
mirrors about it.

Fitting the plate Seam standoffs meant moving the SBC 10.3 mm forward and 2 mm
right in `config/layouts/clamshell.yaml` (and raising the plate by 0.8 mm to
keep the board's clearance): a standoff runs floor to plate and cannot pass
through the board. The Base knuckle used to be screwed to the Tray floor (ADR 0004); the hub
and the battery stand against the rear wall and the Tray wall is only as tall
as the Parting plane, so it is seated in the Deck instead (ADR 0005).

## Review renders

Every assembly target is also exported as glTF with one color per component,
and the Base/Lid shells translucent, so the Sections, Seams and internal parts
can be told apart when reviewing a design. New parts (Visor, hinge knuckles,
service caps, each Section) need their own entry in `utilities/colors.py`.
