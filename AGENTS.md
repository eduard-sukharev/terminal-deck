# AGENTS.md

This file provides guidance to AI coding agents (Claude Code, etc.) when working with code in this repository.

Parametric **slider** cyberdeck CAD generator (build123d), for field debugging
of 3D printers. Target hardware: Orange Pi Zero 2W SBC, 8.8" 1920x480 HDMI
display, 40% Cherry-MX-compatible RP2040/QMK keyboard. The screen lid slides
along the face over the chassis to reveal the keyboard (ADR-0009; the clamshell
is retired). This is **not** a maker platform — no GPIO, sensors, LEDs, or
decorative elements. Priorities: robustness, serviceability, printability,
parametricity, reusability.

> **Status.** `docs/form_factor.md`, `CONTEXT.md` and ADR-0009/0010/0011/0012
> plus ADR-0013 (rods under the display), ADR-0014 (the walled Well and the
> plate mounted to its lower faces), ADR-0015 (per-piece staggered Section
> Seams), ADR-0019 (the Tray's vertical side walls and its end-wall base
> taper) and ADR-0020 (the printed accessory rail on those walls) define the
> slider, and ADR-0021 (deep conical head recesses for the Tray's band screws)
> deepens its screws; ADR-0022 runs the base taper through the long-wall
> stations' cones, and ADR-0023 fillets the cones' mouth rims (1.0 mm) and
> through-lips (0.47 mm) while the walls' edges with the floor stay sharp;
> ADR-0024 fills the Well ring back over the plate's notches and fillets each
> wall column into its cavity wall (1.5 mm) in both halves. The data skeleton
> and the CAD shell are implemented: `--layout slider` (the only layout) derives
> the budget and builds/exports the chassis (Tray + Deck, split at the band
> joint), screen lid (Bezel + Back plate, split at the band joint), the printed
> FPC guard, guide rods, the printed Rod clamps and Bearing clamps, the
> printed accessory rail and its washer pucks, the keyboard plate with the
> Well's ears, notches and M2 clearance holes, and the closed/open assembly. Each shell piece is cut on **its own** Seam (Deck and
> Bezel straight at `x = −14`; Tray and Back a 45° trapezoid at `+10`/`+18`),
> so a screwed pair laps and a centreline band station cross-ties it; every Seam
> also carries two fin-pair glued filament pins (ADR 0006). The
> retired clamshell code,
> config, recipe and tests have been removed. Still next: the
> drag-chain channel, the aux buttons above/below the display (their space and
> depth are reserved) and the redesigned vents (they must stay out of both joint
> bands).

## Build volume

Target printer build volume: **220 × 220 × 256 mm** (X × Y × Z). Every
printable part (chassis tray/deck, screen-lid bezel/back, keyboard plate,
bearing clamp, etc.) must fit this envelope in its intended print orientation;
if a part would exceed it in every viable orientation, split it into joined
printable pieces (alignment features + fasteners) rather than silently
exceeding the limit. See `.agents/skills/cad/references/fdm-printing.md` for
the full FDM manufacturability ruleset (wall thickness, clearances, overhangs,
boss design, build-volume checks).

## Environment (critical)

- **Use the `cyberdeck` conda env** — the base conda env is Python 3.7 and
  fails to import (`typing.Final` missing). Create it once, then activate:
  ```bash
  conda create -n cyberdeck python=3.12 && conda activate cyberdeck
  pip install -r requirements.txt
  ```
- **Backend:** build123d (ADR 0002). Core components are ported; the case
  parts are rebuilt for the slider per `docs/form_factor.md`.

## Commands

```bash
make data                    # data layer only (config → components → layout → validation)
make all                     # full CAD + exports (STEP/STL/SVG/glTF to generated/)
make chassis                 # Tray + Deck + their left/right Sections (no lid)
make screen_lid              # Bezel + Back + their left/right Sections (no chassis)
make chassis_tray            # one piece + its Sections, e.g. chassis_deck,
make screen_lid_bezel        #   screen_lid_back (each builds nothing else)
make test                    # pytest
make check                   # py_compile all modules (run after `make data`)
make rebuild                 # force a full rebuild (ignores the build cache)
make clean                   # remove generated files and __pycache__

# equivalent direct invocations
python main.py --config config/default.yaml --layout slider --steps data
python main.py --steps all
python main.py --steps all --targets display                 # display sub-assembly only (fast)
python main.py --steps all --targets display,chassis         # selected targets
python -m pytest tests/test_slide.py             # single test file
python -m pytest tests/test_slide.py::test_name -v   # single test
```

`--steps data` runs config → components → layout → validation and prints the
report; no CAD library needed. `--steps all` additionally sizes the
chassis/lid, bearing clamps and cutouts, and builds+exports the assembly,
chassis and screen lid.

**Edge treatment runs per Section** (after the lossless rejoin check): OCC can
segfault on a chamfer, so `cad_helpers` runs each attempt in a child process
(`utilities/_cad_worker.py`); a failing edge is skipped with a SOFT warning.

