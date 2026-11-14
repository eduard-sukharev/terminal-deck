---
status: accepted
amends: ADR-0003, ADR-0012, ADR-0014
---

# Each printed piece has its own staggered Section Seam

ADR-0003 split every part into Sections along a stepped Seam at `x = 0`, and
read "staggered" as *between the Base and the Lid only*: the Tray and the Deck
shared one cut line, the Bezel and the Back plate shared another. Every part
also grew into a screw-joined pair only later (ADR-0011, ADR-0012), so at the
time the rule did not cost anything.

On the slider it costs the one thing the Seams exist for. The Tray and the Deck
are screwed together along their whole perimeter, and their Sections butt at
the *same* line: the two joints lie on top of each other, so a Tray Section
pulled in one direction and the Deck Section above it pulled in the other have
one continuous crack straight through the closed shell. The same is true of the
Bezel and the Back plate. A plastic case with two collinear Seams 3 mm apart has
no better a joint than one Seam, and the band's screws sit *beside* that line
rather than across it.

We therefore give **every printed piece its own Seam**, offset from its
partner's, so that the two cuts of a screwed pair lap over each other. Every
part still has **two** Sections.

## Decision

- **Inner pieces get a straight Seam just left of centre.** The **Deck** (the
  welled top) and the **Bezel** (the display carrier) split at **`x = −14.00`**,
  full depth. A straight line is what a part with seats, a Well ring and a
  display opening wants: there is no row structure to dodge, and the cut reads
  as a design line like ADR-0003's original `x = 0`.
