# Keyboard Subsystem Architecture Specification

## Purpose

The keyboard subsystem is a geometry generator that converts a keyboard layout into reusable CadQuery geometry for the cyberdeck assembly.

It is **not** a keyboard CAD application.

It is **not** responsible for:

* keyboard case generation
* PCB generation
* firmware generation
* wiring
* bill of materials

Its responsibility ends with producing accurate keyboard geometry and metadata that can be consumed by the cyberdeck enclosure generator.

---

# Design Goals

The subsystem must satisfy the following requirements.

* Entirely scriptable
* Native CadQuery output
* Fully parametric
* Independent of any particular enclosure
* Independent of any switch family
* Easily extensible
* Deterministic
* Suitable for autonomous LLM development

The keyboard must behave as a reusable CAD component rather than a standalone project.

---

# Input

The primary input is a Keyboard Layout Editor (KLE) JSON layout.

The initial layout is based on the JD40 preset with project-specific modifications.

The layout file is considered the canonical description of key positions.

No key coordinates should ever be duplicated elsewhere.

---

# Output

The subsystem produces:

* keyboard plate
* switch cutouts
* stabilizer cutouts
* mounting holes
* plate outline
* bounding box
* key metadata
* switch center locations
* CadQuery solid
* optional DXF export

No enclosure geometry is generated.

---

# Repository Structure

```
keyboard/

    __init__.py

    layout/

        kle_parser.py
        layout.py
        key.py

    switches/

        kb_builder.py

    stabilizers/

        kb_builder.py

    geometry/

        plate.py
        outline.py
        mounting.py
        cutouts.py

    reference/

        switch_cutouts.yaml
        stabilizer_cutouts.yaml

    export/

        dxf.py
        svg.py

    validation.py
```

The keyboard module should have no dependency on cyberdeck geometry.

---

# Data Flow

```
KLE JSON

↓

Layout Parser

↓

Internal Layout Model

↓

Switch Library

↓

Stabilizer Library

↓

Plate Generator

↓

CadQuery Solid

↓

Cyberdeck Assembly
```

Each stage has exactly one responsibility.

---

# Internal Layout Model

The parser converts KLE into an internal representation.

Example:

```python
KeyboardLayout

    keys: List[Key]
```

Each key stores:

```python
Key

    x

    y

    rotation

    width

    height

    legend

    switch_type

    stabilizer_type
```

This object contains no geometry.

It is purely descriptive.

---

# Switch Library

Switch geometry is isolated from layout logic.

Directory:

```
switches/
```

Each switch family implements a common interface.

Example:

```python
class Switch:

    def cutout()

    def plate_tolerance()

    def plate_thickness()

    def pcb_keepout()

    def body_size()

    def mounting_features()

    def switch_center()

    def metadata()
```

The plate generator must never know whether it is using Cherry MX, Alps or Kailh Choc switches.

It only interacts with the abstract interface.

---

# Stabilizer Library

Stabilizers follow the same design philosophy.

```
stabilizers/

    kb_builder.py
```

Three families are registered from kb_builder's cutout geometry:

| Code | Name | Description |
|------|------|-------------|
| 0 | ``costar_compat`` | Modified MX cherry spec (costar-compatible) |
| 1 | ``cherry`` | Cherry spec plate-mount stabilizer |
| 2 | ``costar`` | Costar twin-slot stabilizer |

Combined types (cherry, costar_compat) produce a **single polygon per key**
that already includes the switch opening — the stabilizer slot is connected
to the switch cutout through a ±2.3 mm notch.  Costar produces two separate
slot polygons.  All polygons are centred on the switch centre (no Y offset).