**Builds are incremental** (`utilities/build_cache.py`). Every exported target
is fingerprinted from the inputs that can move it — the pipeline sources (frame,
budget, placements), the `config/` tree and the layout recipe, plus the modules
that build that piece (`PART_SOURCES`) — and its exports are reused when the
fingerprint and all three artifacts (STEP/STL/glTF) are unchanged: the solid is
neither built nor written. So editing `case/screen_lid.py` rebuilds the lid, its
Sections and the assemblies that embed it, and leaves the chassis alone; a
no-change `make all` takes seconds instead of minutes. The cache is
`generated/.build-cache.json` (git-ignored); `make rebuild` / `NO_CACHE=1` /
`--no-cache` force a rebuild and still refresh it, `--metrics` bypasses reuse
(it needs every selected target built), and `make clean` removes it. Sections
fingerprint together with their whole piece, and the assembled targets
(`assembly`, `assembly_opened`) depend on both halves.

**Selective build targets** (`--targets`, comma-separated), implemented set:

- `assembly` — chassis + screen lid + guide hardware + components
- `assembly_opened` — the open pose: lid, rods and Rod clamps slid by the travel; bearings/Bearing clamps fixed
- `chassis` — chassis shell + keyboard, SBC, controller
- `chassis_left` / `chassis_right` — whole-chassis Sections: compounds of the
  real Tray and Deck pieces (reference only; the printable chassis parts are the
  Tray and Deck Sections below)
- `chassis_tray` — the lower bowl with the twelve screw columns; `chassis_tray_left/right` — its printable Sections
- `chassis_deck` — the purely prismatic Deck with the Well ring, its eight M2 insert bosses, the seats and the band insert bosses; `chassis_deck_left/right` — its printable Sections
- `screen_lid` — lid shell + display + driver + guide rods + Rod clamps
- `screen_lid_left` / `screen_lid_right` — whole-lid Sections: compounds of the
  real Bezel and Back pieces (reference only)
