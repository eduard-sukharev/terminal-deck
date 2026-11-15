---
status: accepted
amends: ADR-0011, ADR-0012
---

# The Bezel's band posts are capped at 45°, not run up to the panel

The Bezel prints face down: its front panel is on the bed, and the band — the
last thing printed — is in the air at the top of the print. Its ten band posts
(the four corner posts and the six long-side pads) stop at `band_z1`, 12.45 mm
short of the front panel's inner face: that is where the insert and the joint
need material, and the rest is the display cavity. Printed face down, each
post's flat top is therefore the print's *first* layer at that height, hanging
off the wall it merges into with nothing underneath it — a 90° ledge,
**213.8 mm² at each corner post and 56.0 mm² at each pad**, which the slicer
reports as an overhang needing support.

ADR-0012 solved the same problem on the Deck by running every insert boss up to
the inner ceiling. Applying that here would add ≈ 15 cm³ and bury the 12.45 mm
of cavity under the display that the moving head and the FPC guard use.

## Decision

- Each post keeps its **full footprint over the 6 mm band** — the M3 insert
  (Ø4.4 × 4.2, cut from `band_z0`) stays buried in the same block of material —
  and is closed by a **45° support cap** (`cad_helpers.support_cap`). The cap
  stands on the post's top face and tapers away from every cavity-facing side
  until the taper runs out at the wall, so each printed layer is carried by the
  one above it and the ledge becomes a slope. The sides merged into the wall
  stay straight: the corner posts taper over their own 12.10 mm width (and the
  slope meets the tapered cavity wall before that), the pads over 4.00 mm and
  end on a ridge above the pad's middle.
- The cap is derived, never hand-sized: the helper takes the post's plan rect
  and which of its four sides are free, and its height is the offset at which
  the first taper runs out. `ScreenLid._band_post` is the one place a post is
  built, so the four corners and the six pads cannot drift apart.
- The rest of the Bezel is unchanged: `band_z0`/`band_z1`, the stations, the
  insert holes, the window, the pocket and the Seam all read as before.

## Consequences

- The Bezel has **no overhang face at all** in its print orientation. The whole
  lid was scanned with `geometry.printability.overhang_faces` (bed normal
  `(0, 0, 1)`); the ten ledges were the only faces it reported, and they are
  gone. That is asserted as a test (`tests/test_slider_case.py`) rather than a
  data-layer HARD check, because it needs the built solid.
- The added material is ≈ **4.2 cm³** over the whole Bezel (four corner caps at
  1.02 cm³, six pad caps at ≈ 0.09 cm³ once the part inside the wall is
  discounted) against ≈ 15 cm³ for full-height columns.
- The caps stay inside the free band: `|y| ≥ 50` for the corner posts and
  `|y| ≈ 61` for the pads, outboard of the display (±32.25), the FPC guard
  (±24.25) and the Rod clamps (`|x| ≤ 105.98`), so no placed component moves.
- The band's own solid, the `x = −14` Seam and the two Sections are untouched:
  no cap crosses the Seam.
- `ADR-0011`'s "the pads carry no extra material into the cavity" now holds
  below `band_z1` only; above it the cap is in the cavity by design.
