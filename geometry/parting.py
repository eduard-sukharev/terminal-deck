"""Parting plane height and Deck screw sizing (ADR 0003).

The Parting plane is the one horizontal plane the Tray top and the Deck
bottom are both cut to. The Deck is held by M3 screws driven from below
through counterbored Tray columns into heat-set inserts in Deck bosses; the
screw length follows from the column height and the insert depth.
"""

from __future__ import annotations

from dataclasses import dataclass

from utilities import fasteners


def parting_height(parting, front_deck_level: float) -> float:
    """Parting plane height above the floor (mm).

    ``front_deck_level`` is the Deck's underside at the front edge, i.e. the
    front wall height; the plane sits at ``parting.front_wall_fraction`` of
    it, clamped to ``[parting.min, parting.max]``.
    """
    return min(parting.max, max(parting.min, parting.front_wall_fraction * front_deck_level))


@dataclass(frozen=True)
class DeckScrew:
    """The Deck screw: stock length and how far it reaches into the insert (mm)."""

    size: str
    length: int
    grip: float
    engagement: float

    @property
    def name(self) -> str:
        return f"{self.size}x{self.length}"


def deck_screw(size: str, grip: float) -> DeckScrew:
    """Longest stock screw that does not bottom out in the insert.

    ``grip`` is the screw's run from its head seat to the Parting plane (mm).
    The screw then threads into a heat-set insert of depth ``insert.depth``;
    it must reach at least one thread diameter into it. Raises ``ValueError``
    when no stock length does.
    """
    insert = fasteners.heat_insert(size)
    nominal = float(size.lstrip("M"))
    fitting = [
        length for length in fasteners.STANDARD_LENGTHS[size]
        if nominal <= length - grip <= insert.depth
    ]
    if not fitting:
        raise ValueError(
            f"no stock {size} screw engages a {insert.depth:g} mm insert across a "
            f"{grip:g} mm grip (stock: {fasteners.STANDARD_LENGTHS[size]})"
        )
    length = max(fitting)
    return DeckScrew(size=size, length=length, grip=grip, engagement=length - grip)
