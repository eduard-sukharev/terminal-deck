"""Project-wide constants and conventions.

Coordinate system
=================
+X -> right
+Y -> forward
+Z -> upward

Origin: center of the base. Never redefine origins.

Units
=====
All dimensions are millimeters, always. Never inches.
"""

from typing import Final

# Units ----------------------------------------------------------------
UNIT: Final[str] = "millimeters"

# Coordinate system ----------------------------------------------------
AXIS_X: Final[str] = "x"
AXIS_Y: Final[str] = "y"
AXIS_Z: Final[str] = "z"

# Orientation faces, used for connector direction and export views -------
# direction vectors
DIR_POS_X: Final[tuple[float, float, float]] = (1.0, 0.0, 0.0)
DIR_NEG_X: Final[tuple[float, float, float]] = (-1.0, 0.0, 0.0)
DIR_POS_Y: Final[tuple[float, float, float]] = (0.0, 1.0, 0.0)
DIR_NEG_Y: Final[tuple[float, float, float]] = (0.0, -1.0, 0.0)
DIR_POS_Z: Final[tuple[float, float, float]] = (0.0, 0.0, 1.0)
DIR_NEG_Z: Final[tuple[float, float, float]] = (0.0, 0.0, -1.0)

# Connector type identifiers ----------------------------------------------
CONNECTOR_USB_C: Final[str] = "USB-C"
CONNECTOR_USB_A: Final[str] = "USB-A"
CONNECTOR_HDMI: Final[str] = "HDMI"
CONNECTOR_ETHERNET: Final[str] = "Ethernet"
CONNECTOR_AUDIO: Final[str] = "Audio"
CONNECTOR_MICROSD: Final[str] = "MicroSD"
CONNECTOR_POWER: Final[str] = "Power"

# Export formats -----------------------------------------------------------
FORMAT_STEP: Final[str] = "step"
FORMAT_STL: Final[str] = "stl"
FORMAT_SVG: Final[str] = "svg"

# Material defaults ----------------------------------------------------------
MINIMUM_WALL_THICKNESS: Final[float] = 2.5
