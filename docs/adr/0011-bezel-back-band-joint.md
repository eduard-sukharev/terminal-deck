---
status: accepted
amends: ADR-0010
amended_by: ADR-0013, ADR-0014
---

# The screen lid splits into a Bezel and a Back plate, joined by a prismatic band

ADR-0010 put the guide rods, the slots and the Bearing clamps on the lid's flat
back panel, but left the lid as one printed inverted tray. That tray cannot be
printed in its intended orientation at 220 mm bed width without splitting both
the cavity and the panel it needs to stay stiff, and it cannot be serviced: the
display and the driver are trapped behind the glass opening.

The reference device (`docs/reference/MDU-12-*`, `cornenr.png`) splits its lid
the other way: a **face panel** (the Bezel) that carries the display, screwed to
a **separate backplate** with corner cut-outs that reach around the face's
taper. The project adopts that arrangement, with two refinements:

- The split plane is the Back plate's **inner face** (`panel_inner_z`), not the
  outer one. The Back stays the thin flat plate the guide hardware is designed
  against (ADR-0010), and the whole 6 mm fastening band lives in the Bezel where
  there is already material.
- The band is **prismatic**, not tapered. The lid's X side walls only start
  their draft above `band_z1`; below it the Bezel band and the Back plate are
  both built at `frame.width`, so the joint face is a clean butt joint in
  straight walls, exactly like the chassis Tray/Deck split (ADR-0003).

The face of the lid therefore reads like the reference: prismatic at the back,
tapered at the front.

## The eight stations

Two stations per long side (**front** and **rear**) plus **four corners**, all
countersunk from the Back's outer face into a heat-set insert in the Bezel's
band:

- **M3 countersunk**, Ø6.2 × 1.5 sink in the 4 mm Back plate, so the grip is
  `lid_back - csk.depth = 2.5` mm; `deck_screw` picks **M3 × 6**, which engages
  3.5 mm of the 4.0 mm insert and cannot bottom out.
- The insert hole is Ø4.4 (M3 heat-set, printed hole) × 4.0 deep, cut from the
  band's underside; the band is 6.0 mm so 2 mm of material stays behind it.
  The band is solid all round (no vents; vents remain deferred).
- Long-side stations sit at `x = ±width/6` on square **band pads** that merge
  into the perimeter wall. They carry no extra material into the cavity.
- Corner stations sit at `x = ±(width/2 - (insert/2 + boss_margin))`,
  `y = ±(lid_height/2 - station_inset)`.

The corners are why the case grew. Inside the lid, the four Rod clamps occupy
the corners of the Back plate; the free Y beyond each clamp is only 3.0 mm
(front) and 5.5 mm (rear). No Ø4.4 insert with a usable margin fits there, and
moving the clamps would break the rod span ADR-0010 fixed. So the lid grew
**outboard instead**: `slide.joint.corner_post` widened the side pod by
8.75 mm per side, which turned each corner into a post between the Rod clamp's
edge and the side wall, with `corner_clearance` (0.5 mm) to the clamp.

**Revised by ADR-0013.** The rods moved under the display, so the corner post
now sits **inboard of the cavity wall** and follows the clamp instead of
widening the case: `post_inner = rod_x + rod_clamp.width/2 + corner_clearance`
(105.36), `post_outer = width/2 − wall` (117.46), post width **12.10 mm** —
enough for the Ø4.4 insert plus the 1.5 mm boss margin. `slide.joint.corner_post`
is retired; the eight stations keep their derivation from the lid plan, and the
width is 238.92 mm. The station-clearance check now measures the post inboard of
the clamp. **Amended by ADR-0014:** the keyboard plate is the width driver, so
the shipped width is 241.17 mm, `rod_x` is ±94.98 and the corner post spans
106.48–118.58 mm.

## Consequences

- The lid was **16.85 mm** thick (now 24.45 with ADR-0013, which puts the
  moving head and the FPC guard under the panel). The earlier assumption that the
  lid's thickness was set by the Rod clamp was wrong: it is set by the
  display (6.5) + driver (4.6) stack. Three changes buy the 1.45 mm:
  the spurious second `clearance.shell` on the front panel (−0.35),
  `slide.driver_gap` 0.5 → 0.4 (−0.10), and a new `bezel.recess` pocket in the
  front panel's inner face (−1.00), which lets the display frame sink 1 mm into
  the panel while a 1.0 mm lip (≥ `material.minimum_feature`) still retains it.
  Device thickness 51.60 → **50.15 mm**, now **57.75 mm** after ADR-0013.
- The joint is a **plain butt** at `panel_inner_z`: eight screws locate it and
  the perimeter walls carry the load. There is no lap or tongue to print, and
  no undercut on either part. Both parts are flat-sliceable; `sections()` still
  splits each at x = 0.
- The Back is removable, so the display, the driver, the rods and the Bearing
  clamps are serviceable from the keyboard side without breaking the glass
  bond. The rods and Rod clamps mount to the Back, so the guide hardware comes
  out as one unit.
- `screen_lid_bezel` and `screen_lid_back` are separate build targets (each
  with `_left` / `_right` Sections); `screen_lid` stays the assembled compound
  the assembly and the opened pose use. The glTF render gives them their own
  colours.
- New HARD checks in `run_slider_checks` (`slide-lid-joint-*`) assert the band
  holds the insert, the corner post holds the insert, a stock screw exists and
  does not bottom out, the bezel recess leaves a printable lip, and every
  station clears the Rod clamps.
- `slide.rod_raise` is now derived (`rod.diameter/2 - lid_back/2`) rather than
  configured: the rod's lowest point always sits at the Back's mid-thickness,
  which is what keeps the inverted tray's cavity deep enough after the split.
- ADR-0010's width estimate (≈ 283 mm) and thickness (51.6 mm) are superseded
  by these numbers; its mechanism, slot and clamp decisions stand.
