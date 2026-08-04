---
title: "Keyboard Subsystem"
type: "concept"
status: "draft"
language: "default"
source_paths: ["docs/keyboard_architecture.md"]
updated_at: "2026-08-04"
---

# Keyboard Subsystem

The keyboard subsystem is a **geometry generator**: it converts a keyboard
layout into reusable CadQuery geometry for the cyberdeck assembly. It is *not* a
keyboard CAD application, and it is not responsible for keyboard case/PCB
generation, firmware, wiring, or bill of materials. Its responsibility ends at
accurate keyboard geometry and metadata for the enclosure generator.

Spec: `docs/keyboard_architecture.md` (external handoff guideline).

> **Status: design, not implemented.** This describes a proposed `keyboard/`
> package. The current codebase instead builds the plate from the grid config in
> `config/keyboard.yaml` via `components/keyboard_plate.py`, with cutouts in
> `geometry/switch_cutout.py` / `geometry/stabilizer_cutout.py`. A JD40 layout
> already exists in ergogen format at `JD40.yaml`.

## Design goals

Entirely scriptable, native CadQuery output, fully parametric, independent of any
particular enclosure *or* switch family, easily extensible, deterministic, and
suitable for autonomous LLM development. The keyboard must behave as a reusable
CAD component, not a standalone project.

## Proposed structure

```
keyboard/
    layout/      kle_parser.py, layout.py, key.py
    switches/    kb_builder.py
    stabilizers/ kb_builder.py
    geometry/    plate.py, outline.py, mounting.py, cutouts.py
    reference/   switch_cutouts.yaml, stabilizer_cutouts.yaml
    export/      dxf.py, svg.py
    validation.py
```

The module must have no dependency on cyberdeck geometry.

## Data flow

```
KLE JSON → Layout Parser → Internal Layout Model → Switch Library →
Stabilizer Library → Plate Generator → CadQuery Solid → Cyberdeck Assembly
```

Each stage has exactly one responsibility. The plate generator only assembles
geometry from reusable libraries; it contains almost no keyboard-specific
knowledge (see [[keyboard-layout-and-libraries]]).

## Reference geometries (kb_builder)

The switch and stabilizer library geometry in the spec's `reference/*.yaml`
mirrors what **kb_builder** (https://github.com/swill/kb_builder, checked out at
`../kb_builder`) provides: its `lib/builder.py` contains reference cutout
geometry for switch types and stabilizer types (Cherry MX, costar, spacebar
stabilizers) driven by the same KLE JSON layout format. Use it as the source of
reference geometries when filling the `reference/*.yaml` data.

## Integration with the cyberdeck

The keyboard is one reusable component inside the larger assembly (display,
Orange Pi, keyboard plate, RP2040, hinges, enclosure, fasteners). The keyboard
knows nothing about the enclosure; the enclosure knows only the keyboard's
geometry and metadata. See [[component-data-pipeline]] for where that sits, and
[[cad-conventions]] for the rules both must honor.
