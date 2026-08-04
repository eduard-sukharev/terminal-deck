"""Compact clamshell layout.

A tighter variant: the SBC is stacked directly beneath the keyboard plate and
the display is pulled forward to minimize the footprint. Positions are
calculated from component sizes — no CAD.
"""

from __future__ import annotations

from layouts.base import Layout, Placement


class LayoutCompact(Layout):
    """Compact clamshell layout."""

    name = "compact"

    def _build_placements(self, placements: list[Placement]) -> None:
        keyboard = self.components["keyboard"]
        sbc = self.components["sbc"]
        display = self.components["display"]

        kb = keyboard.size()

        # Keyboard centered at the base origin, SBC stacked underneath it.
        placements.append(Placement(keyboard, 0.0, 0.0, rotation=0.0, z=0.0))
        sbc_z = sbc.size().height / 2 + kb.height / 2
        placements.append(Placement(sbc, 0.0, 0.0, rotation=0.0, z=sbc_z))

        # Display in the lid, forward of center to shorten the deck.
        placements.append(
            Placement(display, 0.0, kb.depth / 2 + 6.0, rotation=0.0, z=60.0)
        )
