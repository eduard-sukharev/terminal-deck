"""glTF exporter — multi-part, per-component/sub-assembly colored output.

Unlike the other exporters, this one's ``export()`` expects a
``cadquery.Assembly`` (built by ``Assembly.build_colored``) rather than a
single fused solid, so each component keeps its own color in the viewer.
A raw shape is still accepted and wrapped in a single-part assembly with the
palette's default color, so this exporter is a drop-in for the same
``EXPORTERS`` loop the other formats use.
"""

from __future__ import annotations

from pathlib import Path

from utilities import cq_helpers
from utilities.colors import DEFAULT_COLOR
from utilities.constants import FORMAT_GLTF
from exports.export_base import Exporter


class GltfExporter(Exporter):
    """Export a colored ``cadquery.Assembly`` (or a bare shape) as glTF."""

    format = FORMAT_GLTF

    def export(self, shape, path: Path | str) -> Path:
        cq = cq_helpers.require_cq()
        path = Path(path)
        if isinstance(shape, cq.Assembly):
            assy = shape
        else:
            assy = cq.Assembly()
            assy.add(shape, name="part", color=cq.Color(*DEFAULT_COLOR))
        # Binary glTF (.glb) vs. text (.gltf) is selected by cq from the
        # file extension; callers pass whichever they want via `path`.
        assy.save(str(path), exportType="GLTF")
        return path
