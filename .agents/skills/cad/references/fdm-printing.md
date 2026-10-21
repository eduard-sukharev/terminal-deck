# FDM 3D printing: design rules and limitations

Read this file whenever the modeled part is destined for FDM (fused
deposition modeling) 3D printing — the user says "3D print", "STL", names a
printer (Bambu, Prusa, Ender, etc.), or the part is a bracket, enclosure,
mount, jig, or other functional object with no other stated manufacturing
process. Apply these as manufacturability defaults on top of the general
`Default assumptions` in `SKILL.md`; state which ones you assumed in the
final report.

These are FDM-specific limits, not general CAD defaults — do not apply them
to parts destined for CNC, injection molding, SLA/resin, or SLS unless the
user says the part is still going through an FDM printer.

## Minimums and recommendations

Defaults for a 0.4 mm nozzle. Ask (or state the assumption) when a different
nozzle diameter changes these — minimum wall and feature size scale
roughly with nozzle diameter (2 perimeters at that width), not with layer
height.

| Property | Minimum | Recommended |
|---|---|---|
| Wall thickness | 1.2 mm | 2.0-3.0 mm |
| Hole clearance (loose fit, e.g. shaft through hole) | 0.2 mm/side | 0.3 mm/side |
| Press-fit interference | 0.1 mm/side | 0.15 mm/side |
| Min feature size (boss, rib, tooth) | 0.4 mm (one nozzle width) | 0.8 mm |
| Fillet radius that avoids supports on a bottom edge | 0.5 mm | 1.0 mm |
| Unsupported bridge span | — | < 20 mm |
| Max overhang from vertical before supports are needed | — | < 45° |
| Layer height | 0.08 mm | 0.2 mm |

These are starting points, not certified tolerances — treat holes and
press-fits as first-pass values to confirm on the user's printer, and say so
in the final report rather than presenting them as guaranteed fits.

## Build volume

The printer's build volume (bed size and max Z height) is a hard constraint,
not a style preference — a part that doesn't fit does not print, regardless
of how well it satisfies every other rule in this file. Treat it as a
required input, not an assumption to skip past:

- **Look for a declared build volume before modeling anything sized close to
  it.** Check the project's config/CLAUDE.md/README for a stated printer
  model or bed dimensions (X × Y × Z) first. If this project targets FDM
  printing as an explicit goal (not a one-off part) and no build volume is
  declared anywhere, that is itself a gap worth flagging to the user or
  recording in the project's config alongside other machine parameters
  (nozzle diameter, material) — do not silently re-guess it on every part.
- **If nothing is declared and the user hasn't named a printer**, ask once
  (bed size is fit-critical, per the clarification policy in `SKILL.md`) or
  state a conservative assumption and flag it prominently — do not assume a
  large-format printer by default. Common reference envelopes if you must
  assume: Bambu Lab X1C/P1S ~256 × 256 × 256 mm, Prusa MK4 ~250 × 210 ×
  220 mm, Ender 3 (stock) ~220 × 220 × 250 mm. State which one you assumed.
- **Check the bounding box per printable orientation, not just as
  modeled.** A part that exceeds the bed in its "natural" orientation may
  fit diagonally or on a different face; conversely a part that fits the
  raw bounding box may not fit *in the orientation the overhang/bridging
  rules above require*. Validate the combination — orientation choice has
  to satisfy build volume and overhang/bridging/bed-adhesion rules
  together, not evaluate each in isolation.
- **When a part exceeds the build volume in every viable orientation, split
  it into multiple printable pieces** rather than silently shrinking it or
  ignoring the limit. Design the split with the same care as any other
  mating interface: alignment pins/sockets or a dovetail across the seam,
  and either screw bosses (chamfered, per Boss design below) or a glued
  step/rabbet joint sized for the material's shrinkage. Record the split
  and its joint method in the brief and the final report; each piece still
  goes through its own printability self-check below.
- For an assembly with several components, check each printable part
  against the build volume individually — an assembly's overall envelope
  exceeding the bed is expected and not itself a problem as long as every
  part that gets printed on its own fits.

## Material-specific adjustments

