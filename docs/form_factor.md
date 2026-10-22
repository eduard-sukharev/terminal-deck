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
* Bezel held by eight exposed countersunk M2 screws from the front — a
  design element, not hidden: four at the corners, and one above and one
  below the glass on each side of the Bezel's straight centre Seam.

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
  bosses — at least one per Deck Section near its Seam; nothing stands proud
  of the Deck under the hands.
* The keyboard plate is held by eight M2 screws on Tray-floor standoffs: four
  at its edges and two per Section within 1u of its Seam, one in the upper
  and one in the lower rows, in row gaps clear of stabilizers. The build fails
  if they don't fit around the parts buried below.

## Hinge

Printed friction hinge (ADR 0004), Jornada P6 layout: a Lid knuckle at each
corner and one long Base knuckle in the middle. Each Lid knuckle is clamped
between the Base knuckle and an outer Base end cheek by an M3 bolt whose head
and captive nyloc nut are both on the stationary Base side, with steel and
spring washers between the rubbing faces; the head sits under a removable
service cap and tightening it sets the friction. The Base knuckle is a
separate D-profile part with a flat mounting flange, screwed from below to
every Tray Section so it bridges the Tray Seams, and is hollow between its
lands: the display cable tunnel (`hinge.wire_tunnel`). Knuckle diameter must
leave at least `wall.thickness` around the tunnel. The Lid knuckles are fused
to the Lid shell's side Sections (no Seam crosses them); the Lid's rear edge
is rolled (`Hinge.build_lid_roll`) and the roll counts as wall, so Lid shell
Seams pass through it. All dimensions are in the `hinge:` config section and
the layout math stays in `components/hinge.py`.

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
runs along print Z. The bed-face outer edge gets a 0.5 mm chamfer against
elephant's foot. Where an edge treatment doesn't fit it is skipped with a
SOFT warning.

The Tray and Lid shell are joined by two lugs each (`geometry/seam_joint.py`):
a lug straddles the Seam on the floor, and a horizontal M2 screw runs along X
from a clearance bore in the left Half into a heat-set insert pocket in the
right Half. Sites are tried front segment, rear segment, then the interior
segments, skipping any whose lug would touch the components inside; the build
fails if fewer than two clear sites exist. Deck Sections are joined through
the Tray (see Base); Bezel Sections through the Lid shell bosses.

## Review renders

Every assembly target is also exported as glTF with one color per component,
and the Base/Lid shells translucent, so the Halves, Seams and internal parts
can be told apart when reviewing a design. New parts (Visor, hinge knuckles,
service caps, each Half) need their own entry in `utilities/colors.py`.
