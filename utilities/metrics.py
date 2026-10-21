"""Geometry metrics for golden-master regression testing.

Computes a small, backend-agnostic summary (volume, bounding box, center of
mass) of a built solid. Used to record a baseline snapshot of every build
target and detect silent geometry drift across refactors (e.g. the
CadQuery -> build123d port) without needing to diff STEP/STL bytes, which
change on every export even for an identical solid.

Goes through :mod:`utilities.cad_helpers`, never the CAD library directly,
so this module survives a backend swap unchanged.
"""

from __future__ import annotations

from typing import Any


def shape_metrics(shape: Any) -> dict[str, Any]:
    """Return a JSON-serializable metrics summary for *shape*.

    Parameters
    ----------
    shape : Shape
        A built solid (or colored assembly is not supported here — pass the
        fused solid).

    Returns
    -------
    dict
        ``volume`` (mm^3), ``bbox`` ([xlen, ylen, zlen] mm), ``com``
        ([x, y, z] mm center of mass), ``n_faces``, ``n_solids``.
    """
    from utilities import cad_helpers

    cad_helpers.require_cad()
    bbox = cad_helpers.bounding_box_mm(shape)
    com = cad_helpers.center_of_mass_mm(shape)
    return {
        "volume": cad_helpers.volume_mm3(shape),
        "bbox": list(bbox),
        "com": list(com),
        "n_faces": cad_helpers.face_count(shape),
        "n_solids": cad_helpers.solid_count(shape),
    }
