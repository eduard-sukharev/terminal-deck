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
* Bezel held by countersunk M2 screws from the front.

## Base

* Keyboard sits in a **Well**: a rim around it at or below switch-top
  height, so it adds no thickness. The rim is a wall-wide ring around the Deck
  opening, `well.switch_margin` (config) below the switch tops
  (`geometry/well.py`), and is clipped to the closed Lid's underside plane, so
  it tapers away toward the hinge like the Visor.
* Four 15 mm round recesses, 1 mm deep, in the floor for rubber feet. Feet
  and bosses are placed independently — neither positions the other.

## Hinge

Jornada P6 style: three knuckles — two Lid knuckles at the corners, one long
Base knuckle in the middle. The Base knuckle has a solid pin land at each end
and is a hollow tube between them: the display cable tunnel
(`hinge.wire_tunnel`), so the cable never crosses the hinge exposed. Each side
has a pin running from its Lid knuckle into the adjacent Base land, closed by
a removable service cap (head outside the end, plug in the pin bore). Knuckle
diameter must leave at least `wall.thickness` around the tunnel; the build
rejects it otherwise. All dimensions are in the `hinge:` config section and
the layout math stays in `components/hinge.py`. The knuckles are fused onto
the shells, and the Lid's rear edge is rolled: the Lid half of a full-width
barrel on the hinge axis (`Hinge.build_lid_roll`), notched in the middle for
the Base knuckle, so the closed rear reads as one round roll.

## Printing

Every wide part is split into left/right Halves (ADR 0001). Seams are
staggered between parts; outward-facing Seams are stepped in plan view
(`__--__--__`) with butt-joint step faces, held by screws and bosses. Seam
position and step size come from config, per part. The keyboard plate splits
at the key-column gap nearest the center.

The Tray and Lid shell are joined by two lugs each (`geometry/seam_joint.py`):
a lug straddles the Seam on the floor, and a horizontal M2 screw runs along X
from a clearance bore in the left Half into a heat-set insert pocket in the
right Half. Sites are tried front segment, rear segment, then the interior
segments, skipping any whose lug would touch the components inside; the build
fails if fewer than two clear sites exist. The Deck and Bezel are not yet
joined this way.

## Review renders

Every assembly target is also exported as glTF with one color per component,
and the Base/Lid shells translucent, so the Halves, Seams and internal parts
can be told apart when reviewing a design. New parts (Visor, hinge knuckles,
service caps, each Half) need their own entry in `utilities/colors.py`.