- `screen_lid_bezel` / `screen_lid_bezel_left/right` — the display carrier and its printable Sections
- `screen_lid_back` / `screen_lid_back_left/right` — the flat back plate and its printable Sections
- `slide` — guide rods + Rod clamps + LM…LUU bearings + Bearing clamps
- `rod_clamp` — one printable Rod clamp
- `bearing_clamp` — one printable Bearing clamp
- `fpc_guard` — the printable FPC grille plate (bonded to the display's back)
- `rail` — the printed MIL-STD-1913 rail blank; `rail_washer` — one printed washer puck (both ADR-0020)
- `keyboard_plate` — the switch plate with the Well's ears, notches and M2 clearance holes; `keyboard_plate_left/right` — its Sections, split along the Plate Seam
- `display` — LCD panel + HDMI driver combined
- `components` — all per-component debug STLs
- `comp:<role>` — a single component's raw STL (e.g. `comp:driver`)
- `all` — every target above (default)

Every wide part is exported whole for reference and split into **two**
Sections each (ADR 0015) on **its own** Seam: the Deck and the Bezel straight
at `x = −14`, the Tray and the Back plate as a 45° trapezoid at `+10` in the
middle and `+18` at the end walls. The Seams of a screwed pair never coincide,
so the pieces lap and a band station in the lap cross-ties them. Each Seam also
carries **two fin-pair glued filament pins** (ADR 0006): two printed fins with a
2.0 mm slot, and a 1.75 mm filament offcut glued in. The keyboard plate splits
along its row-jogging Plate Seam between keys (ADR 0014). The Sections must fit
220 × 220 × 256 mm or the build fails.

## Architecture

Pipeline: `Component -> Placement -> Assembly -> Enclosure -> Features -> Export`.
Everything derives from reusable components; every dimension originates from
configuration, a measured component, or calculated geometry — never
intuition. Wire-up lives in `main.py` (`BuildPipeline`, `run()`).

- **Data layer (implemented, no CAD library needed):** `components/base.py`
  (`BoundingBox`/`Hole`/`Connector`/`Keepout` + `Component` ABC),
  `utilities/config_loader.py`, `utilities/fasteners.py`,
  `utilities/validation.py`, `layouts/*`, `assemblies/assembly.py`,
  `routing/cable_routing.py`, and the `keyboard/` package (KLE → layout →
  switch/stabilizer libraries → plate geometry model + its own validation).
- **CAD generation (required build123d):** `Assembly.build()` unions component
  solids at their placements; `case.slider_frame.SliderFrame` derives the
  world-frame dimensions from the layout + budget; `case.chassis.Chassis`
  builds the two halves at the Parting plane (ADR-0012): `build_tray()` is the
  prismatic bowl (ADR-0019: vertical X walls, a 15° base draft on the end
  walls that runs up to the band's bottom and steps around the station pads —
  `geometry/base_taper.py`) and the twelve straight screw columns;
  `build_deck()` is the purely prismatic Deck: the keyboard Well, the two
  bearing-clamp seats (merged seat blocks with foot pockets) and the insert
  bosses; `build()` returns their compound; `tray_sections()` /
  `deck_sections()` split a half on the Seam configured for **that piece**
  (ADR-0015), through `geometry.split.split_part`.
- `components/accessory_rail.py` builds the printed rail blank and the washer
  puck from `geometry/rail_mounts.rail_mounts(config, joint)` (ADR-0020), the
  same pure-data pattern `Chassis.build_tray()` cuts the pads, gusset ribs,
  square pockets and M4 bores from; `place_rail()`/`place_rail_washer()` put
  them on either wall.
- `case.screen_lid.ScreenLid.build_fpc_guard()` produces the printed FPC
  grille plate (planform, channel and grille from `SliderFrame`; a separate
  target, placed on the display's back); `build_bezel()` produces the
  inverted-tray front with the glass opening and the prismatic band joint;
  `build_back()` the flat plate with the clamp slots, the Rod-clamp inserts and
  the band's countersunk screws; `bezel_sections()` / `back_sections()` split
  them on their own Seams;
  `components/slide.py` also builds the purchased `build_guide_rod()` /
  `build_linear_bearing()` solids and the printed `build_rod_clamp()` /
  `build_bearing_clamp()` parts (its data model and the budget stay CAD-free);
  `geometry/*` hold the primitives (the two band joints live in
  `geometry/joint.py` and `geometry/chassis_joint.py`, the Well/plate pattern in
  `geometry/well_mounts.py`, the Seam cut in `geometry/split.py`, the Seam pins
  in `geometry/seam_joint.py`, and the Tray's base taper in
  `geometry/base_taper.py`, the rail stations in `geometry/rail_mounts.py`, and
  every concave/bed/cone edge treatment plus the columns' wall-merge fillet in
  `geometry/edge_treatment.py`).
  The drag-chain channel, vents and connector cutouts are the next refinement.
- `geometry/well_mounts.py` is the single source for the Well and the plate's
  mounting pattern (ADR-0014): the plate frame (the keyboard's 180° placement),
  the eight M2 stations, the ears, the notches and the plate Seam, all as pure
  data. `Chassis.build_deck()` builds the ring and the bosses from it and
  `components/keyboard_plate.py` injects the same pattern into the plate; the
  keyboard package itself receives only rectangles and never imports the
  enclosure.
- `utilities/cad_helpers.py` is the **only** CAD adapter (build123d); it imports
  lazily so the data layer stays importable without a CAD library. Geometry
  modules must go through it, not `import build123d` directly.
- `exports/` exporters delegate to build123d exporters (STEP/STL/SVG/glTF).
  The glTF exporter (`exports/export_gltf.py`) takes a
  `cad_helpers.ColoredAssembly` (built by `Assembly.build_colored()`, colors
  from `utilities/colors.py`), not a single fused solid.
- **Assemblies are always also rendered to glTF with one color per
  component.** Every component role needs its own opaque entry in
  `utilities/colors.py` (`tests/test_colors.py` fails otherwise); use
  transparency only where it helps you see inside — currently the chassis and
  lid shells. Any new assembly or build target that groups parts must go
  through `Assembly.build_colored()` and export glTF too.

### Layout system

The single layout, `slider`, is **constraint-based**: it declares placements
as data rather than code.

```
config/layouts/slider.yaml      the recipe (the only one)
  → layouts/recipe_loader.py    parses YAML into Constraint dataclasses
  → layouts/constraints.py      constraint types (EdgeAlignment, CenteredOn,
                                 FixedPosition, CenteredGroup, Clearance,
                                 ZStack, SharePlane, RegionConstraint,
                                 CablePath, FootprintMatch, RelativePlacement,
                                 TargetEnvelope) — pure data, no logic
  → layouts/composer.py         LayoutComposer resolves each constraint in
                                 recipe order via a registered resolver,
                                 accumulates placements, and produces a
                                 ConstraintReport (HARD violations fail the
                                 build; SOFT warn; GOAL is a reported metric)
  → layouts/resolvers/*.py      one resolver per constraint kind
```

Most placements are derived from component sizes and config; the recipe's
`fixed_position` entries are the deliberate manual overrides, each annotated
with why it cannot be derived. The envelope itself comes from the derived
slide budget (`{budget.chassis_height}`, `{budget.rear_band}`, …) rather than
restating the mechanism formulas in YAML.

Layouts contain no CAD, only placements. `layouts/layout_recipe.py` is the
adapter that runs a recipe through the composer and returns placements;
`layouts/layout_constrained.py` is its composer-backed base class.

### Keyboard subsystem

`keyboard/` is a self-contained geometry generator (see
`docs/keyboard_architecture.md`) with **no dependency on cyberdeck code** —
it must stay importable without a CAD library. The cyberdeck adapters
(`components/keyboard_plate.py`, `components/rp2040_keyboard.py`) extrude its
model during the CAD pass.

Data flow: KLE JSON → `keyboard/layout/kle_parser.py` → internal
`KeyboardLayout`/`Key` model → `keyboard/switches/kb_builder.py` +
`keyboard/stabilizers/kb_builder.py` → `keyboard/geometry/plate.py` →
solid, consumed by the cyberdeck assembly. Physical dimensions live in
`keyboard/reference/*.yaml`, never hardcoded in source. Every generated plate
is checked by `keyboard/validation.py`.

## Conventions (from `docs/design_spec.md` — do not violate)

- **No magic numbers.** Every dimension comes from config, a measured
  component, or calculated geometry. Unmeasured values carry
  `# TODO: measure`.
- Units: mm always. Coordinates: +X right, +Y along the slide (toward the
  screen end), +Z up (thickness); origin = centre of the chassis footprint on
  the table plane. Never redefine origins.
- `wall_thickness = config.wall.thickness` is the single wall parameter.
- **Edge treatment follows the material dihedral.** Measure the angle between
  the two faces through the material: `<= 90°` is a convex (outside) edge,
  `>= 270°` is a concave (inside) edge — one square joint read from either
  side. Concave edges are **filleted**: every boss base where it meets a floor,
  wall or ring, and every sharp inside corner of the shell (ADR-0025,
  `geometry/edge_treatment.py`, `chassis_joint.column_fillet`). Convex edges
  are **chamfered**, always 45° (`corners.chamfer`, `edges.*`): outside faces
  are never filleted. A fillet must print without support **in that part's own
  print orientation** — judge the joint there, not in the assembly's Z (the
  Deck prints face down, so its inner ceiling is the bed face and its bosses
  are filleted) — and a concave joint that opens toward the part's bed keeps
  its 45° chamfer instead (the round would print as a curved overhang). A
  shell's cavity corners also carry the **derived inner chamfer**
  (`cad_helpers.inner_corner_chamfer(chamfer, wall)`, ADR-0016): a square
  cavity corner meets a 4 mm outer chop on a 2 mm wall in a knife edge.
- Layouts contain **no CAD** — only placements.
- Slide math lives in `components/slide.py`, cable routing in
  `routing/cable_routing.py`, fasteners in `utilities/fasteners.py` — never
  recreated inline.
- Component sizes/holes are verified against real datasheets (see
  `docs/component_spec.md`); SBC connector edge positions are user-calibrated
  measurements recorded in `components/orange_pi_zero2w.py`.

## Config

`config/default.yaml` is merged with `display.yaml`, `keyboard.yaml`,
`hardware.yaml`, `slide.yaml` (topic files override).
`config/layouts/slider.yaml` holds the constraint recipe for the `slider`
layout. `utilities/config_loader.py` maps YAML to frozen dataclasses; adding
a YAML key usually requires adding a field to the matching dataclass.

The face is flat — there is no keyboard slope and no slope machinery in the
code (the clamshell's `deck.slope`/`tilt_x`/`deck_level_at` are gone). `config.slide` holds the purchased
linear guide (rod diameter/length, bearing model, clamp, travel margin, chain
pitch/width/bend radius) and the accessory rail (`rail.stations`,
`station_spacing`, `width`, `height`, `pitch`, `screw`, `head`, `nut`, `fit`);
the build checks the chosen combination against the
140 mm face-height budget. `config.chassis_joint` holds the Tray/Deck band
(band height, boss cap, per-wall station insets, screw size);
`config.parting` sets the plane it sits on. `config.keyboard.plate` holds the
plate thickness, the `wobble` allowance and the corner radius: there is no
`edge_margin` knob (the plate is the Cutout + one wall per side) and
`well_front_margin` is not configured either — both are derived (ADR-0014).

Gotchas:

- **The face-height budget is the binding constraint.** `travel + bearing
  length + 2 * (Rod clamp + clearance) + end supports + lid bezel ≤ 140`.
  The front margin is the budget's **remainder**, not a knob:
  `well_front_margin = 140.00 − 51.50 lid stack − 80.85 plate depth = 7.65`
  (floored at 7.50 = wall 2.00 + the 5.50 front lip an M2 boss needs). Travel
  is `7.65 + 80.85 + 5.0 clearance = 93.50`, not the keyboard depth (77.75);
  ADR-0014's plate is what sets it. One bearing per rod; the default is the
  short LM6UU (19 mm) because the 35 mm LM6LUU plus the end clamps does not
  fit. A second bearing per rod breaks the budget.
- **The accessory rail sets the Tray's X wall interface (ADR-0020).** Two M4
  stations per wall at `y = ±30` (`slide.rail.stations` / `station_spacing`,
  which must be a whole number of slot pitches so both screws land on rail
  bridge centres), each a full-height pad (`2 × wall` deep, `11.2` wide) with a
  square `10.0 × 10.0 × 2.6` pocket for the printed washer puck and two 45°
  gussets sharing one obstacle-derived run (`3.05`). The puck captures a
  DIN 562 M4 nut; the derived 8.8 mm stack pins the screw to **M4 × 10**. The
  rail blank is `21.2 × 80 × 5.0`, counterbored, overhanging the wall 9.6 mm a
  side. The pad and gussets must stay clear of the band joint's X-wall columns
  (`±114.083, ±44.25`, Ø10) -- `slide-rail-*` are HARD checks. The rail's
  picatinny profile (10 mm slots, hex top) is a **later slice** on an unchanged
  interface; do not move the stations or the holes for it.
- **The lid is the larger half; the chassis grows to it.** The guide span is
  fixed by the purchased bearing and the end clamps, so `chassis height =
  max(keycap top + rear band, guide span + top bezel)` and the
  two halves share the closed face (140.00). Do not shrink the lid to the
  keyboard-driven chassis depth: the lid would no longer clear the bearing at
  the open pose. The added rear band is empty behind the bearing-clamp seat.
- **The guide stance is under the display and is derived, not chosen.** The
  rods sit at `rod_x = ±94.98` (ADR-0013): `min(post 99.68, seat 97.48, head
  107.50) − rod.side_margin 2.50`. The seat bound is the tightest and it grows
  with the width (ADR-0014 made the plate the width driver). Change a clamp
  wall, a seat wall or a station inset and `rod_x` follows — do not pin it. The
  slot, the Deck seats, the pockets, the Rod clamps and the lid band post all
  read `rod_x`.
- **The width is the content plus the lid's drafted side wall, nothing else.**
  The content is now the **keyboard plate (233.25)**, not the 231 mm panel: it
  bears on the Well ring, so it sets the case at **241.17 mm** =
  233.25 + 2 × 3.96 side pod (wall 2.00 + shell 0.35 + lid draft 1.61). The
  Tray's X walls are vertical (ADR-0019: the accessory rail bolts to them), so
  no chassis draft enters the width. Nothing
  lives beside the keyboard: the lid band post is inboard of the cavity wall
  (`rod_x + rod_clamp.width/2 + corner_clearance`) and `slide.joint.corner_post`
  is retired. The lid's draft inset is measured over the display's height, not
  the hardware envelope.
- **The lid's thickness is the Z stack under the panel.** `head crown 9.0 +
  component gap 1.5 + sag 0.5 + FPC guard 1.6 = 12.6` cavity, so lid 24.45 and
  device 57.75. The display is placed at `panel_inner + budget.display_cavity`
  by the layout; the frame raises if the placement disagrees. The guard is a
  separate printed target (`fpc_guard`), tape-bonded to the display's back; its
  underside is what the head must clear.
- **The Bezel's band posts are capped at 45°, not run up to the panel
  (ADR-0017).** The Bezel prints face down (front panel on the bed), so the
  band is printed last and a post that stopped at `band_z1` would print its
  flat top as a bare ledge on the wall. The four corner posts and the six
  long-side pads keep their **full depth over the 6 mm band** (the M3 insert is
  buried there) and are closed by `cad_helpers.support_cap`: from every
  cavity-facing side the material rises at 45° until it meets the wall, so the
  print grows out of the wall instead of bridging. Every post is then **cut to
  `_outer_shell()`** — the Bezel's outside is drafted above the band and its
  corners are chopped, so an unclipped cap pokes through both at all four
  corners. That adds ≈ 4.2 cm³ over the whole Bezel; a full-height column (the
  Deck's rule) would add ≈ 15 cm³ and bury the display cavity. The caps sit in
  the free band (`|y| ≥ 50`) and never cross the `x = −14` Seam. The Bezel must
  have **no overhang face** in its print orientation and nothing outside its
  outer shell — `tests/test_slider_case.py` scans the built solid with
  `overhang_faces` and subtracts the shell, which is how the ledge and then the
  protruding caps were caught.
- **The band is prismatic and solid** — vents stay out of it. The band joint
  has **twelve** stations, but the corner and long-wall stations sit `side_inset`
  (4.5) from the vertical walls (boss capped at 7.80); **five** of the
  **front-wall** stations (two corners, two side, one centreline) reach into the
  keyboard plate's front border, so the plate is notched at each (5.30 × 1.45,
  1.10 bite). The **Well ring above is continuous** (ADR-0024): it fills the
  same plan area and fuses to the band boss, so the Well's outer face is one
  unbroken wall while the sheet below gives way — the ring stays sealed on its
  inner face (its printable remainder is `ring − intrusion` = 1.25). The
  rear-wall stations sit in the free band behind the keyboard. At this width a
  Tray column at mid-side would run through the plate.
- **A wall column fillets into its cavity wall; a Well boss into the ring
  (ADR-0024).** A station sits 2.5 mm inboard of the front/rear cavity face
  while its strict column is Ø7.30, so the cylinder pierces the face and leaves
  two vertical reentrant chords per side — a crack starter in the most handled
  part of the case. `geometry.edge_treatment.merge_column_walls` fillets them at
  `chassis_joint.column_fillet` (1.5 mm) **in both halves**, right after the
  columns are unioned and before the taper fill/cut, the access cones, the
  insert holes and the Seam pins (applied late, the same edges arrive segmented
  into stubs a fillet cannot roll off). The eight Well M2 bosses take the same
  fillet on the ring's front/rear outer faces, which their discs pierce 2.0 mm
  out — a second call with its own column set, because the chords where a
  *band* column crosses that face must stay sharp: at the five notched stations
  its chord passes ~0.1 mm from the M2 boss's, so no fillet rolls between them
  (as is the corner chamfer and the end stations' X walls). A front-lip M2 boss
  whose lip is narrower than one wall bridges outboard as a **rectangle**
  (ADR-0026): its ends sit one `minimum_feature` inside the ring and the facing
  wall, and its chords and base edges are selected by `rect_junction_edges` /
  `rect_base_edges`. Every Well M2 boss is also widened by
  `keyboard.mounting.boss_widen` (1.0 mm, 0.5 per side) over the bare insert +
  margin. Every boss base is also rounded at
  `chassis_joint.boss_base_fillet` (0.6 mm) by
  `fillet_boss_bases` — every chord merge runs before any base round, so a base
  round beside a neighbouring family's chord cannot block it. The Tray's column
  bases and most Deck band bases take the round; the crowded end-station and
  most M2 bases are skipped with a SOFT warning. The HARD checks
  `slide-chassis-joint-column-fillet` and `keyboard-mounts-fillet` require
  `column_fillet + minimum_feature` to fit the tightest wall chord (2.66 mm, the
  strict column) and the tightest Well chord (2.24 mm).
- **The chassis splits at the Parting plane, band-only (ADR-0012).** The 6 mm
  band is split 3 mm each side of `parting_z`, and **both halves are
  prismatic** (ADR-0019 removed the Tray's draft): the band width, the base
  width and the closed-face width are one number (`width`). The Tray's vertical
  end walls carry a 15° base taper from the table up to the band's bottom
  (`chassis_joint.taper_angle` / `taper_runout`, `geometry/base_taper.py`) —
  a draft, so the cavity follows and the wall keeps its thickness. ADR-0022
  runs the taper **through** the six long-wall stations: at the table the
  sloped face sits 2.32 mm inside the access cone's mouth (no floor sliver),
  the pier ring around the pocket is 1.45 at the taper's top and only grows,
  and each wall is one full-width run (214.5 mm). **Only the four corners
  keep a pad** (stop Ø13.80 — pad + runout), the rounded stops the taper
  starts and ends on, set off the corner as before. The HARD checks are
  `chassis-taper-draft`, `-band`, `-opens`, `-pad`, `-stop` and `-fillet` in
  `utilities/slider_validation`. ADR-0023 fillets the cones' own outside
  edges — the mouth rims at the bed (`chassis_joint.taper_fillet` = 1.0 mm,
  tangent run only ~1.02 mm) and the lips where the taper flares a cone open
  (radius-limited to 0.47 mm so the fillet stops one minimum feature below
  the pocket's neck; a larger radius would climb the cone and seal the
  driver access). The selector (`geometry.edge_treatment.cone_cut_edges`)
  matches only cone-against-plane edges at the bed or on the taper's outer
  slope: the long edges where the walls meet the floor, the interior rings
  at the cavity floor and the cavity-side flares stay sharp.
  **Twelve** M3 × 6 come up from below (`grip` = one wall = 2.00)
  into
  heat-set inserts in the Deck's band bosses. The heads are buried one wall
  below the Parting plane in a **deep conical access cavity** (ADR-0021): the
  button head seats at `z_seat = parting_z − wall` = 14.15 (Ø6.10 pocket ×
  1.65 deep, seat ring 1.45), and the driver reaches it down a cone whose
  mouth stays one minimum feature inside the column's floor footprint
  (`mouth_radius = base_boss/2 − min_feature`: Ø6.60 at the long walls,
  Ø8.80 at the ends, half-angles 1.1° / 6.1°) — the pier's wall at the floor
  is `margin − mouth_radius` = 1.20 (never a knife edge), the cone prints
  without a ramp, and the driver enters straight along the screw axis. The
  Tray column is a **strict cylinder Ø7.30** (pocket + 2 × min_feature) from
  the cone's neck (z 12.50) to the Parting plane, and a **frustum below** the
  neck from Ø7.80 at the floor down to the strict diameter — conical outer
  wall beside the cavity. The Deck's insert boss stays a straight full-height
  cylinder. ADR-0018's keyhole stays the lid's band joint.
  Each boss is a **full-height
  column** from the Parting plane up to the Deck's inner ceiling
  (`chassis_top − wall` = 30.30, 14.15 tall), because the Deck prints face
  down and a boss that stopped at the insert (4 + 1.5 margin) would overhang
  off the band's wall. The two centreline long-wall stations are ADR-0015's Seam
  interlock (see below). The stations are sized per wall:
  `station_inset` 6.5 from the vertical X wall,
  `side_inset` 4.5 from a vertical front/rear wall (the keyboard plate). The
  boss is capped at `min(10, 2·(surface − min_feature))` — the long sides only
  afford **7.8 mm** — and every wall is vertical, so the Tray column is a
  straight boss of that diameter (`base_boss == boss`); `_column` keeps the
  frustum path for a station whose floor margin is tighter than its band
  margin. The outer band
  is **plain**: no relief is cut into it (ADR-0016 removed ADR-0012's
  scallops).
  Do not widen the insets: the 2.3 mm insert skin at the long sides and the
  1.4 mm countersink skin are the binding constraints.
- **Every printed piece has its own Seam, and the pairs stagger (ADR-0015).**
  The Deck and the Bezel split straight at `x = −14`; the Tray and the Back
  plate split on a 45° trapezoid at `x = +10` across the middle, stepping to
  `+18` at each end wall (the jog starts at each end wall's inner face, so the
  run is 8 mm). No two Seams of a screwed pair coincide: the Tray/Deck and
  Bezel/Back laps are both **24 mm** and the Deck/plate lap is **9.24 mm**. The
  band station on each long wall's centreline, `(0, ±65.50)`, sits between the
  two Seams, so its screw clamps a Deck piece to the *other* Tray piece — that
  is the interlock, not a new fastener. The lid's band joint carries the same
  centreline pair, `(0, ±65.00)`: **ten** stations, four on one Section of
  each lid part and six on the other (the pair falls right of the Bezel Seam
  and left of the Back's). Do not put
  a Seam back on the centreline or make the pair straight and parallel:
  `slide-seam-offset`, `-stagger`, `-clear`, `-interlock` and `-stations` are
  HARD.
  `config.slide.split` is keyed **per piece** (`chassis_tray`, `chassis_deck`,
  `screen_lid_bezel`, `screen_lid_back`); the old `chassis` / `screen_lid`
  keys are retired and warned about.
- **Every Seam takes two fin-pair filament pins (ADR 0006).** A pin is two
  parallel printed fins `1.4` thick, `2.0` apart, `2.0` tall and `10` long
  across the Seam, with a 45° `1.0` chamfer on each fin's *outer* top edge and
  the slot faces left square. A 1.75 mm filament offcut is glued into the
  2.0 mm slot while the part is assembled, so the Sections register before the
  band screws are in. `geometry/seam_joint.pin_planes` is the single source for
  the four substrate surfaces (Tray floor up, Deck top skin and Bezel panel
  down, Back plate inner face up); the frame cross-checks it. The pins are
  unioned into the half *before* the split, so each Section prints 5 mm of every
  fin. Sites are placements in `slide.seam_pin_sites` (part-frame Y, annotated
  with the feature each avoids) — never derive them, the interior is what
  decides. `slide-seam-pin-fit` and `-clear` are HARD.
- **The Well and the plate are one derived pattern (ADR-0014).** The Deck's
  Well is a 2.00 mm ring around the Cutout from the Deck top (32.30) down to
  the plate top (17.80); the Cutout is the keycap footprint + 2 × wobble
  (`keyboard.plate.wobble` 0.60): 228.05 × 75.65 → 229.25 × 76.85. The plate is
  the Cutout + one wall per side (233.25 × 80.85 × 1.5 at z 16.30) and **bears
  on the ring's lower faces**: there is no Well floor and **no floor
  standoff**. Eight **M2×4** screws come up from below through Ø2.20 holes into
  Ø3.00 × 3.0 inserts in Ø6.00 bosses (z 17.80–30.30, full columns to the
  Deck's inner ceiling) on the front/rear lips,
  four per Section. The stock length is derived from the 1.5 mm grip; the M2
  head (Ø3.80 × 2.00) cannot be recessed, so it spans 14.30–16.30 and **dips
  1.85 mm into the Tray**, 1.75 mm clear of the Tray's inner walls —
  `keyboard-mounts-head` reports it. `parting_z` (16.15) ≤ plate bottom (16.30)
  is HARD. Do not
  give the plate a zero-rotation frame: the pattern is read through the
  keyboard's 180° placement (`well_mounts(..., placement=...)`), from one
  `well_mounts` call for the Deck and the plate. Plate thickness or keycap
  height moves `plate_z`, the Well depth and the derived front margin.
- The keyboard is the tallest content along the face (32.30, keycaps flush with
  the Deck top): the plate's depth and the derived front margin set the travel.
  The RP2040 controller sits under the plate — the cavity there is clear
  end-to-end. The SBC sits in the Rear band behind the keyboard
  (`slide.rear_wall_margin: 8.0`, not 6.0, so it clears the new centreline band
  column at `(0, +65.5)` by 1.6 mm). Neither adds face height beyond the band.
  The USB hub is external (an accessory-rail module), not a chassis placement.
- **The Well/plate invariants are HARD checks** (`--steps data`): the ten
  `keyboard-*` checks — `keyboard-well-parting`, `-ring`, `-cutout`,
  `keyboard-plate-overhang`, `-border`, `-seam`, `-sections`,
  `keyboard-mounts-stations`, `-fit`, `-parting` (0 floor standoffs) — plus
  `slide-chassis-joint-clear`, which measures the joint stations against the
  plate's **notched** footprint rather than its bounding box, and the seven
  `slide-seam-*` checks (`offset`, `stagger`, `clear`, `interlock`, `stations`,
  `pin-fit`, `pin-clear`). The plate border
  is derived, not chosen (L/R 4.05, rear 4.85, spacebar 3.88 mm), and the
  `front-seam-right` station is walked 3.54 mm off the Seam by the front band
  column (`WellMount.adjustments`; do not "fix" it by moving the band joint).
  The at-Seam M2 stations' clearance is the named knob
  `keyboard.mounting.seam_slack: 4.0` (4.0 + ear 2.60 + min feature 0.60 = the
  pinned `seam_clearance` 7.20).
- **Only the lid's X side walls are drafted** (`draft.lid`, 5–10°): it widens
  from its face panel down to the back panel. The **Tray's X walls are
  vertical** (ADR-0019: the accessory rail bolts to a flat, square face), and
  so is the Deck, so the two halves are widest at the closed face and the Tray
  is one width from the table up. The front/rear end walls
  stay vertical too — drafting them would eat the rod end-clamp clearance inside
  the 140 mm guide span — and the Tray's end walls leave the table with a 15°
  base taper instead (`geometry/base_taper.py`). The slide budget adds the
  lid's `draft_allowance` to the side pod so the guide hardware keeps its shell
  clearance as the lid cavity narrows toward the face.
- The face is flat and the keyboard has no slope: do not add a
  `deck.slope`-style angle or a tilting mount. The slide is pure +Y
  translation.
- The lid's flat back slides over the keycaps: the Well sets that clearance.
  A keycap standing above the Deck is a collision over the whole travel.
- The guide rods sit on the lid back panel's inner face, inset `slide.rod.end_support`
  from each lid end; two printed Rod clamps hold each rod. The Bearing clamps
  straddle the panel through a long slot, seat in a pocket in the Deck, and
  slide along the slot. Neither the clamp nor the rod may protrude outside the
  closed envelope. The slot ends at the Rod clamps; the bearing stops
  `rod_clamp.clearance` short of each clamp at the extreme poses, so the panel
  under a clamp stays solid with a shallow rod groove for the clamp to pinch.
- The rod's usable span is `travel + bearing + 2 * (rod_clamp.length +
  rod_clamp.clearance)`; the rod is inset by one `end_support` from the chassis
  front. Do not re-derive the rod or the bearing-clamp centre from the chassis
  front independently: the bearing will run under an end clamp or off the rod.
- **Components must be centered on their origin in XY and run `[0, height]`
  in Z** (`Placement.box` / `z_bounds` assume it).
- A single bounding box per component only reports where it *isn't* solid as a
  coarse yes/no. Two examples that needed slicing: the keyboard's plate is
  sliced along its depth so a tilted volume isn't attributed to every position
  at once (see `_occupied_volume_slices`); `Battery` slices each cylinder
  along its round axis. The battery is external in the slider, but the model
  stays for the accessory pack.
- `layouts.resolvers.clearance.ClearanceResolver` is a true 3D
  separating-axis test. Calibrate placements against the resolver itself, not
  an independent approximation.
- The screen lid is the only moving part; its sweep must be checked over the
  whole travel (closed → open), not just at the end poses.
- The drag chain is a printed accessory whose channel and anchors are in the
  shell: keep the minimum bend radius and the channel clear over the travel.
- The battery and the USB hub are **external** on an accessory rail; do not
  grow the chassis envelope for them. The rail itself is printed (ADR-0020);
  its M4 stations, pads and washer pucks are part of the Tray.

## Docs

`CONTEXT.md` (domain glossary), `docs/form_factor.md` (agreed shape),
`docs/adr/` (decision records), `docs/reference/` (reference images),
`docs/central-unit-slider.md` (source reference measurements and the 140 mm
trim experiment).

`docs/design_spec.md` (conventions/philosophy), `docs/coordinate_system.md`,
`docs/component_spec.md` (datasheet-verified dimensions), `docs/cad_api.md`,
`docs/keyboard_architecture.md` (full keyboard subsystem spec).

## Tools

Use fff and codegraph MCPs for navigating the codebase.
Use ripgrep's `rg` instead of regular `grep`.

## Commits

When asked to commit, agents commit **without signing**: pass `--no-gpg-sign`
to `git commit`.

## Agent skills

### Issue tracker

GitHub Issues on `eduard-sukharev/terminal-deck`, via the `gh` CLI. See `docs/agents/issue-tracker.md`.

### Domain docs

Single-context: `CONTEXT.md` plus `docs/adr/` at the repo root. See `docs/agents/domain.md`.
