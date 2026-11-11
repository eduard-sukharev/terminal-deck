# Cyberdeck CAD Generator – LLM Handoff Specification

This document defines the architecture, conventions, directory layout, APIs, and implementation strategy for an autonomous LLM tasked with designing a fully parametric cyberdeck in build123d (see docs/adr/0002). The intent is to minimize ambiguity and prevent the model from hardcoding dimensions or creating monolithic CAD scripts.

---

# Project Goal

Design a completely parametric **slider** cyberdeck for field debugging of 3D printers: a screen lid that slides along the face to reveal a 40% keyboard (ADR-0009).

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
* decorative cyberpunk elements (including decorative picatinny rails and antennas; the accessory rail interface is functional, not printed)

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

See `docs/form_factor.md` (form reference: the central-unit slider; the
clamshell references are retired with the clamshell, ADR-0009). Not copied.

Desired characteristics:

* slider: the screen lid slides along the face over the chassis
* closed, the device reads as one screen panel; opening reveals the keyboard
* flat face (no deck slope), compact closed face height
* flat bottom
* no palm rest
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
        rp2040_zero.py
        usb_breakout.py
        battery.py
        heatset_insert.py
        slide.py

    geometry/

        boss.py
        ribs.py
        vents.py
        cutouts.py
        seam_joint.py
        split.py
        edge_treatment.py
        printability.py
        merged_boss.py
        parting.py
        spot_search.py

    layouts/

        layout_recipe.py
        slider.py
        composer.py
        resolvers/

    assemblies/

        assembly.py

    routing/

        cable_routing.py

    case/

        chassis.py
        screen_lid.py
        slider_frame.py

    exports/

        export_step.py
        export_stl.py
        export_svg.py

    utilities/

        constants.py
        cad_helpers.py
        config_loader.py
        slider_validation.py
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
center of the chassis footprint (on the table plane)
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
Chassis shell

Screen lid shell

Bosses

Walls

Chamfers

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
wall_thickness = config.wall.thickness  # see config/default.yaml
```

Everything derives from this.

---

# Draft

The X side walls are drafted by `config.draft.angle` (5–10° from vertical).
The Tray widens from its base up to its prismatic half-band; the Deck is
prismatic all the way to the closed face. The Screen lid widens from its face
panel down to the Back plate. The two halves are therefore widest where they
meet on the closed face.

The chassis' 6 mm joint band is **prismatic on both halves** (ADR-0012), split
3 mm each side of the Parting plane: the Tray's draft stops at `band_z0`, and
the Deck carrying the keyboard Well is straight through to the face.

The Screen lid's Back plate and its Band joint are **prismatic** (ADR-0011):
the lid is at full width from `panel_outer_z` up to `band_z1`, and only the
Bezel above the band tapers to the display face. That keeps the Bezel/Back
joint in straight walls.

Only the X side walls are drafted. The front and rear end walls stay vertical:
the guide span and the rod end clamps are pinned to the 140 mm face-height
budget, and drafting them would eat that clearance.

The slide budget adds `draft_allowance` to the side pod, so the display keeps
its shell clearance as the lid cavity narrows toward the face. The guide
hardware is inboard, under the display (ADR-0013), so it no longer sets the
width; the draft inset is measured over the display's height
(`min(display back + height, lid top − front panel) − band`), not over the
hardware envelope.

---

# Edge Treatment

The case is **chamfer-first**. The look is chopped, brutal, heavy-duty
hi-tech: cut bevels, not soft rounds.

Outside faces — every edge visible on the assembled device, and every exposed
convex or bed-facing edge. When an outside edge is broken it is a 45 degree
chamfer, never a fillet: a round on an external corner softens the case toward
a consumer appliance, and on a bed-facing edge it prints as an overhang. A
sharp corner that needs no break may stay sharp — but it never becomes a
round.

Inside (concave) joints:

* Chamfer by default. The stress-relief at horizontal floor/wall, boss/wall,
  boss/floor and rib/floor joints is a 45 degree chamfer
  (`edges.chamfer_factor * wall`).

* Fillets are allowed sparingly and only on hidden inside joints, where a
  smooth relief is needed and a chamfer would leave a sharp rebate. The
  sanctioned uses are the vertical wall/wall joints in
  `geometry/edge_treatment.py` and the Seam tab corners that must nest in
  them. Never decorative, never on an outside face.

No hardcoded sizes. Every edge size is configuration:

```
corners.chamfer          # outside case corners (mm)

edges.chamfer_factor     # inside joint relief, scaled from wall.thickness

edges.bed_chamfer        # bed-face perimeter (elephant's foot)

edges.seam_convex_extra  # tab relief over the notch it nests in

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

# Slide

Separate subsystem (`components/slide.py`, `config/slide.yaml`).

Exports

```
guide rod

linear bearing

bearing clamp

travel stop

retention

drag-chain channel
```

Never integrate slide math into the enclosure. Two guide rods sit on the
screen lid's back panel, held by two printed Rod clamps each; one LM…LUU
bearing per rod is held in a printed Bearing clamp that straddles the panel and
is seated in the chassis deck. The bearing size is config data; the face-height
budget checks the chosen combination.

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

drag-chain channel

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

Minimum cable bend (drag chain)

No connector blocked

Closed lid covers the chassis

Slide travel exposes the keyboard

Slide sweep clears over the whole travel

Guide span and lid retention
```

---

# Configuration Example

See `config/*.yaml` — the config files are the source of truth; this spec
carries no example numbers.

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

Generate slide

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
* Slide (rod + bushing → rail → telescoping)
* Battery (internal Li-ion pack, implemented)
* Alternate lid designs (single panel → dual display → accessory panel)

If component interfaces remain stable, the enclosure should regenerate correctly after configuration changes with minimal or no code modifications.

