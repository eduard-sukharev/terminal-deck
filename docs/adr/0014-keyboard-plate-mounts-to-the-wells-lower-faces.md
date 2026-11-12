---
status: accepted
amends: ADR-0003
---

# The keyboard plate mounts to the Well's lower faces from below

ADR-0003 mounted the keyboard plate on eight M2 screws into Tray-floor
standoffs (four at the plate edges, two per Section near the Seam). Those are
16.3 mm-tall, ~Ø6 columns standing on the Tray floor, crossing the Parting
plane, and they are the plate's only support: the keycaps deflect a floating
plate over those points, and the plate is serviceable only by unscrewing under
the keys. The Well itself was a bare through-opening in the Deck's top plate,
sized by `clearance.shell`, with no walls.

We instead make the plate a flat sheet **wider than the Well Cutout**, screwed
flat against the **lower faces of the Well walls** from below. The Well walls (a
2 mm ring around the Cutout, owned by the Deck) descend to the plate and are its
continuous bearing; the plate carries the typing load by its own stiffness on
the fastening bosses. No floor standoffs remain, so the cavity under the plate
(the RP2040 controller) is clear end-to-end and nothing but the joint screws
crosses the Parting plane.

## Decision

- **Well.** The Deck carries a walled recess: a 2 mm-thick ring of walls around
  a rectangular Cutout, descending from the Deck's top face down to the plate.
  Its depth is **slaved to the plate's Z**, which is itself slaved to the
  tallest keycap:
  `plate_z = chassis_top − tallest_keycap − CAP_PLATE_GAP − plate_thickness`.
  The Well always reaches the plate; the Parting plane never cuts it
  (`parting_z ≤ plate_bottom` is a HARD check).
- **Cutout.** The opening is sized **by the keycap footprint plus a wobble
  allowance** (`wobble = 0.6 mm`), so a keycap rocking under switch play
  (0.5–0.7 mm) never strikes a wall. It is **not** sized by the plate, and
  `clearance.shell` no longer enters its size.
- **Plate.** A flat sheet, `plate = cutout + 2·wall` wide, so it extends one
  wall thickness under each Well wall and bears on the walls' lower faces. The
  switch-free border is derived, not chosen:
  `edge_margin = wall + wobble + (keycap/2 − cutout/2) ≈ 4.85 mm` (was 2.5 mm).
- **Fasteners.** Eight M2 screws, bottom-up, into heat-set inserts in bosses
  merged to the Well walls **on the front and rear lips only** — the X sides
  have ~2 mm of deck rim, nowhere near the ~6.5 mm an M2 boss needs. Four
  bosses per plate Section: front-outer, front-at-Seam, rear-at-Seam,
  rear-outer. Rectangular, filleted **ears** extend the plate past the Cutout
  where the edge border cannot hold a boss. Each screw passes through a
  clearance hole in the plate/ear and threads into the boss above.
- **Assembly.** The plate is screwed to the Deck **before** the Tray/Deck join
  and stays captive after. Servicing the plate or controller means splitting the
  Tray/Deck joint.

## Consequences

- `edge_margin` 2.5 → ≈4.85 grows the plate ≈4.7 mm across, so the keyboard
  (≈234.9 mm) overtakes the display (231 mm) as the width driver and the closed
  case grows **238.9 → ≈242.8 mm**. Each Section is ≈121.4 × 139.25 mm, still
  inside 220 × 220 × 256. The side bezel grows ≈2 mm per side — part of what
  ADR-0013 bought back. Along Y the growth is absorbed by the front margin
  (10 → ≈7.6 mm) and the Rear band (49.5 → ≈47 mm); face height is unchanged.
- The plate Seam follows ADR-0003's original intent — a split **between keys** —
  via `plate_seam()` (the row-jogging path), not the straight `x=0` cut that
  passes through switch cutouts (tracked as a bug, not a decision). The
  Tray-floor Seam standoffs disappear; each Section is held by its four bosses
  and the Well walls' bearing between them. The Seam is now clamped at its two
  ends (front/rear Seam bosses) rather than along its length.
- The cavity under the plate is clear end-to-end — no columns cross the
  Parting plane, and the controller sits free on the floor.
- `build_deck` re-derives the Cutout and walls from the keycap footprint +
  wobble, instead of `keyboard_w + 2·clearance.shell`.

## Considered alternatives

- **A below-plate ledge** (plate rests on a shelf under its edge): rejected —
  the shelf needs 2–3 mm of material below the plate, which pushes the Parting
  plane down and re-derives the whole band joint, for no gain over the plate
  spanning the walls' own lower faces.
- **Bosses on the X sides too** (a full-perimeter pattern): rejected — the case
  is only ~2 mm beside the plate there; an M2 insert boss needs ≈6.5 mm of
  radial room, which only the front/rear lips have.
- **Widening the case to host perimeter bosses:** rejected — it re-opens the
  width ADR-0013 just closed.
- **Floor standoffs (status quo):** rejected — 16 mm thin columns crossing the
  joint, point-loading the plate, weak under screw torque; the wall bosses are
  merged into a continuous 2 mm wall instead.

## Open measurements

- `wobble` (0.6 mm) is assumed from switch play; confirm on the assembled plate.
- The front lip (≈7.6 mm) hosting a Ø6.5 boss: verify it keeps ≥ `boss_margin`
  of material beside the boss.
