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

    def validate(self) -> tuple[int, list[str]]:
        """Check that ports don't overlap each other or run off the PCB edges.

        The north-edge ports are spaced by a computed (not measured) formula
        and the east port is positioned independently, so nothing upstream
        guarantees they stay clear of each other or within the board outline
        as config values change. Returns ``(check_count, errors)``, matching
        the keyboard subsystem's ``validate()`` convention.
        """
        errors: list[str] = []
        checks = 0

        specs = self._north_port_specs()
        xs = self._north_port_x_positions()
        north_boxes = [
            (kind, x - w / 2.0, x + w / 2.0, y_span)
            for (kind, w, _h, d), x in zip(specs, xs)
            for y_span in [(self.depth / 2.0 - d + self.protrusion, self.depth / 2.0 + self.protrusion)]
        ]

        checks += 1
        if north_boxes[0][1] < -self.width / 2.0:
            errors.append(
                f"north port {north_boxes[0][0]!r} starts at x={north_boxes[0][1]:.2f}, "
                f"{-self.width / 2.0 - north_boxes[0][1]:.2f} mm off the west edge of the PCB"
            )

        checks += 1
        if north_boxes[-1][2] > self.width / 2.0:
            errors.append(
                f"north port {north_boxes[-1][0]!r} ends at x={north_boxes[-1][2]:.2f}, "
                f"{north_boxes[-1][2] - self.width / 2.0:.2f} mm off the east edge of the PCB"
            )

        for (kind_a, _, x1_end, _), (kind_b, x2_start, _, _) in zip(north_boxes, north_boxes[1:]):
            checks += 1
            gap = x2_start - x1_end
            if gap < 0.0:
                errors.append(
                    f"north ports {kind_a!r} and {kind_b!r} overlap by {-gap:.2f} mm "
                    "— widen edge_inset or shrink the ports"
                )

        east_d = self.usb_a_depth
        east_x = self.width / 2.0 - east_d / 2.0 + self.protrusion
        east_x0, east_x1 = east_x - east_d / 2.0, east_x + east_d / 2.0
        east_y0, east_y1 = -self.usb_a_width / 2.0, self.usb_a_width / 2.0

        checks += 1
        if east_y1 > self.depth / 2.0 or east_y0 < -self.depth / 2.0:
            errors.append(
                f"east USB-A port spans y=[{east_y0:.2f}, {east_y1:.2f}], "
                f"outside the PCB depth [{-self.depth / 2.0:.2f}, {self.depth / 2.0:.2f}]"
            )

        for kind, nx0, nx1, (ny0, ny1) in north_boxes:
            checks += 1
            x_overlap = min(east_x1, nx1) - max(east_x0, nx0)
            y_overlap = min(east_y1, ny1) - max(east_y0, ny0)
            if x_overlap > 0.0 and y_overlap > 0.0:
                errors.append(
                    f"east USB-A port overlaps north port {kind!r} by "
                    f"{x_overlap:.2f} x {y_overlap:.2f} mm at the NE corner"
                )

        return checks, errors

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
