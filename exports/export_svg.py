"""SVG exporter.

Exports a 2D projection (a flat face or sketch) as SVG. Used for laser-cut
templates and documentation views.
"""

from __future__ import annotations

from pathlib import Path

from utilities import cq_helpers
from utilities.constants import FORMAT_SVG
from exports.export_base import Exporter


class SvgExporter(Exporter):
    """Export a 2D shape as SVG."""

    format = FORMAT_SVG

    def export(self, shape, path: Path | str) -> Path:
        cq = cq_helpers.require_cq()
        path = Path(path)
        # CadQuery's SVG export expects a 2D shape (Workplane with faces/edges).
        cq.exporters.export(shape, str(path), exportType="SVG")
        return path
