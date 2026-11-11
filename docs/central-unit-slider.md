# Central-unit slider (form reference)

The source reference for the project's form: an externally authored STEP,
"Central unit" (`central-unit.step`). The device is a flat-faced slab whose
screen lid slides over a chassis on two steel guide rods; the keyboard is
revealed by the slide. The project adopts the **form and the mechanism**, not
the reference's dimensions (ADR-0009). The 8.8" 1920×480 panel adaptation is
in `generated/central-unit_screen88.sc`.

Terms used here are the canonical ones in `CONTEXT.md` (Chassis, Screen lid,
Face, Face height, Slide travel, Bearing clamp). This document only records
what the reference measures and what the 140 mm pass found.

## Axis mapping of the reference file

The reference is modelled upright: the face lies in **XZ**, so its **Z** is
the slide direction (face height) and its **Y** is the thickness. It is upside
down relative to the device: −Z is the device's top (screen end), +Z the
bottom. In the project model the device is laid face-up: face height is **Y**,
thickness is **Z** (`docs/coordinate_system.md`).

## Measured geometry (mm)

| Part | X | Along the slide | Thickness | Source |
|---|---|---|---|---|
| Full reference envelope | 334.8 | **226.4** | 80.6 | `central-unit.step` |
| Keyboard JD40 plate | 230.15 | **77.75** | 1.5 | `keyboard_plate.size()` |
| Screen module 8.8" | 231.0 | **64.5** | 6.5 | `config/display.yaml` |
| HDMI driver board | 55 | 45.5 | 4.6 | `config/display.yaml` |
| Orange Pi Zero 2W | 65 | 30 | 6.7 | `components/orange_pi_zero2w.py` |
| Guide rods (2) | ⌀8.1 | ~189 | — | measured from STEP |
| Bearing housings | ⌀21 | 12.7 | — | measured from STEP |

The reference's dominant faces are normal to Y (the front/back of the slab);
the 20° faces at the top and bottom are end chamfers, not a typing slope. The
rods sit at x = 7.7 and 278.7 (hence ±135.5 from the centreline), outboard of
the 230 mm keyboard — this is where the side pods come from.

## Mechanism measurements

Measured from the same STEP (axes: X width, Y thickness, Z slide). These are
the source for ADR-0010:

| Part | X | Thickness (Y) | Along the slide (Z) |
|---|---|---|---|
| Guide rod | ⌀8.1 | — | 189.2 |
| Rod clamp (blue) | 26.0 | 10.0 | 14.0 (2 screws) |
| Bearing clamp (green) | 26.7 body | 28.2 (foot below the panel) | 31.0 |
| Through-slot in the back panel | 22.6 | 6.0 panel | 161.2 (between rod clamps) |

The rod centre sits 0.45 mm off the back panel's inner face. The printed
Bearing clamp straddles the panel: its body is on the lid side, its foot drops
through the slot into a pocket in the chassis (the chassis top is 15 mm thick
there). The slot ends at the two rod clamps, which are screwed into solid panel
on either side of it. The project's rod clamps are narrower (22 mm), its
bearing clamp shorter (14 mm) and its bearing is the short LM6UU (19 mm,
instead of the reference's 12.7 mm housing): the 140 mm budget has to pay for
two rod clamps at the rod ends as well, so the long LM6LUU does not fit. The
arrangement is the same.

## Reference envelope vs project target

The reference spends its 335 × 80.6 mm on decorative rails, an antenna and an
empty SBC/battery compartment. The project keeps the mechanism and re-derives
the envelope from the components:

| Dimension | Reference | Project |
|---|---|---|
| Width | 334.8 | ≈ 283 (keyboard/panel + side pods) |
| Thickness | 80.6 | ≈ 56 (GOAL) |
| Face height (closed) | 226.4 | **140 (HARD)** |

The 140 mm budget, the travel (≈ 93, not 77.75) and the one-bearing-per-rod
rule are in `docs/form_factor.md` and ADR-0009.

## The 140 mm trim experiment

Result files: `generated/central-unit_screen88_z140.sc` / `.step`
(pre-trim snapshot: `generated/central-unit_screen88_before_z140.sc`).
Envelope after the pass: **334.8 × 80.6 × 140.0** (−106…+34 on the reference's
Z).

It was a feasibility check on the real geometry, not the project model. What
it found:

- **Bulk cut crashes OCC.** One `solid.box` cut over all ~50 low bodies
  segfaulted SolidCraft. Cutting **one body per feature** is stable (~180 ms
  each); that is the workable method.
- **Five imported bodies are open shells** that OCC cannot cut, split or
  stitch: `Left/Rigth screen frame`, `Lower chassis rigth`, `lower chasis
  left` (+1). They are the structural walls and were removed for the pass —
  which is why the result is a silhouette, not a printable part.
- **Duplicate instances**: a cut targeted by definition name hits only the
  first instance; extras are removed by their full world name.
- `surface.stitch` does not close the open shells; `solid.split_body` fails on
  them the same way as a box cut.

The project does not reuse the imported bodies: `case/` is generated from
components in build123d.

## Files

- `central-unit.step` — original import (untracked).
- `generated/central-unit_screen88.sc` — 8.8" screen adaptation, pre-Z work.
- `generated/central-unit_screen88_before_z140.sc` — snapshot before the trim.
- `generated/central-unit_screen88_z140.sc` / `.step` — 140 mm silhouette.
- ADR: `docs/adr/0009-slider-replaces-the-clamshell.md`.
