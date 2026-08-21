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
        comment = self._metadata_comment()
        if comment:
            data = bytearray(path.read_bytes())
            # Binary STL reserves the first 80 bytes as a free-form header;
            # ASCII STL starts with "solid" and is left untouched.
            if not data[:5].lower().startswith(b"solid"):
                header = comment.encode()[:80]
                data[0:80] = header.ljust(80, b"\0")
                path.write_bytes(bytes(data))
        return path
