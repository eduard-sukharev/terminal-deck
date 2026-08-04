# Cyberdeck CAD Generator – LLM Handoff Specification

This document defines the architecture, conventions, directory layout, APIs, and implementation strategy for an autonomous LLM tasked with designing a fully parametric cyberdeck in CadQuery. The intent is to minimize ambiguity and prevent the model from hardcoding dimensions or creating monolithic CAD scripts.

---

# Project Goal

Design a completely parametric clamshell cyberdeck for field debugging of 3D printers.

Primary use cases:

* Linux terminal
* minicom
* SSH
* tmux
* AI agent harnesses
* Git
* Local documentation
* Printer firmware flashing

The device is **not** intended to be a maker platform.

Avoid:

* GPIO projects
* sensors
* LEDs everywhere
* Meshtastic
* SDR
* decorative cyberpunk elements

Priorities:

* robust
* serviceable
* printable
* parametric
* reusable

---

# Target Hardware

## SBC

Orange Pi Zero 2W

Needs:

* USB
* HDMI
* WiFi
* USB-C power

---

## Display

8.8"

1920×480

HDMI driver board

---

## Keyboard

40%

Cherry MX compatible

XDA profile keycaps

RP2040 controller

QMK/Vial firmware

---

## Case Style

Inspired by:

* Micro Journal Rev2
* Micro Journal Rev2 Revamp
* Micro Journal Rev8

But **NOT** copied.

Desired characteristics:

* clamshell
* compact
* flat bottom
* large palm rest
* minimal bezel
* easily printable

---

# Fundamental Design Philosophy

Never write CAD directly around dimensions.

Instead:

```
Component
↓

Placement

↓

Assembly

↓

Enclosure

↓

Features

↓

Export
```

Everything must derive from reusable components.

---

# Repository Layout

```
cyberdeck/

    README.md

    requirements.txt

    pyproject.toml

    config/

        default.yaml
        display.yaml
        keyboard.yaml
        hardware.yaml

    components/

        orange_pi_zero2w.py
        display_88.py
        hdmi_driver.py
        rp2040_keyboard.py
        usb_breakout.py
        heatset_insert.py
        hinge.py

    geometry/

        boss.py
        fillet.py
        shell.py
        ribs.py
        vents.py
        cutouts.py

    layouts/

        layout_default.py
        layout_compact.py

    assemblies/

        assembly.py

    case/

        base.py
        lid.py

    exports/

        export_step.py
        export_stl.py
        export_svg.py

    utilities/

        constants.py
        cq_helpers.py
        validation.py

    generated/

        step/
        stl/
        svg/

    docs/

        coordinate_system.md
        component_spec.md
        cad_api.md
```

---

# Coordinate System

All components must follow one coordinate convention.

```
+X → right

+Y → forward

+Z → upward
```

Origin:

```
center of base
```

Never redefine origins.

---

# Units

Always millimeters.

Never inches.

---

# Component API

Every hardware component exports the same interface.

Example:

```python
class Component:

    name: str

    size()

    mounting_holes()

    connectors()

    keepout()

    reference_origin()

    build()
```

This keeps all placement generic.

---

# Bounding Box

Every component returns:

```python
BoundingBox(

    width,

    depth,

    height
)
```

Never estimate.

Always measured.

---

# Mounting Holes

Return

```python
[
    Hole(
        x,
        y,
        diameter
    )
]
```

Coordinates relative to component origin.

---

# Connector Definition

Each connector exposes:

```python
Connector(

    type,

    x,

    y,

    z,

    direction,

    width,

    height,

    depth
)
```

Example

```
USB-C

HDMI

USB-A

Ethernet

Audio

MicroSD
```

---

# Keep-Out Volume

Every component exports:

```python
Keepout(

    width,

    depth,

    height
)
```

Used to avoid collisions.

---

# Component Example

