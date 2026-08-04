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

A `Placement` carries `(x, y, rotation, z)` in the world frame:

* `x`, `y` — component origin position.
* `rotation` — rotation about +Z in degrees; 0 = component +Y aligned with
  world +Y.
* `z` — stacking height; assigned by the assembly stage when left 0.

## Units

All dimensions are millimeters, always. Never inches.
