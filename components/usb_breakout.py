"""USB hub board (ZMT23_HUB_VER1.0).

Multifunctional USB hub PCB: ribbon cable on the west edge, 1x USB-A on the
east edge, and on the north edge (west to east) 3x USB-A, a micro-SD reader,
an audio jack, and a USB-C port. Dimensions from ``config/hardware.yaml``
(``usb_breakout`` section).
"""

from __future__ import annotations

from typing import Any

from components.base import BoundingBox, Component, Connector
from utilities.constants import (
    CONNECTOR_AUDIO,
    CONNECTOR_MICROSD,
    CONNECTOR_USB_A,
    CONNECTOR_USB_C,
    DIR_POS_X,
    DIR_POS_Y,
)

# (kind, config key) for the north-edge ports, west to east, as observed on
# the board.
_NORTH_PORT_KINDS = ("usb_a", "usb_a", "usb_a", "microsd", "audio", "usb_c")


class UsbBreakout(Component):
    """USB hub PCB with USB-A/USB-C/micro-SD/audio ports."""

    name = "USB Hub"

    def __init__(self, hardware: dict[str, Any] | None = None) -> None:
        data = (hardware or {}).get("usb_breakout", {})
        self.width = float(data.get("pcb_width", 133.0))
        self.depth = float(data.get("pcb_depth", 24.0))
        self.pcb_thickness = float(data.get("pcb_thickness", 1.0))
        self.protrusion = float(data.get("port_protrusion", 1.4))
        self.edge_inset = float(data.get("edge_inset", 10.0))

        usb_a = data.get("usb_a", {})
        self.usb_a_width = float(usb_a.get("width", 13.3))
        self.usb_a_height = float(usb_a.get("height", 8.5))
        self.usb_a_depth = float(usb_a.get("depth", 6.0))

        usb_c = data.get("usb_c", {})
        self.usb_c_width = float(usb_c.get("width", 9.0))
        self.usb_c_height = float(usb_c.get("height", 7.0))
        self.usb_c_depth = float(usb_c.get("depth", 3.3))

        audio = data.get("audio_jack", {})
        self.audio_diameter = float(audio.get("diameter", 5.0))
        self.audio_depth = float(audio.get("depth", 15.0))

        microsd = data.get("microsd", {})
        self.microsd_width = float(microsd.get("width", 13.5))
        self.microsd_thickness = float(microsd.get("thickness", 2.0))
        self.microsd_depth = float(microsd.get("depth", 12.0))

    # -- geometry helpers ---------------------------------------------------

    def _pcb_center_z(self) -> float:
        """Z of the PCB mid-plane that every through-cutout port is centered on."""
        return max(self.usb_a_height, self.usb_c_height) / 2.0

    def _north_port_specs(self) -> list[tuple[str, float, float, float]]:
        """North-edge ports, west to east, as ``(kind, width, height, depth)``."""
        by_kind = {
            "usb_a": (self.usb_a_width, self.usb_a_height, self.usb_a_depth),
            "usb_c": (self.usb_c_width, self.usb_c_height, self.usb_c_depth),
            "audio": (self.audio_diameter, self.audio_diameter, self.audio_depth),
            "microsd": (self.microsd_width, self.microsd_thickness, self.microsd_depth),
        }
        return [(kind, *by_kind[kind]) for kind in _NORTH_PORT_KINDS]

    def _north_port_x_positions(self) -> list[float]:
        """Evenly space the north-edge ports within the PCB's edge margin.

        Exact factory placement was not measured; ports are distributed with
        equal gaps across the usable edge width (PCB width minus
        ``edge_inset`` on each side), in the west-to-east order observed on
        the board.
        """
        widths = [w for _, w, _, _ in self._north_port_specs()]
        usable = self.width - 2.0 * self.edge_inset
        gap = (usable - sum(widths)) / (len(widths) - 1)
        xs: list[float] = []
        cursor = -usable / 2.0
        for w in widths:
            xs.append(cursor + w / 2.0)
            cursor += w + gap
        return xs

    def size(self) -> BoundingBox:
        pcb_top = self._pcb_center_z() + self.pcb_thickness / 2.0
        microsd_top = pcb_top + self.microsd_thickness
        height = max(self.usb_a_height, self.usb_c_height, microsd_top)
        return BoundingBox(self.width, self.depth, height)

    # No mounting_holes() override: this board has no mounting holes — it
    # must be retained by its edge connectors and a case-side clip/cradle
    # instead (see the base Component default, which returns none).

    def connectors(self) -> list[Connector]:
        pcb_z = self._pcb_center_z()
        conns: list[Connector] = []
        for (kind, w, h, d), x in zip(self._north_port_specs(), self._north_port_x_positions()):
            y = self.depth / 2.0 - d / 2.0 + self.protrusion
            if kind == "microsd":
                z = pcb_z + self.pcb_thickness / 2.0 + self.microsd_thickness / 2.0
                conns.append(Connector(CONNECTOR_MICROSD, x, y, z, DIR_POS_Y, w, h, d))
            elif kind == "audio":
                conns.append(Connector(CONNECTOR_AUDIO, x, y, pcb_z, DIR_POS_Y, w, h, d))
            elif kind == "usb_c":
                conns.append(Connector(CONNECTOR_USB_C, x, y, pcb_z, DIR_POS_Y, w, h, d))
            else:
                conns.append(Connector(CONNECTOR_USB_A, x, y, pcb_z, DIR_POS_Y, w, h, d))

        east_x = self.width / 2.0 - self.usb_a_depth / 2.0 + self.protrusion
        conns.append(
            Connector(
                CONNECTOR_USB_A, east_x, 0.0, pcb_z, DIR_POS_X,
                self.usb_a_width, self.usb_a_height, self.usb_a_depth,
            )
        )
        return conns

    def build(self):
        """PCB slab boolean-unioned with every port body (no PCB cutouts).

        Every through-cutout port (USB-A/USB-C/audio) is centered on the PCB
        mid-plane; the micro-SD reader sits on the PCB's top surface instead.
        All ports overhang their PCB edge by ``port_protrusion``.
        """
        from utilities import cq_helpers

        cq_helpers.require_cq()
        pcb_z = self._pcb_center_z()
        board = cq_helpers.box_centered(self.width, self.depth, self.pcb_thickness)
        board = cq_helpers.translate(board, 0.0, 0.0, pcb_z)

        parts = [board]
        for (kind, w, h, d), x in zip(self._north_port_specs(), self._north_port_x_positions()):
            y = self.depth / 2.0 - d / 2.0 + self.protrusion
            if kind == "audio":
                jack = cq_helpers.cylinder_centered(self.audio_diameter, d)
                jack = cq_helpers.rotate_x(jack, 90.0)
                parts.append(cq_helpers.translate(jack, x, y, pcb_z))
            elif kind == "microsd":
                z = pcb_z + self.pcb_thickness / 2.0 + self.microsd_thickness / 2.0
                reader = cq_helpers.box_centered(w, d, self.microsd_thickness)
                parts.append(cq_helpers.translate(reader, x, y, z))
            else:
                port = cq_helpers.box_centered(w, d, h)
                parts.append(cq_helpers.translate(port, x, y, pcb_z))

        east_d = self.usb_a_depth
        east_x = self.width / 2.0 - east_d / 2.0 + self.protrusion
        east_port = cq_helpers.box_centered(east_d, self.usb_a_width, self.usb_a_height)
        parts.append(cq_helpers.translate(east_port, east_x, 0.0, pcb_z))

        result = parts[0]
        for part in parts[1:]:
            result = result.union(part)
        return result