State the assumed material in the brief when the user hasn't named one
(default PLA). Adjust the table above per material:

- **TPU / other flexibles**: clearances ~0.5 mm/side — flex absorbs a tight
  fit and a nominal clearance binds.
- **PETG**: stickier than PLA in the nozzle and to itself; add +0.1 mm to
  fit clearances, especially press-fits and snap-fits.
- **ABS / ASA**: shrinks ~0.5-0.7% while cooling; scale critical/mating
  dimensions up slightly on parts with tight tolerances, and prefer ASA over
  ABS outdoors (UV resistance).
- **Nylon**: absorbs moisture and swells; oversize clearance holes slightly
  versus the PLA baseline if the part will see humidity.
- Recommend PETG or ABS/ASA over PLA for load-bearing, outdoor, or
  hot-environment parts (see Print Recommendations below); call out that no
  common FDM material is inherently food-safe.

## Orientation and overhangs

- Design toward a flat printable face; a part with no natural flat face
  needs an explicit statement of the intended print orientation in the
  brief and in source comments.
- Keep overhangs under 45° from vertical where the design has freedom to
  choose the shape; where an overhang is functionally required, either
  redesign around it (chamfer instead of a sharp horizontal ledge, taper
  instead of a stepped shelf) or flag it in the final report as needing
  supports.
- **Bottom edges: chamfer, not fillet.** A fillet on an edge touching the
  print bed needs support material to print cleanly; a 45° chamfer on that
  same edge is self-supporting. Reserve fillets for edges away from the
  bed, or for radii below the ~0.5 mm minimum in the table, which print
  clean either way. (See `build123d-modeling.md` for fillet/chamfer build
  order and failure-mode handling — this file covers *when* to prefer one
  over the other for printability, that file covers *how* to apply it
  without breaking the boolean.)
- Bridges under ~20 mm print unsupported; longer unsupported spans need
  either a support strategy (tree supports, or splitting the part) or a
  redesign (add a mid-span rib, shorten the span, reorient the part).
- Screw bosses, standoffs, and ribs must be solidly connected to a wall or
  floor along their full contact face — a boss that only grazes the wall
  prints as a weak, easily-snapped joint even though the geometry validates
  as watertight.
