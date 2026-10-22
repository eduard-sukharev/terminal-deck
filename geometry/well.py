"""Well: the rim around the keyboard opening in the Deck.

The keyboard sits in a recess bounded by a rim that stands proud of the Deck
but stays below the switch tops, so the keys are protected without adding
closed thickness.
"""

from __future__ import annotations


def rim_height(switch_top: float, deck_thickness: float, margin: float) -> float:
    """Rim height above the Deck top (mm), never reaching the switch tops.

    ``switch_top`` is measured from the plate top, which is also the Deck's
    underside; the rim top therefore sits ``switch_top - margin`` above that.
    """
    return max(0.0, switch_top - margin - deck_thickness)


def build_rim(inner_w: float, inner_d: float, width: float, height: float,
              overlap: float):
    """Rectangular ring (outer = inner + 2*width), bottom at z=0 and sunk
    ``overlap`` into the slab below so it fuses with the Deck."""
    from utilities import cad_helpers

    if height <= 0.0:
        return cad_helpers.empty_solid()
    total = height + overlap
    outer = cad_helpers.box_centered(inner_w + 2 * width, inner_d + 2 * width, total)
    inner = cad_helpers.box_centered(inner_w, inner_d, total + 2.0)
    ring = cad_helpers.cut(outer, inner)
    return cad_helpers.translate(ring, 0.0, 0.0, total / 2.0 - overlap)
