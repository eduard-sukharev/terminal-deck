---
status: accepted
supersedes: ADR-0007
---

# The slider replaces the clamshell as the project's form factor

The 8.8" 1920×480 panel and the 40% keyboard that the project already targets
fit a **slider** better than a clamshell: the screen stays visible with the
device closed (it reads as a tablet), and the keyboard is revealed by sliding
the screen lid along the face instead of unfolding it. The reference for the
form and the mechanism is an externally authored STEP, "Central unit"
(`central-unit.step`, ADR-0008's experiment): a flat-faced slab whose lid
rides two steel guide rods over a chassis. We adopt that form for the whole
project and build it in **build123d** (ADR 0002), not in the SolidCraft stream
of ADR-0008. The clamshell, its Visor, its Well-as-thickness-trick and its
Torque hinge (ADR-0007) are retired.

## Targets

Derived from the real components, not copied from the reference:

- **Closed face height 140 mm — HARD.** The budget is the slide, not the
  content: `travel (≈93) + one LM…LUU bearing (35) + end supports + lid top
  bezel`. Travel is not the keyboard depth (77.75); it is the keyboard's
  front offset plus its depth plus clearance (≈93), because the lid's lower
  edge must pass the keyboard's *upper* edge when open.
- **Thickness ≈ 56 mm — GOAL** (the clamshell closed at 57). Chassis (keyboard,
  SBC, bearing clamps) plus screen lid (panel, driver, guide rods).
- **Width ≈ 260 mm — derived**: keyboard 230.15 / panel 231 plus two side
  pods (guide rod, C-channel, bearing clamp, accessary-rail pockets). It is
  not the reference's 335 mm, which is padded with decorative rails and an
  antenna.
- **Battery external** on an accessory rail, as the reference does; an
  internal pack (ideally a small one that keeps the system alive while
  external packs are swapped) is added later only if the envelope allows.
- **Accessory rails: picatinny interface, not modelled.** The side walls get
  square-nut pockets printed in (nuts inserted during a print pause); the rail
  bars themselves are user-supplied accessories.

## Mechanism

- Two steel guide rods, one per side, run **inside the screen lid's thickness,
  at the sides of the panel**, in a C-channel in the lid's side walls.
- Two **linear bearings (LM…LUU, default LM6LUU, one per rod)** are clamped in
  **Bearing Clamps standing on the chassis deck behind the keyboard**, rising
  above the base surface. The clamp enters the lid's C-channel through a slot;
  the rod slides through the bearing.
- **One bearing per rod, not two.** Two per rod would put the rod at
  `travel + spacing + bearing length ≈ 160 mm` and break the 140 mm face
  height. The bearing size is config-selectable; the build fails if the chosen
  combination does not fit the budget.
- The display/driver cable crosses the sliding joint in a **drag chain** in a
  channel along the slide axis, behind the screen. The channel and its anchors
  are reserved and validated now; the chain links are a separate printable
  part.

## What is kept from the clamshell

The parts that are form-factor-independent: the `Component → Placement →
Assembly → Enclosure → Features → Export` pipeline, the constraint-based
layout composer, Sections with stepped Seams and Seam lugs (ADR-0003/0006), the
Tray/Deck split with a horizontal Parting plane, the fastener library, the
keyboard subsystem, and the STEP/STL/SVG/glTF exporters. The screen lid keeps
the Bezel/Lid-shell split, but the bezel is an **inverted tray** (front face
with the glass opening, walls running back) closed by a **flat back panel**;
the screen and driver live in the tray.

## Considered options

- **Keep the clamshell** — rejected: the screen is hidden when closed, and the
  Visor/hinge/closed-plane machinery exists only to fold it.
- **Two supported layouts (clamshell + slider)** — rejected: two case builders,
  two validation sets and two sets of docs for one device.
- **Copy the reference envelope 335 × 80.6 mm** — rejected: the extra width
  and thickness are decorative/accessory volume, not component volume.
- **Four bearings (two per rod)** — rejected: it is what sets the reference's
  226 mm height; 140 mm needs one long bearing per rod.

## Consequences

- ADR-0007 (Torque hinge) is superseded; ADR-0008 (separate SolidCraft stream)
  is deprecated. ADR-0002 (build123d) and ADR-0003/0006 (Sections, Parting
  plane, Seam lugs) stay.
- Clamshell terms (Base, Lid, Visor, Closed plane, Torque hinge, Leaf, Hinge
  axis, Travel stop, Cable guard, Cable slot) are retired in `CONTEXT.md`.
- The spec is `docs/form_factor.md`; the reference measurements and the
  140 mm trim experiment stay in `docs/central-unit-slider.md`.
- Code migration: `case/base.py`/`case/lid.py` become `case/chassis.py`/
  `case/screen_lid.py`, `components/hinge.py` becomes `components/slide.py`,
  and the layout recipe becomes `config/layouts/slider.yaml`. It lands as a
  separate step after this spec.
