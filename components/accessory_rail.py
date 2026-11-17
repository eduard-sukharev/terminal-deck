"""The printed accessory rail and its washer pucks (ADR-0020).

The rail bolts to the Tray's vertical X walls over two M4 stations each; the
washer puck drops into the pad's square pocket and captures the DIN 562 nut.
Both parts are cut from the station pattern in :mod:`geometry.rail_mounts`, so
their holes cannot drift from the Tray's.

The rail is a **blank**: the MIL-STD-1913 width across the wall, its thickness
off the wall and one slot pitch of run past each end, with a counterbored M4
hole on each station. The picatinny profile (10 mm slots, hex top) is a later
slice on top of this interface -- the holes and the bridge centres stay where
they are.

Both are built in their own frame; the caller places them (the rail's local X
is its thickness, its Y its length and its Z its width, so it stands the same
way on either wall after a 180 degree turn about Z).
"""

from __future__ import annotations

from typing import Any


def build_rail(mounts: Any):
    """The rail blank, centred on its own origin (local frame)."""
    from utilities import cad_helpers as ch

    ch.require_cad()
    body = ch.box_centered(mounts.height, mounts.length, mounts.width)
    over = 0.5
    cutters = []
    for y in mounts.station_offsets:
        # The ordinary button head sits in a counterbore on the rail's outer
        # face; the clearance bore runs on through.
        pocket = ch.rotate_y(
            ch.cylinder_centered(
                mounts.head_recess.pocket_diameter, mounts.head_recess.depth + over
            ),
            90.0,
        )
        pocket = ch.translate(
            pocket,
            mounts.height / 2.0 - (mounts.head_recess.depth - over) / 2.0,
            y,
            0.0,
        )
        bore = ch.rotate_y(
            ch.cylinder_centered(mounts.screw.clearance, mounts.height + 2.0 * over),
            90.0,
        )
        bore = ch.translate(bore, 0.0, y, 0.0)
        cutters.extend((pocket, bore))
    body = ch.cut(body, *cutters)
    return ch.clean(body)


def build_rail_washer(mounts: Any):
    """The washer puck, its outboard bearing face on ``x = 0`` (local frame).

    A square printed washer with the nut's pocket opening on its cavity side:
    it cannot rotate in the pad's square pocket, the nut cannot rotate in its
    own pocket, and the puck protrudes one fit so it lifts back out.
    """
    from utilities import cad_helpers as ch

    ch.require_cad()
    over = 0.2
    body = ch.translate(
        ch.box_centered(
            mounts.puck_thickness, mounts.puck_width, mounts.puck_width
        ),
        mounts.puck_thickness / 2.0,
        0.0,
        0.0,
    )
    pocket_depth = mounts.puck_thickness - mounts.puck_floor
    pocket = ch.box_centered(
        pocket_depth + over, mounts.puck_pocket, mounts.puck_pocket
    )
    pocket = ch.translate(
        pocket,
        mounts.puck_thickness - (pocket_depth - over) / 2.0,
        0.0,
        0.0,
    )
    bore = ch.rotate_y(
        ch.cylinder_centered(mounts.screw.clearance, mounts.puck_floor + 2.0 * over),
        90.0,
    )
    bore = ch.translate(bore, mounts.puck_floor / 2.0, 0.0, 0.0)
    body = ch.cut(body, pocket, bore)
    return ch.clean(body)


def place_rail(mounts: Any, side: int):
    """One rail, standing on the ``side`` wall (world frame)."""
    from utilities import cad_helpers as ch

    part = build_rail(mounts)
    if side < 0:
        # The counterbore has to open outward on either wall.
        part = ch.rotate_z(part, 180.0)
    return ch.translate(
        part, side * mounts.rail_center_x, 0.0, mounts.stations[0].z
    )


def place_rail_washer(mounts: Any, station: Any):
    """One washer puck, seated in its station's pad pocket (world frame).

    Its plain face bears on the pocket floor and its nut pocket opens toward
    the cavity, so it turns over on the right-hand wall.
    """
    from utilities import cad_helpers as ch

    part = build_rail_washer(mounts)
    if station.side > 0:
        part = ch.rotate_z(part, 180.0)
    return ch.translate(
        part, station.side * station.pocket_floor, station.y, station.z
    )


__all__ = [
    "build_rail",
    "build_rail_washer",
    "place_rail",
    "place_rail_washer",
]
