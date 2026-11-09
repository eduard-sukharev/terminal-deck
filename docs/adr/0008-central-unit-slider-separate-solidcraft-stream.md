---
status: deprecated
superseded_by: ADR-0009
---

# Central-unit slider: a separate SolidCraft experimental stream

> Deprecated by ADR-0009: the slider replaces the clamshell and is built in
> build123d. This separate SolidCraft stream is closed; its measurements and
> the 140 mm pass are kept in `docs/central-unit-slider.md`.

The mainline is the build123d clamshell (ADR 0002). Separately, an externally
authored "Central unit" **slider** — a Vaio-UX-style deck whose screen lid
slides up to reveal the keyboard — was imported (`central-unit.step`) and
adapted to the 8.8" 1920×480 display in SolidCraft
(`generated/central-unit_screen88.sc`). We pursue it as an **experimental
stream on its own git branch**, built in **SolidCraft rather than
build123d**, targeting a compact deck with **closed Z ≈ 140 mm** (down from
the imported 226 mm). This records the stream and its target, not a decision
to replace the clamshell: the question it answers is whether the slider form
factor is viable for the 8.8" screen.

## Why 140 mm

Computed from the real parts, not guessed:

- JD40 keyboard plate is **77.75 mm** deep (along the slide), **230.15 mm**
  wide; the keyboard is the tallest content along Z.
- 8.8" screen module is 231 × **64.5** × 6.5 mm; its driver board (55 × 45.5
  × 4.6) sits back-to-back behind it and adds no Z.
- Orange Pi Zero 2W is 65 × 30 × 6.7 mm — it fits **beside** the keyboard in
  the 334.8 mm width, so it adds no Z.

Content floor is therefore ~106 mm (keyboard + margins). The slide mechanism
(rods inside the lid, ~78 mm of travel to expose the keyboard) is what sets
the lid to ~140 mm. **Overlap model A**: the lid fully covers the chassis
when closed, so the closed device reads as one screen panel; opening slides
the lid up by the keyboard depth.

## Why the import is not the final model

The imported STEP is fragile to edit and this is the reason the stream ends
in a redraw, not a trim:

- Five bodies import as **open / non-solid shells** (both screen frames, both
  lower-chassis halves, +1). OCC refuses to boolean-cut or split them
  (`boolean Cut: no result` / `boolean Intersect: no result`); `surface.stitch`
  does not close them.
- One `solid.box` cut across the whole assembly **crashes SolidCraft** (OCC
  segfault; a prior `solid.box` crash exists in the project's crash log).
  Cutting **one body per feature** is stable (~180 ms each).
- Duplicated instances (screws, rail tabs) can only be removed by their full
  world name; a cut targeted by definition name hits only the first instance.

The 140 mm destructive pass (`generated/central-unit_screen88_z140.*`) is a
**silhouette / feasibility proof, not a printable part**. The durable path is
to redraw the structural parts as closed solids in SolidCraft.

## Consequences

- No code in the build123d pipeline (`case/`, `components/`, `layouts/`)
  changes for this stream; it does not consume `config/` sizing.
- Documentation lives in `docs/central-unit-slider.md` (geometry budget,
  experiment log, next steps). The clamshell glossary `CONTEXT.md` only
  points at it.
- Large binary artifacts (`central-unit*.step`, `*.sc`) stay on disk,
  untracked, as the repo already treats generated geometry.
