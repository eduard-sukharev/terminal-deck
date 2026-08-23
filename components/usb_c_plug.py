"""Mated USB-C plug body (cable end), as a placed obstruction.

A cable plugged into a board is a real solid that has to fit inside the case,
not an abstract "leave some room" margin: it protrudes a fixed length along
the port axis and needs its overmold's full cross-section. Modelling it as a
component means the ordinary collision and clearance machinery checks it,
and the layout reports *where the plug does not fit* rather than silently
relying on a hand-picked clearance number being generous enough.

The plug mates with one of a host board's USB-C connectors, chosen by index —
the deck's SBC has two (OTG and power) and which one carries the cable is an
assembly-time decision, so :meth:`reference_origin` reads the host's real
connector geometry rather than repeating its coordinates here.

Local frame: the framework's standard component convention — centered on the
origin in X and Y, rising from z=0 to ``height``, with the protrusion along
the local Y (depth) axis. :meth:`reference_origin` therefore returns the
offset to the plug's *centre*, stepping out from the port by half the
connector depth plus half the plug length, and biasing Z down by half the
height so the body ends up centered on the opening.

Keeping to the convention matters: ``Placement.box`` and
``Component.occupied_volumes`` both assume a component is centered on its
origin in XY, so a body modelled as extending *from* the origin would be
collision-checked half a plug-length away from where it is drawn.
"""

from __future__ import annotations

from typing import Any

from components.base import BoundingBox, Component
from utilities.constants import CONNECTOR_POWER, CONNECTOR_USB_C


class UsbCPlug(Component):
    """The body of a USB-C cable plugged into a host board's port."""

    name = "USB-C Plug"

    #: Connector types that are physically a USB-C socket. The SBC's power
    #: inlet is a USB-C port too — it is typed ``Power`` for what it carries,
    #: not for its shape — so matching on ``USB-C`` alone would find only one
    #: of the board's two USB-C ports and make ``port_index: 1`` unreachable.
    usb_c_types = (CONNECTOR_USB_C, CONNECTOR_POWER)

    def __init__(
        self,
        plug: dict[str, Any] | None = None,
        host: Component | None = None,
    ) -> None:
        data = plug or {}
        #: How far the plug body stands off the board's connector face (mm).
        self.protrusion = float(data.get("protrusion", 25.0))
        self.width = float(data.get("width", 11.0))
        self.height = float(data.get("height", 7.0))
        #: Which of the host's USB-C connectors this plug mates with (0-based).
        self.port_index = int(data.get("port_index", 0))
        self.host = host

    def size(self) -> BoundingBox:
        # Depth is the protrusion: the body runs along the port axis.
        return BoundingBox(self.width, self.protrusion, self.height)

    def host_connector(self):
        """The host board connector this plug mates with.

        Raises
        ------
        ValueError
            No host was supplied, or it has no USB-C connector at
            ``port_index`` — better than silently placing the plug at the
            host's origin, buried inside the board.
        """
        if self.host is None:
            raise ValueError(
                f"{self.name} has no host board; cannot resolve its port"
            )
        ports = [
            c for c in self.host.connectors() if c.type in self.usb_c_types
        ]
        if not ports:
            raise ValueError(
                f"{self.host.name} has no USB-C connector to plug into"
            )
        if not 0 <= self.port_index < len(ports):
            raise ValueError(
                f"{self.host.name} has {len(ports)} USB-C port(s); "
                f"port_index {self.port_index} is out of range"
            )
        return ports[self.port_index]

    def reference_origin(self) -> tuple[float, float, float]:
        """Offset from the host board's origin to this plug's origin (mm).

        Places the plug's mating face on the chosen port's opening, so the
        recipe positions it with ``use_reference_origin`` and never restates
        the port coordinates. Because the offset is read from the host's own
        connector list, re-measuring the board moves the plug with it.
        """
        conn = self.host_connector()
        # Step out from the connector centre to the port face (half the
        # connector's depth), then out again to the plug's own centre (half
        # its length). Z is biased down by half the plug height so the body —
        # which occupies ``[z, z + height]`` — ends up centered on the
        # opening rather than sitting on top of it.
        dx, dy, _ = conn.direction
        standoff = conn.depth / 2.0 + self.protrusion / 2.0
        return (
            conn.x + dx * standoff,
            conn.y + dy * standoff,
            conn.z - self.height / 2.0,
        )

    def build(self):
        """Generate the plug body: a box centered in XY, rising from z=0.

        The protrusion runs along local Y; :meth:`reference_origin` positions
        this box so that axis points out of the port. A port on an X-facing
        edge would need the placement rotated 90 degrees.
        """
        from utilities import cq_helpers

        cq_helpers.require_cq()
        body = cq_helpers.box_centered(self.width, self.protrusion, self.height)
        return cq_helpers.translate(body, 0.0, 0.0, self.height / 2.0)
