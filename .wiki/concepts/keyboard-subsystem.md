---
title: "Keyboard Subsystem"
type: "concept"
status: "active"
language: "default"
source_paths: ["docs/keyboard_architecture.md", "keyboard/"]
updated_at: "2026-08-05"
---

# Keyboard Subsystem

The keyboard subsystem is a **geometry generator**: it converts a keyboard
layout into reusable CadQuery geometry for the cyberdeck assembly. It is *not* a
keyboard CAD application, and it is not responsible for keyboard case/PCB
generation, firmware, wiring, or bill of materials. Its responsibility ends at
accurate keyboard geometry and metadata for the enclosure generator.

Spec: `docs/keyboard_architecture.md` (external handoff guideline).

## Design goals

Entirely scriptable, native CadQuery output, fully parametric, independent of any
particular enclosure *or* switch family, easily extensible, deterministic, and
suitable for autonomous LLM development. The keyboard must behave as a reusable
CAD component, not a standalone project.

## Structure (implemented)

```
keyboard/
    layout/      kle_parser.py, layout.py, key.py
    switches/    kb_builder.py
    stabilizers/ kb_builder.py
    keycaps/     xda.py
    geometry/    plate.py, outline.py, mounting.py, cutouts.py, keycaps.py
    reference/   switch_cutouts.yaml, stabilizer_cutouts.yaml, keycap_profiles.yaml
    export/      dxf.py, svg.py
    metadata.py, registry.py, validation.py, __init__.py
```

The module has no dependency on cyberdeck geometry or on CadQuery — it imports
cleanly without it (verified by blocking `cadquery` at import). The cyberdeck
adapters (`components/keyboard_plate.py`, `components/rp2040_keyboard.py`,
`components/keycap_set.py`) consume its `KeyboardGeometryModel` and extrude
polygons through `utilities/cq_helpers.py`.

Keycap profiles (`keycaps/xda.py`, `reference/keycap_profiles.yaml`) follow the
same registry pattern as switches/stabilizers; the cyberdeck adapter lofts them
into caps above the plate. See [[keycaps]].

## Data flow

```
KLE JSON → Layout Parser → Internal Layout Model → Switch Library →
Stabilizer Library → Plate Generator → CadQuery Solid → Cyberdeck Assembly
```

Each stage has exactly one responsibility. The plate generator only assembles
geometry from reusable libraries; it contains almost no keyboard-specific
knowledge (see [[keyboard-layout-and-libraries]]).

## Reference geometries (kb_builder)

The switch and stabilizer library geometry in `reference/*.yaml` mirrors what
**kb_builder** (https://github.com/swill/kb_builder, `../kb_builder`) provides:
its `lib/builder.py` contains reference cutout geometry for switch types and
stabilizer types (Cherry MX, costar, spacebar stabilizers) driven by the same KLE
JSON layout format. The YAMLs are loaded at import time by
`keyboard/switches/kb_builder.py` and `keyboard/stabilizers/kb_builder.py`, and
are shipped as package data (see `pyproject.toml`).

## Integration with the cyberdeck

The keyboard is one reusable component inside the larger assembly (display,
Orange Pi, keyboard plate, RP2040, hinges, enclosure, fasteners). The keyboard
knows nothing about the enclosure; the enclosure knows only the keyboard's
geometry and metadata. See [[component-data-pipeline]] for where that sits, and
[[cad-conventions]] for the rules both must honor.
