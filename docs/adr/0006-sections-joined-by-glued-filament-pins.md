---
status: accepted
amends: ADR-0003, ADR-0005
---

# Sections joined for good by glued filament pins

ADR 0003 held the Sections of the Tray and the Lid shell together with Seam
lugs carrying a horizontal M2 screw into a heat-set insert, and ADR 0005 gave
the Deck one such lug. Those screws are never meant to come out, and they run
along X a few millimetres above a floor or a Parting plane, where neither a
hand nor a screwdriver can get at them. The M2 insert also sets the lug's size
(5.4 mm square): too tall for the Deck's front skirt, which has 4.5 mm between
the Parting plane and the keyboard plate, so the Deck Seam had only its rear
lug.

Every Seam lug now carries a glued pin instead: a through-bore along X across
the Seam, sized for 1.75 mm filament plus a glue fit, with a 1 mm sleeve. The
Sections are put together, a length of filament is pushed through, glued, and
trimmed flush with side cutters. The lug shrinks to 3.9 mm square, so the Deck
Seam gets two lugs like the Tray's and Lid shell's — the front one fits under
the keyboard plate, clear of the space bar switch. Pin size, fit, engagement
and sleeve are in the `seam_pin:` config section.

With the Deck Seam pinned, ADR 0003's rule that each Deck Section has a Deck
column near the Seam is dropped: that column only clamped the Seam, and the
one left of it stood in the run of the SBC's mini-HDMI ribbon. Deck columns
now keep out of a strip behind that plug instead.

Screws remain wherever one part is held to another (Deck columns, Bezel,
keyboard plate, hinge), so the case still opens for service; only the Sections
of one part become one piece once assembled.

## Considered Options

- Keep the M2 screw/insert lugs: rejected — unreachable to drive, never
  undone, and too big for the Deck's front skirt.
- Blind holes with a dowel glued in before joining: rejected — the pin has to
  be cut to length beforehand and the Sections pressed together over it; a
  through-bore takes any length and is trimmed after.
- A smaller fastener (M2 self-tapping, no insert): rejected — still
  unreachable, and it would barely fit the front skirt (0.03 mm to spare).

## Consequences

- Tray, Deck and Lid shell can't be taken apart into Sections again; a broken
  Section means reprinting and re-gluing, or cutting the pins.
- Each lug's bore must stay open at both ends for the pin to go in; anything
  standing right against a lug end along X would block it.
