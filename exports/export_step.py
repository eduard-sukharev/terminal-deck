"""STEP exporter."""

from __future__ import annotations

from pathlib import Path

from utilities import cq_helpers
from utilities.constants import FORMAT_STEP
from exports.export_base import Exporter


class StepExporter(Exporter):
    """Export a solid as STEP (AP214)."""

    format = FORMAT_STEP

    def export(self, shape, path: Path | str) -> Path:
        cq = cq_helpers.require_cq()
        path = Path(path)
        cq.exporters.export(shape, str(path), exportType="STEP")
        comment = self._metadata_comment()
        if comment:
            text = path.read_text()
            marker = "ISO-10303-21;\n"
            if marker in text:
                text = text.replace(marker, marker + f"/* {comment} */\n", 1)
                path.write_text(text)
        return path