- **Outer pieces get a trapezoid Seam.** The **Tray** (the bottom bowl) and the
  **Back plate** (the lid's flat panel) run at **`x = +10.00`** across the
  middle, stepping out to **`x = +18.00`** at each end wall. The transitions are
  **45°** diagonals that start at each end wall's inner face, so the run is
  `|18 − 10| = 8 mm` in Y and the diagonal is 8 mm long for an 8 mm jog.
- **The pair laps over 24 mm.** `tray(+10..+18) − deck(−14) = 24` and
  `back(+10..+18) − bezel(−14) = 24`, over the full shared depth: along the
  whole joint the two Seams are apart, never collinear, and the 45° jogs keep
  the outer piece's seam away from the inner one's even at the end walls.
- **Offsets stay inside 10–20 mm of the centreline.** A Seam on the centreline
  would coincide with its partner; a far one would leave one Section a stub. The
  configured range is 10..18, with 20 as the hard ceiling.

### A band station in the lap is the interlock

The point of staggering is not just to hide the joints: the shell must be held
together *across* the lap. The chassis band joint (ADR-0012) therefore gains one
station per long wall **on the centreline**, `(0, ±65.50)`, which sits between
the Tray's Seam (+10 middle, +18 at the ends) and the Deck's (−14) with
`boss/2 + boss_margin = 5.4 mm` to spare on both sides.

That single M3 × 18 screw does the interlocking:

- the **Deck half** that carries its heat-set insert boss is the one *right* of
  `x = −14`, i.e. the half with the station in it;
- the **Tray half** that carries the countersunk column is the one *left* of
  `x = +10` at that Y, i.e. the other half.

So the screw clamps a Deck piece to the diagonally opposite Tray piece. Without
this station the two pairs of Sections would each be internally fastened but the
shell could hinge along the lap.

The stations become **twelve** (was ten): four corners, **six** long-wall (the
four existing at ±114.08/±65.50 and ±40.19/±65.50, plus the two new centreline
ones), two in the free rear band. Sizes, screw, scallops and `parting_z` are
unchanged; the new station takes the same `side_inset` and the same `7.80 mm`
long-wall boss.

### The lid takes the same centreline pair

The lid's band stations sit at `x = ±116.88` and `±40.19`. With the Bezel Seam
at −14 and the Back Seam at +10..+18, the Bezel's left piece holds `−40.19` and
`−116.88` and the Back's right piece holds `+40.19` and `+116.88` — four
stations each, and **nothing across the lap**. The first draft of this record
claimed the lap had no room; it has: the band runs along both long walls, the
lap spans `−14 .. +10` on each of them, and a station on the centreline clears
the Bezel Seam by 14 mm and the Back Seam by 10 mm (15 mm at the station's own
Y), against a required `boss/2 + margin` of 5.4 mm. The lid therefore gains the
same **centreline pair**, `(0, ±65.00)`: **ten** stations, four on one Section
of each part and six on the other (the pair falls to the right of the Bezel
Seam and to the left of the Back's),
each Bezel piece clamped to the *other* Back piece. The lid is a display
carrier, so two extra M3 × 6 are a cheap way not to rely on the glass bond to
hold its two halves together.

### Every Seam also takes two glued filament pins

The staggered Seams interlock in plan, but the two *straight* ones (Deck and
Bezel) have no key at all, and none of them registers anything while the part
is being assembled and the band screws are still out. Each of the four Seams
therefore carries **two fin-pair pin pockets** (ADR-0006): two parallel fins
with a 2.0 mm slot between them, and a length of 1.75 mm filament glued into
the slot. Where each pair goes is `slide.seam_pin_sites` — placements in the
part's free interior, each annotated in `config/slide.yaml` with the feature it
avoids (the Tray's under the plate and clear of the RP2040 and the SBC, the
Deck's in the rear band above the SBC, the Bezel's and the Back plate's
outboard of the display and the driver).

### The keyboard plate notch count follows the stations

The plate is notched wherever a band boss reaches its border (ADR-0014). The new
centreline front station is another such column, so the plate's spacebar lip is
notched **five** times instead of four. The notch is the same `5.30 × 1.45` with
a `1.10 mm` bite into the `2.00 mm` border, leaving `0.90 mm` of sheet: thin, but
one connected sheet, and the plate is checked to stay one.

### Two knobs moved

- **`keyboard.mounting.seam_slack: 4.0`** is now its own config value. The
  at-Seam M2 stations used to read the stepped Seam's jog out of the Section
  split; with the Deck's Seam straight there is no jog to read, and the
  `7.20 mm` `seam_clearance` that pins ADR-0014's shipped numbers must not move.
  `seam_slack` (4.0) + ear (2.60) + `minimum_feature` (0.60) = 7.20, exactly as
  before.
- **`slide.rear_wall_margin` 6.0 → 8.0.** The new rear centreline column at
  `(0, +65.50)` is `Ø7.80`, so the SBC (which moved back with the margin) now
  clears it by **1.6 mm** instead of the 0.4 mm a 6.0 margin would leave. The
  SBC sits at `y 30.0..60.0`; nothing else moves.

## The Seam model

`utilities.config_loader.Seam` is now a plan **polyline**, not a single X: a
tuple of `(y0, y1, x)` runs with the jogs implicit in the gaps between them, and
`x_at(y)` interpolating across a diagonal. `Seam.straight(x)` and
`Seam.stepped(x, step, steps, depth)` build the two historical shapes;
`Split` adds `style="trapezoid"` with `ends_x` and `jog`, and `Split.seams(depth,
wall)` needs the part's depth because a trapezoid's jogs start at its end walls.
`geometry.split.split_part(shape, split, depth, wall)` is the build entry point,
and `geometry/split.py` cuts the Seam's own polygon, so a 45° jog and a square
step cut the same way. `utilities.validation.seam_bands` and
`geometry.edge_treatment.seam_corner_points` walk the same polyline.

The configured splits are per piece:

```yaml
split:
  chassis_tray:     {sections: 2, x: 10.0, style: trapezoid, ends_x: 18.0, jog: 45.0}
  chassis_deck:     {sections: 2, x: -14.0, style: straight}
  screen_lid_bezel: {sections: 2, x: -14.0, style: straight}
  screen_lid_back:  {sections: 2, x: 10.0, style: trapezoid, ends_x: 18.0, jog: 45.0}
```

`chassis` and `screen_lid` are retired as split keys; the pipeline warns if they
are still configured.

## Consequences

- The `chassis_left/right` and `screen_lid_left/right` reference exports are now
  **compounds of the real pieces** (`tray_* + deck_*`, `bezel_* + back_*`), not
  one cut of an assembled shell. `screen_lid_left/right` are no longer printable
  targets; the printable set is the four pieces per shell.
- The widest Section is **138.6 mm** (`241.17/2 + 18`), still far inside 220 mm.
  Tray/Deck Sections are `139.25 × 16.15`, Bezel/Back `140.00 × 24.45` tall-ish
  pieces: all inside `220 × 220 × 256`.
- The plate is notched five times; `keyboard-plate-seam`, the Well ring and the
  eight M2 stations are unchanged (`seam_clearance` stays 7.20 through
  `seam_slack`).
- New HARD checks in `run_slider_checks`:
  - `slide-seam-offset` — every Seam path stays 10..20 mm off the centreline;
  - `slide-seam-stagger` — the Tray/Deck, Bezel/Back and Deck/plate Seams stay
    at least one wall apart over their whole shared depth;
  - `slide-seam-clear` — no Seam crosses a band station, a Well M2 boss or a
    bearing seat (with the boss margin);
  - `slide-seam-interlock` — a band station on **each** long wall sits between
    the Tray's and the Deck's Seam;
  - `slide-seam-stations` — each Section of each part keeps at least two
    stations of its joint;
  - `slide-seam-pin-fit` — the filament sits in the slot with glue room, the
    fins are at the printable minimum and each reaches 5 mm into its Section;
  - `slide-seam-pin-clear` — every pin site is on a straight run of the Seam,
    two per Seam, and clear of the band stations and the components' **solid
    sub-volumes** (not their bounding boxes).
  `seam-lap-*` GOALS report the measured laps (24.00, 24.00, 9.24) and
  `seam-pins-*` the pin count per part.
- `slide-section-fit` reports the widest Section from the Seam offsets instead of
  half the case width.
- Every Seam now carries two fin-pair glued filament pins (ADR-0006 revised):
  the Seams are butt joints *plus* their pins, not pins alone, and the band
  screws still carry the shell.

## Considered alternatives

- **Three Sections per shell** (left/center/right, two Seams each): rejected —
  it doubles the seam lines, implies ~16 screws per shell, and a 241 mm case
  gives each Section ~80 mm, which is not the print problem the split solves.
- **Offsetting both Seams but keeping them straight** (`−14` and `+10`): it does
  stagger, but the ends of each cut still land on the same end wall only 24 mm
  apart, and the two probes are parallel lines that read as one wide slot. The
  trapezoid makes the lap a genuine interlock and gives the plan its zigzag.
- **A Seam at 70 mm** (one side largely unsplit): rejected — it leaves a stub
  Section and puts the cut through the bearing seats.
- **Symmetric offsets** (`±12`): the band station between the Seams would have
  to sit on the centreline anyway, so one Seam has to cross the centreline
  opposite the other; the 10/18 pair keeps the middle run clear of the Well's
  M2 bosses.
- **Right-angle jogs** (the user's first sketch was `|‾|`): a 45° jog is
  printable without support and does not create a thin, fragile tongue at the
  step; the square-stepped shape from ADR-0003 is kept only for tests.
- **A ninth lid station in the lap**: rejected in the first draft, then
  adopted — the reasoning ("the eight existing stations already cross the lap")
  was wrong: they do not, because each Back piece is only screwed to its own
  Bezel piece. The centreline pair is in, at ten stations.
- **A drilled lug with a glued pin** (ADR-0006's earlier form): rejected — two
  printed fins leave the same alignment with less material, one tolerance and
  no bore to keep open.

## Open measurements

- The 45° jog relies on the Tray's floor being flat at the seam: the tray is
  drafted below `band_z0` and the jog lies in the band, so no `TODO: measure`
  is opened. The step's cosmetic corner radius (if added) would be
  `geometry/edge_treatment.round_seam_corners`.
