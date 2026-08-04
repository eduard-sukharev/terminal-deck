# Component Specification

Every hardware component implements the shared `Component` API so placement,
assembly, and enclosure generation stay generic.

## Component API

```python
class Component(ABC):
    name: str

    def size(self) -> BoundingBox          # measured overall size, mm
    def mounting_holes(self) -> list[Hole] # relative to component origin
    def connectors(self) -> list[Connector]
    def keepout(self) -> Keepout           # default: size + cable allowance
    def reference_origin(self) -> (x, y, z)  # default (0, 0, 0)
    def build(self) -> cadquery.Shape      # CAD solid, NotImplemented
```

## Data model

| Type        | Fields                                   |
|-------------|------------------------------------------|
| `BoundingBox` | `width, depth, height` (all > 0)       |
| `Hole`        | `x, y, diameter`                       |
| `Connector`   | `type, x, y, z, direction, width, height, depth` |
| `Keepout`     | `width, depth, height`                 |

`Connector.type` is one of the constants in `utilities/constants.py`:
`CONNECTOR_USB_C`, `CONNECTOR_USB_A`, `CONNECTOR_HDMI`, `CONNECTOR_ETHERNET`,
`CONNECTOR_AUDIO`, `CONNECTOR_MICROSD`, `CONNECTOR_POWER`.

## Components

| Module                      | Measured source                                | Status |
|-----------------------------|------------------------------------------------|--------|
| `orange_pi_zero2w.py`       | Official user manual + hand measurement        | verified (board, connectors, height) |
| `display_88.py`             | HannStar HSD088IPW1-A00 + hand measurement     | verified; no mounting holes (bezel-held), FPC 38.5 mm |
| `hdmi_driver.py`            | Hand measurement                               | verified (board, connectors, holes) |
| `rp2040_keyboard.py`        | `config/keyboard.yaml` (calculated)            | grid real |
| `rp2040_zero.py`            | Waveshare RP2040-Zero: 23.5x18x8, 4x 2.0mm holes | verified |
| `usb_breakout.py`           | `config/hardware.yaml` (usb_breakout)          | size real (TODO measure) |
| `heatset_insert.py`         | `utilities/fasteners.py`                        | real |
| `hinge.py`                  | `config/default.yaml` (hinge)                   | data real, CAD TODO |
| `keyboard_plate.py`         | `config/keyboard.yaml` (calculated)             | grid real, CAD TODO |

## Measurement rules

* All dimensions originate from configuration, a measured component, or
  calculated geometry. Never intuition.
* Values not yet measured carry a `# TODO: measure ...` marker.
* `size()` is always a measured or calculated `BoundingBox` — never estimated.
