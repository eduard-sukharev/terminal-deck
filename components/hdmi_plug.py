"""Mated mini-HDMI cable connector body, as a placed obstruction.

The mini-HDMI ribbon that runs from the SBC to the display driver board
(through the hinge wire tunnel — see the recipe's ``cable_path``) has a real
connector shell at each end, same reasoning as ``components/usb_c_plug.py``:
modelling it as a component means the ordinary collision and clearance
machinery checks it, instead of a hand-picked margin having to be generous
enough on faith.

Unlike ``UsbCPlug``, this connects two internal boards rather than a single
host plus a cable running off to nothing — a placement of this component is
needed at *both* ends (:meth:`reference_origin` reads whichever host it is
given), one per side of the ribbon. There is exactly one mini-HDMI port per
host board, so there is no ``port_index`` to choose between — unlike the
SBC's two USB-C ports.

Local frame: the framework's standard component convention — centered on the
origin in X and Y, rising from z=0 to ``height``, with the protrusion along
the local Y (depth) axis. :meth:`reference_origin` therefore returns the
offset to the plug's *centre*, stepping out from the port by half the
connector depth plus half the plug length, and biasing Z down by half the
height so the body ends up centered on the opening — identical to
``UsbCPlug.reference_origin``.
"""

from __future__ import annotations

from typing import Any

from components.base import BoundingBox, Component
from utilities.constants import CONNECTOR_HDMI


class MiniHdmiPlug(Component):
    """The body of a mini-HDMI cable connector plugged into a host board."""

    name = "Mini-HDMI Plug"

    def __init__(
        self,
        plug: dict[str, Any] | None = None,
        host: Component | None = None,
        label: str | None = None,
    ) -> None:
        data = plug or {}
        #: How far the plug body stands off the board's connector face (mm).
        self.protrusion = float(data.get("protrusion", 21.0))
        self.width = float(data.get("width", 17.5))
        self.height = float(data.get("height", 4.5))
        self.host = host
        # Both ends of the same ribbon are separate placements of this same
        # class — a colored glTF export (ColoredAssembly) requires every
        # part to have a unique name, so the two need to be told apart. The
        # class default still works for a build with only one instance.
        if label is not None:
            self.name = f"{self.name} ({label})"

    def size(self) -> BoundingBox:
        # Depth is the protrusion: the body runs along the port axis.
        return BoundingBox(self.width, self.protrusion, self.height)

    def host_connector(self):
        """The host board's mini-HDMI connector this plug mates with.

        Raises
        ------
        ValueError
            No host was supplied, or it has no HDMI connector — better than
            silently placing the plug at the host's origin, buried inside
            the board.
        """
        if self.host is None:
            raise ValueError(
                f"{self.name} has no host board; cannot resolve its port"
            )
        ports = [c for c in self.host.connectors() if c.type == CONNECTOR_HDMI]
        if not ports:
            raise ValueError(
                f"{self.host.name} has no mini-HDMI connector to plug into"
            )
        return ports[0]

    def reference_origin(self, flip: bool = False) -> tuple[float, float, float]:
        """Offset from the host board's origin to this plug's origin (mm).

        Places the plug's mating face on the host's mini-HDMI port, so the
        recipe positions it with ``use_reference_origin`` and never restates
        the port coordinates. Because the offset is read from the host's own
        connector list, re-measuring the board moves the plug with it.
        """
        conn = self.host_connector()
        # Step out from the connector centre to the port face (half the
        # connector's depth), then out again to the plug's own centre (half
        # its length). Z is biased by half the plug height so the body —
        # which occupies ``[z, z + height]`` — ends up centered on the
        # opening rather than sitting on top of it: down (``-``) for a
        # normally-mounted host, but the host's own placement transform
        # (``Placement.world_offset``) negates a flipped host's Z component
        # (the driver board is mounted flipped, back-to-back with the
        # panel), so a flipped host needs the bias pre-negated (``+``) to
        # still land centered once that transform is applied — see
        # ``Component.reference_origin``'s ``flip`` parameter, and the
        # driver-side placement's comment in clamshell.yaml, for the
        # verification (not just this reasoning alone).
        dx, dy, _ = conn.direction
        standoff = conn.depth / 2.0 + self.protrusion / 2.0
        z_bias = self.height / 2.0 if flip else -self.height / 2.0
        return (
            conn.x + dx * standoff,
            conn.y + dy * standoff,
            conn.z + z_bias,
        )

    def build(self):
        """Generate the plug body: a box centered in XY, rising from z=0.

        The protrusion runs along local Y; :meth:`reference_origin` positions
        this box so that axis points out of the port. A port on an X-facing
        edge (e.g. the driver board's) needs the placement rotated 90
        degrees, same as any other component whose local frame does not
        happen to match its world orientation.
        """
        from utilities import cad_helpers

        cad_helpers.require_cad()
        body = cad_helpers.box_centered(self.width, self.protrusion, self.height)
        return cad_helpers.translate(body, 0.0, 0.0, self.height / 2.0)
