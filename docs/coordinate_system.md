# Coordinate System

This document defines the single coordinate convention used everywhere in the
cyberdeck generator. Never redefine origins.

## Convention

| Axis | Direction |
|------|-----------|
| +X   | right     |
| +Y   | forward   |
| +Z   | upward    |

* Origin: **center of the base**.
* +Y forward means "toward the user / away from the hinge" in the closed
  position.
* The hinge runs along the +X axis at the rear (-Y edge).

## Component frame

Every component has its own local frame whose origin is the component's
reference origin:

* Default: center of the component's measured bounding box (center of base).
* Overridden (e.g. HDMI driver board) via `reference_origin()` to express a
  deliberate offset from the display center.

Component-local coordinates (mounting holes, connectors) are always relative
to the component origin, never the world origin.

## Placement

A `Placement` carries `(x, y, rotation, z, flip_x, tilt_x)` in the world
frame:

* `x`, `y` — component origin position.
* `rotation` — rotation about +Z in degrees; 0 = component +Y aligned with
  world +Y.
* `z` — stacking height; assigned by the assembly stage when left 0.
* `flip_x` — the fixed 180° turn-over about X, for boards mounted face-down
  against another part. A flipped component occupies `[z - height, z]`.
* `tilt_x` — the wedge angle about X, in degrees, for parts riding the sloped
  base deck. Negative raises the rear (-Y), matching `Base.deck_level_at`.

The transforms compose in that order — Z rotation, then flip, then tilt —
in both `Placement.world_offset` and `Assembly.build_subset`, so the data
layer and the generated solids agree.

A `rotation` swaps which component dimension faces which world axis; a
`tilt_x` mixes depth and height into each other. Anything comparing boxes in
world space must go through `layouts.base.volume_extents` (or `Placement.box`
/ `z_bounds`) rather than reading a raw component `size()`.

## The sloped deck

The base top deck is a wedge, set by `config.deck.slope` (degrees): flat
along the front edge, rising toward the rear so the keyboard gets a typing
tilt and the rear interior opens up for the SBC and battery cells.
`case.base.Base.deck_level_at(y)` is the single source of that plane — the
tray rim, corner standoffs, deck slab, and keyboard mount all derive from it.
A slope of `0` reproduces the original flat geometry exactly.

## Units

All dimensions are millimeters, always. Never inches.
