---
status: accepted
amends: ADR-0009
---

# Guide rods are clamped to the lid's back panel, with the bearing clamps straddling the panel

ADR-0009 specified the guide rods inside the screen lid's side walls, in a
C-channel, with the Bearing clamps rising from the chassis deck into that
channel. That first-generation shell put the rods in a pocket and left them
unheld; it also hid the whole mechanism inside the lid's solid side pod. The
form reference (`central-unit.step`, `render.png`) does it differently: the
rods sit on the lid's **flat back panel**, each held by two printed end clamps;
between the clamps the panel has a long through-slot, and the printed Bearing
clamp — body on the lid side, foot through the slot to the chassis — slides
along that slot.

The project adopts that arrangement. It is a better fit for the constraints:

- The back panel is the datum for the guide geometry. Two Rod clamps per rod
  can be printed and screwed into the panel without weakening a side wall into
  a C-channel.
- The Bearing clamp straddles the panel. Its head is a **cylinder at the neck
  width** (Ø16, no flange): the **rod passing through the bearing** is what
  retains the lid against lift-off. No separate retainer is needed.
- The clamp's foot seats in a pocket in the Chassis Deck, so the load path goes
  from the rod, through the bearing and clamp, straight into the deck.
- The lid's cavity opens to the side walls (no solid side pod). **Revised by
  ADR-0013:** the rods and clamps sit **under the display**, not beside it —
  the reference's side-by-side arrangement cost 33.7 mm of dead bezel per side.
  The mechanism, the slot and the clamp decisions below stand; only the stance
  moved (`rod_x` 125.25 → 93.86).

## Consequences

- The rods are inset by `slide.rod.end_support` from the lid's ends so the end
  walls stay solid. The rod's usable span is
  `travel + bearing + 2 * (Rod clamp + clearance)`: the bearing's travel
  envelope is flanked by the end clamps, so it never runs under them. The
  bearing clamp's centre shifts with the same allowance.
- The default bearing becomes the short **LM6UU (19 mm)** rather than the
  35 mm LM6LUU. The long bearing plus the end clamps would need a 154 mm lid;
  the short one leaves the closed face at **139.25 mm**, under the 140 mm
  limit. The bearing still spans the full travel; it is the same purchased
  part class (6 mm bore, 12 mm OD).
- The back-panel slot runs between the two Rod clamps. The bearing is 0.5 mm
  short of each clamp at the extreme poses, so the panel under a clamp is
  solid, with a shallow rod groove; the clamp pinches the rod into it.
- The Bearing clamp is a separate printed part in the `slide` target. It is
  installed before the lid's back panel; the back panel is the last part, so
  the rods can be slid through the bearing axially before the Rod clamps are
  tightened.
- The clamp's foot is longer than the bearing (30 mm vs 19 mm) and its two
  screws are 24 mm apart, outboard of the bearing's ends: a screw tip cannot
  reach the bore or the housing above it. The foot's top face is flush with
  the Deck top — the neck spans the back panel and the joint gap, and the
  foot sits wholly in the pocket. The foot's four vertical corners and the
  matching chassis pocket get a 5 mm 45-degree relief (they are what locates
  the clamp); the foot's top perimeter and the pocket mouth get a 0.5 mm
  relief. The head's circular rims stay as formed: an arc chamfer is fragile
  and a round rim is already print-friendly. The bore stays sharp — a chamfer
  there would relieve the bearing seat. **Amendment:** the cylindrical head
  replaced the earlier flanged body, so the guide hardware now needs only the
  slot width (16.5 mm) of display clearance, and the clamp no longer overhangs
  the back-panel slot. With that margin, the 8.75 mm corner posts and the
  draft allowance, the derived width was **292.4 mm** (side pod 30.7 mm), not
  the ≈ 283 quoted below. **Superseded by ADR-0013**: the stance moved under
  the display and the width is **238.92 mm** with no side pod and no corner
  post.
- Width grows from ≈ 267 to ≈ 283 mm (then to 292.4; ADR-0013 takes it to
  238.92): the side pod now clears the 22 mm Rod
  clamp and a 1.5 mm gap to the display. Thickness grows by 2 mm because the
  back panel is 4 mm thick, needed for the slot and the Rod-clamp inserts
  (51.6 mm). The chassis grows to the closed face (≈ 139 mm) so its rear wall
  ends flush with the closed lid; the added rear band sits behind the
  bearing-clamp seat (which ends ≈ 8 mm forward of the rear wall) and gives
  the drag chain its channel.
- `CONTEXT.md` and `docs/form_factor.md` use "Rod clamp" and "Clamp slot"; the
  old "C-channel" term is retired with the side-wall guide.
