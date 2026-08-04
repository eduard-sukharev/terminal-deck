"""Exporter interface.

All exporters write a CadQuery shape to the ``generated/`` directory in a
specific format. The base class validates the output path; format-specific
exporters delegate to CadQuery's exporters.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from utilities.constants import FORMAT_STEP, FORMAT_STL, FORMAT_SVG

#: Root of all generated output.
GENERATED_DIR: Path = Path(__file__).resolve().parent.parent / "generated"


class Exporter(ABC):
    """Abstract exporter with a declared format."""

    #: Export format identifier, one of ``utilities.constants.FORMAT_*``.
    format: str = ""

    def output_path(self, name: str, output_dir: Path | None = None) -> Path:
        """Return the absolute output path for ``name`` in this format.

        Parameters
        ----------
        name : str
            Build/part name, e.g. ``"cyberdeck_base"``.
        output_dir : Path or None
            Output directory; defaults to ``generated/<format>/``.

        Returns
        -------
        Path
            ``<output_dir>/<name>.<extension>``.
        """
        directory = output_dir or (GENERATED_DIR / self.format)
        directory.mkdir(parents=True, exist_ok=True)
        return directory / f"{name}.{self.extension}"

    @property
    def extension(self) -> str:
        return self.format.lower()

    @abstractmethod
    def export(self, shape, path: Path | str) -> Path:
        """Write ``shape`` to ``path`` and return the path.

        Parameters
        ----------
        shape : cadquery.Shape
            The solid to export.
        path : Path or str
            Destination file path.

        Returns
        -------
        Path
            The written file path.
        """


EXPORTERS: dict[str, type[Exporter]] = {
    FORMAT_STEP: None,  # populated below to avoid circular import
    FORMAT_STL: None,
    FORMAT_SVG: None,
}
