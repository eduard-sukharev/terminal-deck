---
status: accepted
amends: ADR-0009, ADR-0010, ADR-0011, ADR-0012
amended_by: ADR-0014
---

# The guide rods move under the display, guarded by a printed FPC plate

ADR-0010 put the guide rods on the lid's back panel **beside** the display, and
ADR-0011 bought the room for them by widening the lid with
`slide.joint.corner_post`. Both are correct for the mechanism and wrong for the
device: the two side pods (guide hardware + wall + draft + corner post) set the
case **292.39 mm** wide for a **231 mm** panel, i.e. 33.7 mm of dead bezel on
each side of the glass. The width is carried by printed wall and hardware
envelope, not by anything the user sees or touches, on a device that is already
139.25 mm tall.

The rods also have to clear the display's ribbon (FPC), which runs from the
panel's east short edge to the HDMI driver behind the panel. That ribbon hung in
a 5.0 mm cavity with a 6.0 mm `display.flex.fold` allowance and no check owned
it.

## Decision

Both rods, their Rod clamps and the moving Bearing-clamp heads move **inboard,
under the display**, and the panel gets a printed grille plate where the head
sweeps the ribbon.

- Width **292.39 → 238.92 mm** (−18.3 %), side bezel to glass **33.7 → 6.96 mm**.
- Face height **139.25 mm unchanged**: travel, guide span, the 140 mm HARD
  limit, the stops and the open pose are untouched.
- Thickness **50.15 → 57.75 mm** (lid **16.85 → 24.45 mm**), because the moving
  head now has to pass under the panel, and the panel carries the guard.
- `rod_x` **125.25 → 93.86 mm**; the rails are 187.7 mm apart instead of 250.5.

**Amended by ADR-0014.** The keyboard plate grew to bear on the Well ring
(230.15 → 233.25 wide) and overtook the panel as the width driver: the shipped
width is **241.17 mm**, `rod_x` is **±94.98** (bounds post 99.68, seat 97.48,
head 107.50), the derived front margin is 7.65 mm and the closed face is
**140.00 mm** (the 140 limit). The side pod (3.96 mm) and the lid thickness
(57.75) stand.

### The stance is derived from three bounds, not chosen

`rod_x` must satisfy, simultaneously:

| bound | expression | value |
|---|---|---|
| lid band corner post | `W/2 − wall − rod_clamp.width/2 − corner_clearance − (insert_hole + 2·boss_margin)` | 98.56 |
| Deck seat vs chassis band corner boss | `W/2 − station_inset − boss/2 − minimum_feature − seat_width/2` | 96.36 |
| head under the display | `display.width/2 − clamp_width/2` | 107.50 |

`rod_x = min(bounds) − slide.rod.side_margin` (2.5 mm) = **93.86**. The seat
bound is the tightest; it is a plan-space proxy for a pair that is Z-separated
(the seat sits on the Deck top at 26.3, the band boss tops out at 21.65), so the
margin is deliberate rather than earned by that bound. The three bounds are
exposed on `SlideBudget.rod_x_bounds` and a HARD check asserts the stance stays
inside all of them.

### The width includes the draft, so it is 238.92, not 235.70

The first estimate (`wall + shell` per side → 235.70) is unbuildable. The lid's
X side walls are drafted (7°), and the cavity narrows from `band_z1` toward the
face panel, so a 231 mm panel in a 235.7 mm case collides with the tapered wall
about 1.5 mm in. The side pod is therefore

```
side_pod = wall + clearance.shell + draft_inset(draft_angle,
                    min(display_back + display.height, lid_thickness − lid_front) − band)
         = 2.0 + 0.35 + 1.61 = 3.96 mm
width    = max(keyboard.width, display.width) + 2 · side_pod = 238.92 mm
```

`usable_half` stays the content's half-width (115.50), so the layout-width and
clamp-corridor checks keep their meaning.

### The lid thickness follows the head, the guard and the sag

```
head_crown      = rod_raise + clamp_width/2                        = 9.00
display_cavity  = head_crown + component_gap + sag_allowance + guard.total
                                                                   = 12.60
lid_thickness   = lid_back + display_cavity + display.height
                  + lid_front + shell − bezel.recess               = 24.45
thickness       = chassis_top + lid_clearance + lid_thickness      = 57.75
```

The driver (4.6 tall, 0.4 gap to the panel) floats in that cavity; the display's
back is carried 12.6 mm above the panel's inner face. `display.flex.fold` is
retired: the ribbon no longer loops behind the panel, it is taped flat.

### The corner post flips inboard

`slide.joint.corner_post` is gone. The post is now whatever is left between the
Rod clamp's outer edge and the cavity wall:

```
post_inner = rod_x + rod_clamp.width/2 + corner_clearance   (105.36)
post_outer = width/2 − wall                                 (117.46)
width      = 12.10  ≥ insert hole 4.40 + 2 · boss_margin 1.50
```

Nothing widens the case for the joint any more, and the eight stations keep
their derivation from the lid plan.

