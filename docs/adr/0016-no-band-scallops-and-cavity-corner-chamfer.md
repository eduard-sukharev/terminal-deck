---
status: accepted
amends: ADR-0003, ADR-0012
---

# No band scallops, and the cavity corners follow the outer chamfer

ADR-0012 gave every band station a 10 × 0.8 mm **scallop** on each half, described
as "a relief line round the joint, not a structural feature". On the built shell
that relief is a row of shallow rectangular dents on the outside of the case at
every one of the twelve screws. It holds nothing, hides nothing, and the rest of
the skin is plain: the band should be one straight line, not a dotted one.

The same build turned up a real defect at the four outside corners. The shells
chop their vertical corners (`corners.chamfer`, 4 mm, chamfer-first) while the
cavity behind them was cut with **square** corners. With a 2 mm wall the square
cavity corner sits

```
(2 * wall - chamfer) / sqrt(2) = (4 - 4) / 1.414 = 0 mm
```

from the outer chamfer plane — the cavity corner and the chop meet exactly. The
Tray, the Deck and the Bezel therefore print a **knife edge** at each corner; at
a corner station the scallop cut through that sliver and left an open hole.

## Decision

- **The scallops are gone.** The cuts, the `chassis_joint.scallop_*` config, the
  scallop fields on `geometry.chassis_joint.ChassisJoint` and
  `utilities.config_loader.ChassisJoint`, the build's cutter and the
  `slide-chassis-joint-scallop` check are removed. The outer skin of the band is
  flush the whole way round, on both halves.
- **The cavity's corners carry the derived inner chamfer.** A shell that chops
  its outside corners chops the cavity behind them by

  ```
  inner_corner_chamfer(chamfer, wall) = max(0, chamfer - wall * (2 - sqrt(2)))
  ```

  (`utilities/cad_helpers.py`). The inner chamfer plane then lies exactly one
  `wall` behind the outer one: for the shipped `chamfer 4.0` on `wall 2.0` the
  cavity is chopped `2.83 mm` and the corner is a uniform **2.00 mm** wall. When
  the chop is small enough that a square corner already stands a wall off it
  (`chamfer <= wall * (2 - sqrt(2))` = 1.17 mm here), the helper returns 0 and
  the cavity stays square. The Tray, the Deck and the Bezel all build their
  cavities through it.

The formula: the outer chop line in plan is `x + y = hx + hy - chamfer`; the
cavity's corner line is `x + y = hx + hy - 2 * wall - inner`; their perpendicular
separation is `(2 * wall + inner - chamfer) / sqrt(2)`, which is set to `wall`
to solve for `inner`.

## Consequences

- The twelve rectangular dents are gone; the band reads as one plain surface and
  the countersunk Tray/Deck pair reads as a single seam line.
- Every outside corner of every shell keeps a full wall. There is no knife edge
  and no hole at the corners, and the Tray's corner columns stay merged into the
  corner wall as before.
- The cavity loses a `2.83 mm` sliver at each corner (a 2 mm wall's worth). No
  placed component reaches it: the keyboard plate's rear corners are more than
  5 mm inboard of the inner chamfer face, and nothing else is near a corner.
- The `slide-chassis-joint` family is **eight** HARD checks, not nine.
- Tests: the band is asserted flush at every non-corner station of both halves,
  and the Tray, the Deck and the Bezel are each asserted to hold material behind
  all four chops (`tests/test_chassis_joint.py`,
  `tests/test_slider_case.py`).