Per-key ``_s`` codes 0-1 are accepted; code 2 and unknown values fall back
to the config default (mirroring kb_builder's ``range(2)`` check).

The plate generator requests geometry from the stabilizer rather than computing it.

---

# Reference Library

All physical dimensions are stored as immutable reference data.

Directory:

```
reference/
```

Example:

```
switch_cutouts.yaml

stabilizer_cutouts.yaml
```

Example:

```yaml
plate_cutout:

  width: 14.00

  height: 14.00

  corner_radius: 0.50

plate:

  nominal_thickness: 1.60

recommended_clearance:

  0.05
```

No production geometry should contain hardcoded dimensions copied from datasheets.

The reference files are the single source of truth.

---

# Plate Generator

The plate generator is intentionally simple.

Pseudo-code:

```
Create plate outline

For every key

    Obtain switch geometry

    Subtract switch cutout

    If stabilized

        Obtain stabilizer geometry

        Subtract stabilizer cutout

Generate mounting holes

Return CadQuery solid
```

The generator contains almost no keyboard-specific knowledge.

Its purpose is assembling geometry from reusable libraries.

---

# Plate Outline

The outline is generated independently of KLE.

Algorithm:

```
Collect switch centers

↓

Compute occupied area

↓

Expand by configurable margin

↓

Round corners

↓

Generate outline
```

The outline is therefore independent from switch cutouts.

Changing bezel width or enclosure margins must not require changing the layout.

---

# Mounting System

Mounting holes belong to the keyboard subsystem.

They should be generated from configuration rather than embedded into the enclosure.

Inputs:

* edge margin
* screw size
* minimum spacing
* plate dimensions

Outputs:

* mounting hole locations
* metadata

The enclosure generator later creates bosses that align with these holes.

---

# CadQuery Integration

The keyboard subsystem exports native CadQuery objects.

Example:

```python
plate = keyboard.generate_plate()

assembly.add(
    plate,
    Location(...)
)
```

The cyberdeck assembly can then:

* subtract recesses
* create mounting bosses
* check collisions
* compute clearances

No intermediate DXF import step is required.

---

# Metadata

The subsystem should expose structured metadata alongside geometry.

Example:

```python
KeyboardMetadata

    width

    height

    switch_centers

    mounting_points

    bounding_box

    plate_thickness
```

This information is used by the enclosure generator without re-measuring CAD geometry.

---

# Validation

Every generated plate must pass validation.

Checks include:

* no overlapping cutouts
* valid stabilizer spacing
* switch entirely inside outline
* mounting holes inside plate
* minimum edge distance
* valid plate thickness
* no duplicate keys
* supported switch family
* supported stabilizer family

Generation must fail with explicit errors rather than silently producing invalid geometry.

---

# Configuration

Example:

```yaml
keyboard:

  layout:

    source: layouts/jd40.json

  switch:

    family: mx_alps

  stabilizer:

    family: cherry

  plate:

    thickness: 1.6

    edge_margin: 6.0

    corner_radius: 8.0

  mounting:

    screw: M2

    edge_offset: 5.0
```

Changing layouts or switch families should require only configuration changes.

---

# Relationship with the Cyberdeck

The keyboard subsystem is one reusable component within the larger cyberdeck project.

```
Cyberdeck Assembly

├── Display

├── Orange Pi

├── Keyboard Plate

├── RP2040

├── Hinges

├── Enclosure

└── Fasteners
```

The keyboard knows nothing about the enclosure.

The enclosure knows only the keyboard's geometry and metadata.

This separation keeps both systems independently reusable.

---

# Guiding Principles

The following rules should be followed throughout implementation.

* Never hardcode measured dimensions in source code.
* Keep layout, geometry and assembly strictly separated.
* Every hardware family should be implemented as a replaceable module.
* Prefer immutable reference data over embedded constants.
* Produce native CadQuery geometry rather than intermediate CAD files.
* Expose metadata alongside geometry.
* Build the plate entirely from reusable switch and stabilizer libraries.
* Keep the keyboard subsystem completely independent from the cyberdeck enclosure while making its outputs straightforward to consume by the enclosure generator.

