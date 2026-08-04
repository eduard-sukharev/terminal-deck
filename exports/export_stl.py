"""STL exporter."""

from __future__ import annotations

from pathlib import Path

from utilities import cq_helpers
from utilities.constants import FORMAT_STL
from exports.export_base import Exporter


class StlExporter(Exporter):
    """Export a solid as binary STL."""

    format = FORMAT_STL

    def export(self, shape, path: Path | str) -> Path:
        cq = cq_helpers.require_cq()
        path = Path(path)
        cq.exporters.export(shape, str(path), exportType="STL")
        return path