```python
class OrangePiZero2W(Component):

    name = "Orange Pi Zero 2W"

    size():

        return BoundingBox(
            60,
            53,
            14
        )

    mounting_holes():

        return [

            Hole(...),

            Hole(...),

            Hole(...),

            Hole(...)
        ]

    connectors():

        return [

            HDMI(),

            USB(),

            Power()
        ]
```

---

# Layout Engine

The layout contains **NO CAD**.

Only placements.

Example

```python
layout.place(

    display,

    x=0,

    y=120,

    rotation=0
)

layout.place(

    keyboard,

    x=0,

    y=20,

    rotation=0
)
```

---

# Assembly

Assembly resolves:

* collisions

* cable clearance

* connector accessibility

* mounting bosses

* enclosure size

---

# Enclosure Generator

Input:

```
Placed components
```

Output:

```
Base shell

Lid shell

Bosses

Walls

Fillets

Cutouts
```

---

# CAD Rules

Never:

```
box(220,120,20)
```

Instead:

```
overall_width()

overall_depth()

overall_height()
```

---

# Wall Thickness

Single parameter.

```
wall_thickness = 2.5
```

Everything derives from this.

---

# Fillets

No hardcoded radii.

```
edge_radius

corner_radius

```

---

# Boss Generator

Input

```
hole diameter

screw size

insert type

wall thickness
```

Output

```
boss
```

Reusable.

---

# Heat Inserts

Dedicated module.

```
HeatInsert

outside diameter

depth

clearance
```

Never recreate manually.

---

# Screw Library

Single file.

```
M2

M2.5

M3
```

Contains:

```
pilot hole

clearance

head diameter

head depth
```

---

# Hinges

Separate subsystem.

Exports

```
left hinge

right hinge

pin

wire tunnel

rotation stop
```

Never integrate hinge math into enclosure.

---

# Cable Routing

Dedicated routing engine.

Tracks

```
HDMI

USB

power
```

Outputs

```
minimum bend radius

clearance tunnel
```

---

# Keyboard Plate

Separate CAD file.

Exports

```
plate

switch cutouts

mounting holes

stabilizers
```

Independent of enclosure.

---

# Display Module

Exports

```
LCD

driver PCB

mounts

bezel

glass recess
```

Never assume display PCB is centered.

---

# Cutout Generator

Consumes connector definitions.

Produces

```
USB holes

HDMI hole

SD slot

audio slot

vents
```

---

# Fastener Library

One module.

```
Screw

Insert

Nut trap

Washer recess
```

Reusable.

---

# Validation

Every build runs:

```
No collisions

No floating bosses

Minimum wall thickness

Minimum screw clearance

Minimum cable bend

No connector blocked

Lid closes

Hinge clears
```

---

# Configuration Example

```yaml
wall:
  thickness: 2.5

corners:
  radius: 8

display:

  width: 219.52

  height: 54.88

  thickness: 5.6

keyboard:

  columns: 12

  rows: 4

hinge:

  diameter: 10

  pin: 3

clearance:

  shell: 0.35

  insert: 0.2
```

---

# Build Pipeline

```
Load configuration

↓

Load components

↓

Place layout

↓

Validate placement

↓

Generate enclosure

↓

Generate bosses

↓

Generate hinge

↓

Generate cutouts

↓

Generate ribs

↓

Export STEP

↓

Export STL

↓

Export SVG

↓

Run validation
```

---

# Coding Standards

Every dimension must originate from:

* configuration
* measured component
* calculated geometry

Never from intuition.

No duplicated dimensions.

No magic numbers.

Functions should be short (<100 lines), pure where possible, and heavily documented with units and assumptions.

---

# Future Expansion

The architecture should support replacing any major module without modifying unrelated code:

* SBC (Orange Pi → Raspberry Pi CM5 → Radxa)
* Display (8.8" ultrawide → 7" 16:10 → 10.1")
* Keyboard (40% → 60% → split)
* Hinge (barrel → torque → friction)
* Battery (external only → internal Li-ion pack)
* Alternate lid designs (single panel → dual display → accessory panel)

If component interfaces remain stable, the enclosure should regenerate correctly after configuration changes with minimal or no code modifications.

