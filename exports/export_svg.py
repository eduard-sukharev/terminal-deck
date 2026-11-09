"""SVG exporter.

Exports a 2D projection (a flat face or sketch) as SVG. Used for laser-cut
templates and documentation views.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

from utilities import cad_helpers
from utilities.constants import FORMAT_SVG
from exports.export_base import Exporter

# The actual SVG conversion, run in a subprocess (see SvgExporter.export).
_SVG_WORKER = (
    "import sys\n"
    "from utilities import cad_helpers\n"
    "cad_helpers.export_svg(cad_helpers.import_step(sys.argv[1]), sys.argv[2])\n"
)
_REPO_ROOT = Path(__file__).resolve().parent.parent


class SvgExporter(Exporter):
    """Export a 2D shape as SVG."""

    format = FORMAT_SVG

    def export(self, shape, path: Path | str) -> Path:
        cad_helpers.require_cad()
        path = Path(path)
        # OCC's HLR (hidden-line removal) algorithm, which SVG export goes
        # through, is the least robust part of the kernel we touch: it has
        # segfaulted — not raised, *segfaulted*, killing the whole build with
        # no Python exception to catch — on a solid that STEP and STL export
        # (and the shape's own .clean()) both accepted without complaint. That
        # first happened on a large multi-part union; narrowed down by
        # bisecting which sub-union actually triggered it, not fixed by
        # cleaning harder.
        #
        # Rather than chase a specific OCC HLR bug (this kernel has had many,
        # across many shapes, for years), run the conversion in a throwaway
        # subprocess: crash it in there and this exporter can still report a
        # clean warning and move on instead of taking the whole build down.
        # The shape itself goes through a STEP round-trip first (STEP export
        # already proved reliable for exactly this geometry) rather than
        # trying to pickle a live build123d/OCC object across the process
        # boundary, which its C++ backing doesn't support anyway.
        with tempfile.TemporaryDirectory() as tmp_dir:
            step_path = Path(tmp_dir) / "shape.step"
            cad_helpers.export_shape(shape, str(step_path), "STEP")
            result = subprocess.run(
                [sys.executable, "-c", _SVG_WORKER, str(step_path), str(path)],
                capture_output=True,
                text=True,
                cwd=_REPO_ROOT,
            )
        if result.returncode < 0:
            print(
                f"[export] WARNING: SVG export of {path.name} was killed by "
                f"signal {-result.returncode} (OCC hidden-line removal) — "
                "skipping this file, the rest of the build is unaffected."
            )
            return path
        if result.returncode != 0 or not path.exists():
            print(
                f"[export] WARNING: SVG export of {path.name} failed "
                f"(exit {result.returncode}) — skipping this file, the rest "
                f"of the build is unaffected.\n{result.stderr.strip()[-2000:]}"
            )
            return path

        comment = self._metadata_comment()
        if comment:
            text = path.read_text(encoding="utf-8")
            if text.startswith("<?xml"):
                idx = text.find("?>")
                if idx != -1:
                    text = text[: idx + 2] + f"\n<!-- {comment} -->" + text[idx + 2 :]
            else:
                text = f"<!-- {comment} -->\n" + text
            path.write_text(text, encoding="utf-8")
        return path
