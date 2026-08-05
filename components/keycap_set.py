"""Keycap set — cyberdeck CAD adapter for the keycap geometry model.

Builds one lofted keycap per switch centre using the profile registered in
the keycap registry.  Switch housings are **not** rendered — only the plate
cutouts and the keycaps above them.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from keyboard.layout.key import Key

# Gap between the top of the switch plate and the bottom of the keycap.
# This is the exposed switch stem height above the plate (~5.5 mm for MX).
CAP_PLATE_GAP: float = 5.5


class KeycapSet:
    """A set of keycaps lofted above the switch plate.

    Parameters
    ----------
    switch_positions : list[tuple[float, float]]
        (x, y) switch centre positions in mm (from the plate model).
    keys : list[Key]
        Layout keys in the same order as *switch_positions*.
    profile_name : str
        Registered keycap profile name (e.g. ``"xda"``).
    plate_raise : float
        Z offset of the plate bottom (mm).
    plate_thickness : float
        Plate thickness (mm).
    pitch : float
        Switch pitch in mm (default 19.05).
    layout_centroid : tuple[float, float]
        Layout centroid in units (for centering).
    enabled : bool
        If False, ``build()`` returns an empty compound (default True).
    """

    def __init__(
        self,
        switch_positions: list[tuple[float, float]],
        keys: list[Key],
        profile_name: str = "xda",
        plate_raise: float = 0.0,
        plate_thickness: float = 1.5,
        pitch: float = 19.05,
        layout_centroid: tuple[float, float] = (0.0, 0.0),
        enabled: bool = True,
    ) -> None:
        self._positions = switch_positions
        self._keys = keys
        self._profile_name = profile_name
        self._plate_raise = plate_raise
        self._plate_thickness = plate_thickness
        self._pitch = pitch
        self._centroid = layout_centroid
        self._enabled = enabled

    def build(self) -> Any:
        """Build the keycap set solid.

        Returns a CadQuery Workplane (or an empty compound if disabled).
        """
        if not self._enabled or not self._positions:
            from utilities.cq_helpers import require_cq
            cq = require_cq()
            return cq.Workplane("XY")

        from keyboard.registry import get_keycap
        from keyboard.geometry.keycaps import keycap_specs, rectangle_vertices, stadium_vertices
        from utilities import cq_helpers

        cq_helpers.require_cq()

        profile_cls = get_keycap(self._profile_name)
        profile = profile_cls()
        specs = keycap_specs(
            self._keys, profile,
            pitch=self._pitch,
            layout_centroid=self._centroid,
        )

        cap_z = self._plate_raise + self._plate_thickness + CAP_PLATE_GAP
        caps: list[Any] = []

        for sp, s in zip(self._positions, specs):
            bottom = rectangle_vertices(
                float(s["base_w"]), float(s["base_d"]),
                int(s["segments"]),
            )
            top = stadium_vertices(
                float(s["top_w"]), float(s["top_d"]),
                float(s["corner_radius"]),
                int(s["segments"]),
            )
            cap = cq_helpers.loft_between(
                bottom, top, float(s["height"]),
                x=sp[0], y=sp[1], z=cap_z,
            )

            rot = float(s["rotation"])
            if rot:
                cap = cq_helpers.rotate_z(cap, rot)

            caps.append(cap)

        if not caps:
            return cq_helpers.require_cq().Workplane("XY")
        return cq_helpers.make_compound(caps)
