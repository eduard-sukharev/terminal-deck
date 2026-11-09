# Coordinate System

This document defines the single coordinate convention used everywhere in the
slider generator. Never redefine origins.

## Convention

| Axis | Direction |
|------|-----------|
| +X   | right |
| +Y   | along the slide, from the keyboard end toward the screen end |
| +Z   | upward (normal to the face; thickness) |

* The device is modelled **face-up**, lying on its back: the keyboard and the
  screen face +Z, and +Z is the thickness.
* Origin: **center of the chassis footprint**, on the table plane (the
  chassis's outer back, Z = 0).
* The user sits at **−Y** (the keyboard end). **+Y is the direction the screen
  lid opens** (away from the user). "Front edge" means the keyboard edge
  (−Y); "rear edge" means the screen edge (+Y).
* The screen lid sits above the chassis and slides along +Y; it is the only
  moving part.

The old clamshell convention (+Y forward, +Z up with the device closed like a
book, a hinge at −Y) is retired with the clamshell (ADR-0009).

## Degrees of freedom

The face is flat — there is no deck slope. The only motion in the assembly is
the screen lid's translation along **+Y** over the Slide travel. The
kinematic checks (closed cover, sweep, guide span, chain path) all run along
that axis.

## Component frame

Every component has its own local frame whose origin is the component's
reference origin:

* Default: center of the component's measured bounding box.
* Overridden (e.g. HDMI driver board) via `reference_origin()` to express a
  deliberate offset from the display center.

Component-local coordinates (mounting holes, connectors) are always relative
to the component origin, never the world origin.

Components are centred on their origin in X and Y and run `[0, height]` in Z;
`Placement.box` / `z_bounds` rely on that.

## Placement

A `Placement` carries `(x, y, rotation, z, flip_x, tilt_x)` in the world
frame:

* `x`, `y` — component origin position.
* `rotation` — rotation about +Z in degrees; 0 = component +Y aligned with
  world +Y.
* `z` — stacking height; assigned by the assembly stage when left 0.
* `flip_x` — the fixed 180° turn-over about X, for boards mounted face-down
  against another part. A flipped component occupies `[z - height, z]`.
* `tilt_x` — a wedge angle about X, in degrees. The slider's deck is flat, so
  this is 0 for every placed part in the default layout; the field stays for
  unusual placements and for the display, if it is ever mounted at an angle.

The transforms compose in that order — Z rotation, then flip, then tilt —
in both `Placement.world_offset` and `Assembly.build_subset`, so the data
layer and the generated solids agree.

A `rotation` swaps which component dimension faces which world axis. Anything
comparing boxes in world space must go through `layouts.base.volume_extents`
(or `Placement.box` / `z_bounds`) rather than reading a raw component `size()`.

## Units

All dimensions are millimeters, always. Never inches.
