"""DXF export for the keyboard plate.

Produces a 2D DXF of the plate outline and cutouts for lasercutting/CNC.
Uses ``ezdxf`` (lazy import — optional dependency).
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from keyboard.metadata import KeyboardGeometryModel


def export_dxf(model: KeyboardGeometryModel, path: str | Path) -> None:
    """Write a 2D DXF of the keyboard plate.

    Parameters
    ----------
    model : KeyboardGeometryModel
        The geometry model to export.
    path : str or Path
        Output file path.
    """
    try:
        import ezdxf
    except ImportError:
        raise ImportError(
            "ezdxf is required for DXF export. Install it with: pip install ezdxf"
        )

    doc = ezdxf.new("R2010")
    msp = doc.modelspace()

    # Plate outline
    if model.plate_outline:
        msp.add_lwpolyline(model.plate_outline, close=True)

    # Switch cutouts
    for cut in model.switch_cutouts:
        msp.add_lwpolyline(cut.vertices, close=True)

    # Stabilizer cutouts
    for cut in model.stabilizer_cutouts:
        msp.add_lwpolyline(cut.vertices, close=True)

    # Mounting holes as circles
    for hole in model.mounting_holes:
        msp.add_circle((hole.x, hole.y), hole.diameter / 2.0)

    doc.saveas(str(path))
