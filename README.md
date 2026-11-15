# Cyberdeck CAD Generator

Fully parametric **slider** cyberdeck for field debugging of 3D printers: the
screen lid slides along the face to reveal a 40% keyboard, so the screen stays
visible when the device is closed. The clamshell form was retired in ADR-0009.

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
* +X -> right, +Y -> along the slide (toward the screen end), +Z -> upward.
* Origin: centre of the chassis footprint, on the table plane. Never redefine
  origins.

See `docs/coordinate_system.md`, `docs/component_spec.md`, and
`docs/cad_api.md` for the full contract.

## Repository layout

```
config/        YAML configuration (default, display, keyboard, hardware)
components/    hardware components (Component API, measured data)
geometry/      generative CAD helpers (boss, ribs, vents, cutouts, edge treatment, split)
layouts/       placement-only layout definitions (no CAD)
assemblies/    collision / clearance / enclosure resolution
case/          chassis and screen-lid shell generation
routing/       cable routing engine (bend radius, drag-chain channel)
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

# builds are incremental: a target is reused when its sources, the config and
# its exports are unchanged (see utilities/build_cache.py), so re-running only
# rebuilds what moved. `--no-cache` (or `make rebuild`) forces a full rebuild,
# and `make clean` drops the cache along with the exports.
```

## Status

CAD generation is implemented on build123d. Create the env once with
`conda create -n cyberdeck python=3.12 && conda activate cyberdeck &&
pip install -r requirements.txt`.

The target form is a **slider** (ADR-0009/0010): a 140 mm closed face height,
a screen lid sliding on two guide rods over a chassis, and a 40% keyboard
revealed by the slide. The **data skeleton and the first-generation CAD shell**
are implemented: `python main.py --layout slider --steps data` derives and
validates the 140/56/283 budget from the real components, and `make all`
builds and exports the chassis, screen lid, guide rods, printed
Rod clamps and Bearing clamps, and both the closed and open assembly (the lid,
rods and Rod clamps slid by the travel) as STEP/STL/glTF, each shell piece split
into two Sections on its own staggered Seam (ADR-0015) and registered by
fin-pair glued filament pins (ADR-0006) to fit the
220 × 220 × 256 mm build volume. The
slider is the only layout; the retired clamshell code is removed. See
`docs/form_factor.md`, `docs/adr/`, and `CONTEXT.md`.
