# Central-unit slider (experimental stream)

A Vaio-UX-style **slider** deck: the screen lid slides up over the chassis to
reveal a 40% keyboard. This is a separate form-factor experiment from the
build123d clamshell (see ADR 0008); it is built and edited in SolidCraft and
does not touch the Python pipeline. The 8.8" 1920×480 panel is the target
display.

Source model: `central-unit.step` (an externally authored STEP, "Central
unit"). The 8.8" adaptation (screen opening cut, bezel fillers) is in
`generated/central-unit_screen88.sc`.

## Terms (local to this stream)

These are the slider's vocabulary and do **not** replace the clamshell's
`CONTEXT.md` terms (Base, Lid, Tray, Deck).

**Chassis** — the sliding base: keyboard, SBC, and the bearing housings the
rods ride in. Conceptually the clamshell's *Base*, but it slides relative to
the lid rather than hinging.

**Screen lid** — the panel carrying the 8.8" display plus the rod clamps; it
slides along Z over the chassis. Conceptually the clamshell's *Lid*.

**Closed Z** — the device's height along Z in the closed (carried) pose,
where the lid fully covers the chassis and the device reads as one screen
panel. This is the number being minimised.

**Slide travel** — the Z distance the screen lid moves to expose the keyboard
fully; ~the keyboard depth (≈78 mm; the reference quotes ≥96 mm including
finger clearance).

**Overlap model A** — the layout this stream targets: the lid covers the
*whole* chassis when closed, and opening slides it up by the slide travel.

**Slide axis** — the imported file's Z. In that file the device is upside
down: the display/keycap side faces −Z, so −Z is the device *top* and +Z the
*bottom*. The face (keyboard + screen) lies in the XZ plane; **Y ≈ 80 mm** is
the thickness (chassis ~30 + screen lid ~33 + protrusions). X ≈ 335 mm is the
width (keyboard + side rails).

## Geometry (measured, mm)

| Part | X | Z (slide direction) | Y (thickness) | Source |
|---|---|---|---|---|
| Keyboard JD40 plate | 230.15 | **77.75** | 1.5 | `keyboard_plate.size()` |
| Screen module 8.8" | 231.0 | **64.5** | 6.5 | `config/display.yaml` |
| HDMI driver board | 55 | 45.5 | 4.6 | `config/display.yaml` |
| Orange Pi Zero 2W | 65 | 30 | 6.7 | `components/orange_pi_zero2w.py` |
| Rod clamp (lid) | ~14 | ~14 | — | central-unit import |
| Bearing housing (chassis) | ~26 | ~23 | — | central-unit import |

The SBC fits beside the keyboard in X (335 − 230 ≈ 105 mm free), so it adds
nothing to Z. A 2×18650 pack and a USB hub are **not** budgeted here; both are
placed by leftover space (the reference's main battery is external on a
picatinny rail).

## Z budget: imported vs target

Imported closed envelope **226.4 mm** (main frame 214.6 + an 11.8 mm
screen-release tab and rear vents at the top).

Chassis (214.6): 12.5 top edge · **83.5 keyboard** · **118.65 empty SBC/
battery compartment** ← the fat.

Screen lid (214.6): **81 top bezel** (covers the keyboard when closed) · 56
screen opening (module 64.5) · **77.65 bottom bezel** (covers the empty
compartment) · 2 × 14 rod clamps.

Target **140 mm**: chassis ≈ 106 (keyboard + margins, SBC moved beside the
keyboard); lid ≈ 140 (keyboard-cover bezel + screen + rod-clamp zones, sized
by ~78 mm of travel). The lid is the binding part.

## Experiment: destructive trim to 140 mm

Result files: `generated/central-unit_screen88_z140.sc` / `.step`
(pre-trim snapshot: `generated/central-unit_screen88_before_z140.sc`).

Envelope after the pass: **X 334.8 × Y 80.6 × Z 140.0** (−106…+34). Every
body above Z=+34 was cut flush; the screen-release tab and rear vents were
trimmed to −106.

What the pass found, and how it was done:

- **Bulk cut crashes OCC.** A single `solid.box` cut over all ~50 low bodies
  segfaulted SolidCraft. Cutting **one body per `solid.box` feature** is
  stable (~180 ms each); the same body-by-body pass is the working method.
- **Five bodies are open shells** that OCC cannot cut, split or stitch:
  `Left/Rigth screen frame`, `Lower chassis rigth`, `lower chasis left` (+1).
  These are the structural walls and were **removed** for the pass — they are
  exactly what the redraw rebuilds. The trimmed result is therefore a
  **silhouette, not a printable part** (37 of 87 bodies remain: bodies fully
  inside the cut zone vanished; spanning bodies were trimmed).
- **Duplicate instances**: cutting by definition name hits only the first
  instance; the extras are removed with their full world name.
- `surface.stitch` does not close the open shells; `solid.split_body` fails on
  them the same way as a box cut.

## Next steps (redraw in SolidCraft)

1. Rebuild the structural parts as **closed solids** at 140 mm: screen frame
   L/R, lower-chassis L/R, upper chassis — instead of editing the import.
2. Size the slide hardware (rods/clamps/bearings) to ~78 mm travel inside the
   ~140 mm lid.
3. Place the Orange Pi Zero 2W beside the keyboard; re-add the reference's
   buttons in the remaining bottom band.
4. Optionally revisit **Y** (currently 80.6 mm): chassis ~30 + lid ~33.

## Files

- `central-unit.step` — original import (untracked).
- `generated/central-unit_screen88.sc` — 8.8" screen adaptation, pre-Z work.
- `generated/central-unit_screen88_before_z140.sc` — snapshot before the trim.
- `generated/central-unit_screen88_z140.sc` / `.step` — 140 mm silhouette.
- ADR: `docs/adr/0008-central-unit-slider-separate-solidcraft-stream.md`.
