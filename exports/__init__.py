"""Exports: STEP, STL, and SVG exporters."""

from exports.export_base import EXPORTERS, GENERATED_DIR, Exporter
from exports.export_step import StepExporter
from exports.export_stl import StlExporter
from exports.export_svg import SvgExporter

# Register concrete exporters by format identifier.
EXPORTERS.update(
    {
        StepExporter.format: StepExporter,
        StlExporter.format: StlExporter,
        SvgExporter.format: SvgExporter,
    }
)

__all__ = [
    "Exporter",
    "StepExporter",
    "StlExporter",
    "SvgExporter",
    "EXPORTERS",
    "GENERATED_DIR",
]