### The FPC guard

The head sweeps the back-panel slot **under the glass**, and the panel's ribbon
crosses exactly that sweep. The display's back therefore gets a printed plate:

- **1.6 mm total** = 1.0 mm grille floor + 0.6 mm channel, `fpc_guard.recess`
  (`display.flex.stack`, `TODO: measure`, 0.6 assumed) recessed from the
  display-facing side and open at both ends so the ribbon can leave toward the
  driver.
- Planform from the driver's FPC connector to the head's sweep plus
  `fpc_guard.margin` (5.0), over the ribbon width plus the same margin:
  x 18.4…107.11, y ±24.25 in the display's frame (88.7 × 48.5 mm). It stops
  inside the display's shadow, which is where the head can reach; the east end
  of the ribbon is out of the head's reach and stays unmounted.
- Blind grille slots (2.0 max wide, 0.4 deep, 3.2 pitch) on the underside, so
  the plate stays compliant and light while spreading a point load over the
  ribbon; `minimum_feature` of material remains under the channel.
- Tape-bonded to the panel's back, so it peels off for service and the panel is
  never re-bought. It is a separate printed target (`fpc_guard`) with its own
  colour.
- The head's crown clears the plate's underside by `component_gap` (1.5) plus a
  documented `sag_allowance` (0.5, `TODO: measure` by a load test on the
  assembled lid): a creeping clamp can only ever reach the sacrificial plate.

### The chassis band joint had to move inside the same design

A 238.92 mm case is only 4.39 mm wider than the 230.15 mm keyboard, so there is
no band beside the keys: a 10 mm M3 insert boss cannot sit between the X wall
and the plate, and a Tray column at mid-side would run through the keyboard. The
joint keeps its ten stations, M3 × 18, boss arithmetic, scallops and
`parting_z`, but:

- the corner and long-wall stations sit `side_inset` (4.5) from the vertical
  walls, which caps those bosses at **7.80** (the long sides were already
  capped there);
- the two short-side stations moved from mid-side to the middle of the free
  band **behind the keyboard** (y 43.875), the only stretch of the X wall with
  room for an insert. They no longer mirror about the Y centreplane; the four
  corners and four long-wall stations still do.

The tightest floor-skin margin is the front corner: `base_distance 3.81 −
countersink 3.10 = 0.71 mm` (≥ `minimum_feature` 0.6).

## Consequences

- The case no longer has side pods: the picatinny nut pockets cannot live in a
  ~2.4 mm side wall. The rail interface is **lost** with this change and its
  relocation (base or a local boss) is tracked separately. The battery stays an
  external accessory; neither is grown back into the envelope.
- The 37.4 mm strips above and below the display stay free for the future aux
  buttons, and the 24.45 mm lid finally gives them depth. Their cut-outs, caps
  and wiring are out of scope here.
- The lid is deeper than the chassis needs, but the closed face is still pinned
  by the guide span (ADR-0009): the chassis grows to the lid, and the added rear
  band is empty behind the bearing-clamp seat.
- Sections are now **119.5 × 139.25** (Tray/Deck 16.15 tall, lid 24.45 tall) —
  comfortably inside 220 × 220 × 256, and the Seam does not cross the new
  inboard seats.
- New HARD checks: the guard stack (floor + channel vs the ribbon), the guard's
  coverage of the ribbon and the slot band, the Deck seat against the chassis
  band corner boss, the corner post measured inboard of the Rod clamp, and the
  display clearance as a **Z** stack against the guard's underside (the old
  X-only check is gone). `slide-clamp-clear` now uses the moving head's real
  corridor (`rod_x − hardware_width/2`).
- Retired terms: `slide.joint.corner_post`, `display.flex.fold` as a
  parameter. New terms: **FPC guard**, **guard channel**.

## Considered alternatives

- **A thinner clamp wall** (1.0 mm → Ø14 head, −1.0 mm thickness): a 1 mm
  printed ring around a 12 mm bearing is the wear part that decides the
  thickness; rejected as too weak after the move, where the head is buried.
- **Sinking the rods into a thicker back panel**: each millimetre buys 0.5 mm of
  cavity and costs 1 mm of lid; the 2.0 mm wall plus the guard was cheaper.
- **A flat MGN7 linear rail**: thinner and flatter, but a different purchased
  part, a new alignment problem and a new ADR. Rejected for now; the thickness
  is acceptable at 57.75.
- **Tape-only ribbon retention** (no plate): rejected after review — the ribbon
  is the one part a deflecting head must not touch, and tape gives no gap.
- **Dropping `usable_half` to the keyboard and keeping a wider case** for the
  band: that is the current design; it costs ~17 mm of width to keep the joint
  unchanged, which is the trade this ADR rejects.

## Open measurements

- `display.flex.stack` (0.6): the flat ribbon with its stiffener and coverlay.
- `fpc_guard.sag_allowance` (0.5): a load test on the assembled lid, recorded in
  config. Both keep `TODO: measure` until measured.