- **Chamfer sharp right-angle transitions wherever geometry allows.** FDM
  parts fail along layer lines concentrated at sharp internal/external
  right angles (a boss-to-floor junction, a rib-to-wall junction, a
  bracket's inside corner) well before the bulk material would; a small
  chamfer (or fillet, away from bed-facing edges — see above) spreads that
  stress across a transition instead of concentrating it at one printed
  seam. Default to chamfering every functional right-angle junction that
  bears load or repeated handling, not just the outer cosmetic edges.

## Boss design

Bosses (screw bosses, standoffs, alignment posts) are a common FDM failure
point: a tall thin post glued to a floor by one small circular footprint
snaps off exactly there under load. Apply these rules, favoring the
strongest option the layout allows:

- **Widen the base.** Taper or step the boss so its footprint is larger
  than its screw-hole diameter alone — a boss that flares outward toward
  its base sheds load into the floor/wall over a larger printed area
  instead of concentrating it at the post's nominal diameter.
- **Add side fins when a wider base isn't enough**, or the boss is tall
  relative to its diameter. Fins (small triangular or trapezoidal gussets)
  running from the boss to the adjacent floor/wall carry bending load in
  their own strong printed plane rather than relying on the boss's
  layer-line adhesion alone.
- **Merge a boss into a nearby wall instead of leaving it freestanding.**
  When a boss sits close enough to a wall that a freestanding post and the
  wall would nearly touch, extend the boss into the wall so they print as
  one continuous printed mass, and chamfer the transition where the merged
  boss meets the wall face. The same rule applies when a boss sits near an
  inner corner: merge it into the corner (touching both walls) rather than
  leaving it freestanding nearby, and chamfer the boss's transition into
  *both* walls of the corner.
- **Use a rounded-rectangle (squircle) profile, not a circular-post
  profile, for any boss that gets merged into a wall or corner.** A
  circular post merged into a flat wall or a corner leaves thin
  crescent-shaped slivers of material at the tangent points, which are
  themselves weak and prone to trapping stress; a rounded-rectangle profile
  (rectangle sized to reach the wall(s) cleanly, corners filleted to the
  same radius used elsewhere on the part) merges into a wall or corner as a
  single clean printed mass with no thin slivers. Keep the circular-post
  profile only for genuinely freestanding bosses with no nearby wall to
  merge into.
- The screw/insert bore itself stays circular regardless of the boss's
  outer profile — only the outer profile changes from circular to
  rounded-rectangle when merging.

## Fit and tolerance features

- Clearance and press-fit holes/pockets are diameter or gap allowances
  applied *in addition to* the nominal dimension of the mating part — do
  not fold them into the nominal dimension itself; keep them as a separate
  named parameter (e.g. `fit_clearance`) so they can be retuned per printer
  without touching the nominal geometry.
- Snap-fit cantilever clips: keep the hook overhang under the ~45° limit
  above, and give the flexing beam enough length/thickness ratio to survive
  repeated deflection without living-hinge-style fatigue (unless a living
  hinge is explicitly wanted, which needs a different, much thinner
  cross-section and usually a different material).
- Threaded-insert bosses (heat-set inserts) need a bore sized to the
  insert's datasheet, not the raw screw — do not approximate one from a
  clearance-hole table meant for a cut thread.
- When the part interfaces with a real physical object (an SBC, connector,
  another printed part, threaded insert, bearing), source exact dimensions
  before modeling — per `cad-brief.md`'s dimension-conflict guidance, a
  guessed dimension that's a millimeter off makes the fit fail outright,
  which is a worse failure than an ordinary geometry error.

## Print recommendations to include at delivery

When handing off a part or assembly intended for printing, include a short
(≈3 line) slicer recipe with the STEP/STL handoff — do not restate every
slicer setting; Bambu Studio/PrusaSlicer/OrcaSlicer already set sane
defaults from the material preset. State only what this part needs:
material, layer height, wall count, infill, supports, and orientation.

Baseline (0.4 mm nozzle): PLA, 0.2 mm layer, 2 walls, 15% gyroid infill, no
supports, flat face down.

Deviate when the part calls for it:

- Load-bearing brackets, hooks, hinges, clips: 25-40% infill, 3-4 walls;
  consider PETG over PLA.
- Thin decorative or non-structural shells: 0-1 wall, vase mode where
  applicable.
- Tall, narrow, or small-footprint parts: add a brim for bed adhesion.
- Geometry with unavoidable overhangs: call out that supports (tree
  supports preferred) are needed, and where.
- Outdoor or hot-environment parts: PETG or ASA, not PLA.
- Food- or skin-contact parts: state that FDM output is not food-safe as
  printed.

## Printability self-check before delivery

Before treating a print-destined part as done, in addition to the
snapshot/validation steps in `snapshot-review.md` and
`inspection-and-validation.md`, confirm:

- [ ] Every wall, boss, and rib meets the minimum in the table above (or a
      stated, deliberate exception).
- [ ] The part has a flat or explicitly-stated print orientation.
- [ ] Overhangs beyond 45° are either absent, redesigned around, or called
      out as needing supports.
- [ ] Fit-critical holes/gaps use a named clearance parameter, not a bare
      literal.
- [ ] Bottom-touching edges use chamfers, not fillets, unless the radius is
      small enough to be self-supporting.
- [ ] Functional right-angle junctions (boss/rib/bracket-corner to
      floor/wall) are chamfered, not left sharp.
- [ ] Bosses have a widened base or side fins rather than a thin freestanding
      post, unless deliberately freestanding and lightly loaded.
- [ ] Bosses close to a wall or inner corner are merged into it with
      chamfered transitions, and use a rounded-rectangle profile rather than
      a circular-post profile at the merge.
- [ ] Material assumption is stated (default PLA) and any material-specific
      clearance adjustment from the table above was applied.
- [ ] The part's bounding box in its intended print orientation fits the
      declared (or stated-assumption) build volume; if it doesn't in any
      viable orientation, it has been split into joined printable pieces.
