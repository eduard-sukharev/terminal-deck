"""Keyboard layout model — the internal representation after parsing.

:class:`KeyboardLayout` holds the parsed keys and provides methods to
retrieve switch centers, bounding box, and stabilizer positions in
millimeters.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from keyboard.layout.key import Key


@dataclass
class KeyboardLayout:
    """Internal keyboard layout model.

    Attributes
    ----------
    keys : list[Key]
        All keys in the layout (flat list, not grouped by row).
    pitch : float
        Switch pitch in mm (default 19.05).
    """

    keys: list[Key] = field(default_factory=list)
    pitch: float = 19.05

    @property
    def switch_centers(self) -> list[tuple[float, float]]:
        """Switch center positions in mm, centered on the layout centroid."""
        if not self.keys:
            return []
        cx, cy = self._centroid()
        return [
            ((k.x - cx) * self.pitch, (k.y - cy) * self.pitch)
            for k in self.keys
        ]

    def switch_center_mm(self, key: Key) -> tuple[float, float]:
        """Return the (x, y) position of *key* in mm, centered on layout."""
        cx, cy = self._centroid()
        return ((key.x - cx) * self.pitch, (key.y - cy) * self.pitch)

    def _centroid(self) -> tuple[float, float]:
        """Geometric center of the key field in units.

        This is the midpoint of the occupied extents, not the mean of the key
        positions. The mean is pulled off-center by uneven key counts per row
        — a 40% layout with a sparse bottom row shifts it several millimetres
        — which would leave the plate outline, and therefore the component's
        bounding box, no longer centered on the component origin that every
        placement is measured from.
        """
        if not self.keys:
            return (0.0, 0.0)
        xs = [k.x for k in self.keys]
        ys = [k.y for k in self.keys]
        return ((min(xs) + max(xs)) / 2.0, (min(ys) + max(ys)) / 2.0)

    @property
    def width_units(self) -> float:
        """Total width of the layout in key units."""
        if not self.keys:
            return 0.0
        min_x = min(k.x - k.width / 2.0 for k in self.keys)
        max_x = max(k.x + k.width / 2.0 for k in self.keys)
        return max_x - min_x

    @property
    def height_units(self) -> float:
        """Total height of the layout in key units."""
        if not self.keys:
            return 0.0
        min_y = min(k.y - k.height / 2.0 for k in self.keys)
        max_y = max(k.y + k.height / 2.0 for k in self.keys)
        return max_y - min_y

    @property
    def width_mm(self) -> float:
        return self.width_units * self.pitch

    @property
    def height_mm(self) -> float:
        return self.height_units * self.pitch
