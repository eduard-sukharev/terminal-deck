# Split every wide part into left/right Halves with stepped Seams

The 8.8" panel (231 mm module) makes the Envelope ~236 × 118 mm, which does not
fit the 220 × 220 × 256 mm build volume in any viable orientation (not even
diagonally). Every wide part — Tray, Deck, keyboard plate, Lid shell, Bezel —
is therefore printed as two Halves split along X and joined by screws and
bosses. Seams are staggered between parts so they never line up, and every
outward-facing Seam is a stepped line in plan view (`__--__--__`) with plain
butt-joint step faces.

## Considered Options

- Print standing on end (236 mm < 256 mm Z): rejected — unsupported tray
  floors, warping.
- Straight butt Seam at one shared X=0 plane: rejected — aligned seams make a
  single weak hinge line through the closed device.
