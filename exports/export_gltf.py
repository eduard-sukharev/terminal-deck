"""glTF exporter — multi-part, per-component/sub-assembly colored output.

Unlike the other exporters, this one's ``export()`` expects a
``ColoredAssembly`` (built by ``Assembly.build_colored``) rather than a
single fused solid, so each component keeps its own color in the viewer.
A raw shape is still accepted and wrapped in a single-part assembly with the
palette's default color, so this exporter is a drop-in for the same
``EXPORTERS`` loop the other formats use.
"""

from __future__ import annotations

from pathlib import Path

from utilities import cad_helpers
from utilities.colors import DEFAULT_COLOR
from utilities.constants import FORMAT_GLTF
from exports.export_base import Exporter


class GltfExporter(Exporter):
    """Export a colored ``ColoredAssembly`` (or a bare shape) as glTF."""

    format = FORMAT_GLTF

    def export(self, shape, path: Path | str) -> Path:
        path = Path(path)
        if cad_helpers.is_assembly(shape):
            assy = shape
        else:
            assy = cad_helpers.new_assembly()
            cad_helpers.assembly_add(assy, shape, "part", DEFAULT_COLOR)
        # Binary glTF (.glb) vs. text (.gltf) is selected by cq from the
        # file extension; callers pass whichever they want via `path`.
        cad_helpers.export_assembly(assy, str(path), "GLTF")
        return path
