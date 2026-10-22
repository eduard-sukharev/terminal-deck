# Cyberdeck CAD Generator

Fully parametric clamshell cyberdeck for field debugging of 3D printers.

Target hardware:

* SBC: Orange Pi Zero 2W
* Display: 8.8" 1920x480 (HDMI driver board)
* Keyboard: 40% Cherry-MX-compatible, RP2040, QMK/Vial

This project is **not** a maker platform: no GPIO, sensors, LEDs, or decorative
elements. Priorities are robustness, serviceability, printability,
parametricity, and reusability.

## Design philosophy

Never write CAD directly around dimensions.

```
Component -> Placement -> Assembly -> Enclosure -> Features -> Export
```

Everything derives from reusable components. Layouts contain no CAD, only
placements. Every dimension originates from configuration, a measured
component, or calculated geometry — never intuition.

## Coordinate system and units

* Units: millimeters, always.
* +X -> right, +Y -> forward, +Z -> upward.
* Origin: center of the base. Never redefine origins.

See `docs/coordinate_system.md`, `docs/component_spec.md`, and
`docs/cad_api.md` for the full contract.

## Repository layout

```
config/        YAML configuration (default, display, keyboard, hardware)
components/    hardware components (Component API, measured data)
geometry/      generative CAD helpers (boss, fillet, shell, ribs, vents, cutouts)
layouts/       placement-only layout definitions (no CAD)
assemblies/    collision / clearance / enclosure resolution
case/          base and lid shell generation
routing/       cable routing engine (bend radius, clearance tunnels)
exports/       STEP / STL / SVG exporters
utilities/     constants, cad_helpers, fasteners, validation, config loading
generated/     output directory for exported files
docs/          specifications
```

## Usage

```bash
# activate the build123d environment (setup: see AGENTS.md)
conda activate cyberdeck

# generate the build (STEP + STL + SVG)
python main.py --config config/default.yaml --steps all
```

## Status

CAD generation is implemented on build123d. Create the env once with
`conda create -n cyberdeck python=3.12 && conda activate cyberdeck &&
pip install -r requirements.txt`. The case is a symmetric clamshell (Lid has the
Base's footprint, Visor closes the Deck slope, P6-style three-knuckle hinge);
every wide part is exported as left/right Halves that fit the 220 × 220 × 256 mm
build volume. See `docs/form_factor.md`, `docs/adr/`, and `CONTEXT.md`.
