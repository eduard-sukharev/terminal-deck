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
* decorative cyberpunk elements (including decorative picatinny rails and antennas; the accessory rail itself is a functional, printed part with a MIL-STD-1913 width -- ADR-0020 -- not decoration)

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

Only the **Screen lid's** X side walls are drafted, by `config.draft.lid`
(5–10° from vertical): the lid widens from its face panel down to the Back
plate, so it is widest at the closed face.

The **Tray's X side walls are vertical** (ADR-0019): the printed accessory rail
bolts to them (ADR-0020), and a rail needs a flat, square face. The Deck is prismatic too, so
the chassis is one width from the table to the closed face and the two halves
still meet at full width. The chassis' 6 mm joint band is therefore prismatic
on both halves (ADR-0012).

The Tray's front/rear end walls are vertical as well, and they leave the table
in a **base taper** (`geometry/base_taper.py`, ADR-0019/ADR-0022/ADR-0027): a
draft that runs from the table up to the bottom of the joint band, so the slope
stops 3 mm below the Parting plane. Its reach is derived, not its angle: the
face at the table sits `side_inset` inside the wall, exactly on the long-wall
band stations' axes (~18.9° over the 13.15 mm band bottom), so the outboard
half of each access cone's mouth is cut away. The cavity follows the same line,
one wall in, so the wall keeps its thickness over the whole slope; the taper is
suppressed inside a pad at the four corner stations only, which keeps the head
recesses' ring and swallows the station columns. The cones' outside edges -- the
mouth rims at the bed and the taper-flared lips -- take the 45° chamfer of
`edges.bed_chamfer`, never a fillet (ADR-0025/ADR-0027).

The Screen lid's Back plate and its Band joint are **prismatic** (ADR-0011):
the lid is at full width from `panel_outer_z` up to `band_z1`, and only the
Bezel above the band tapers to the display face. That keeps the Bezel/Back
joint in straight walls.

The front and rear end walls stay vertical on the lid too: the guide span and
the rod end clamps are pinned to the 140 mm face-height budget, and drafting
them would eat that clearance.

The slide budget adds the lid's `draft_allowance` to the side pod, so the
display keeps its shell clearance as the lid cavity narrows toward the face. The guide
hardware is inboard, under the display (ADR-0013), so it no longer sets the
width; the draft inset is measured over the display's height
(`min(display back + height, lid top − front panel) − band`), not over the
hardware envelope.

---

# Edge Treatment

The case's edge treatment follows the **material dihedral** (ADR-0025): a
convex edge is chopped into the brutal hi-tech look with a 45 degree chamfer,
and a concave edge is rolled with a fillet, because a reentrant corner is a
crack starter. The look is chopped, brutal, heavy-duty hi-tech: cut bevels on
every edge you can see, rounds only inside the material.

Outside faces — every edge visible on the assembled device, and every exposed
convex or bed-facing edge. When an outside edge is broken it is a 45 degree
chamfer, never a fillet: a round on an external corner softens the case toward
a consumer appliance, and on a bed-facing edge it prints as an overhang. A
sharp corner that needs no break may stay sharp — but it never becomes a
round.

Inside (concave) joints:

* The material angle decides. Measure the dihedral between the two faces
  through the material: `<= 90` degrees is a convex (outside) edge, `>= 270`
  degrees is a concave (inside) edge — one square joint read from either side.
  Convex takes a chamfer, concave takes a fillet. Never the other way round,
  and the angle is the only criterion.

* A concave edge is a reentrant corner, and a reentrant corner is a crack
  starter: it gets a fillet, so the material rolls smoothly from one face into
  the other. That covers **every boss base** — a boss meets its floor, wall or
  ring at such an angle — and every other sharp inside edge of the shell:
  cavity floor/wall, wall/wall, boss/wall, boss/floor, rib/floor.

* A fillet must print the way the part is printed. Judge every joint in that
  part's own print orientation, not in the assembly's Z: the Deck prints face
  down, so its inner ceiling is the bed face and the bosses that stand on it
  take the fillet like any other boss base. A concave joint that opens toward
  the bed *of that part* keeps the 45 degree chamfer
  (`edges.chamfer_factor * wall`) — the round approaches horizontal there and
  prints as a curved overhang, while the 45 degree chamfer is the widest
  self-supporting break.

* A shell's cavity corners follow the outer chop. The outer chamfer is cut
  with a square cavity behind it and the corner pinches to nothing — for the
  shipped 4 mm chop on a 2 mm wall the cavity corner lies exactly on the
  chamfer plane. The cavity is therefore chopped by the derived
  `cad_helpers.inner_corner_chamfer(chamfer, wall)`
  (`chamfer - wall * (2 - sqrt(2))`), which puts the inner chamfer face one
  `wall` behind the outer one (ADR-0016). Never leave a knife edge at a
  chamfered corner.

* The build implements this in `geometry/edge_treatment.py` (ADR-0025): the
  concave joints it can roll are filleted — `merge_column_walls` at the
  columns and the Well bosses (ADR-0024), `fillet_boss_bases` at every boss
  base (the selector `boss_base_edges` reads the part's print orientation),
  the vertical wall/wall relief and the Seam tab corners that nest in it —
  while the horizontal joints that open toward the bed keep the 45 degree
  chamfer, and bed-facing outside edges keep `edges.bed_chamfer`. Every chord
  merge runs before any base round, so a base round beside a neighbouring
  family's chord cannot block it. A round that does not fit is skipped with a
  SOFT warning; the build never blocks on OCC.

No hardcoded sizes. Every edge size is configuration:

```
corners.chamfer          # outside case corners (mm)

edges.chamfer_factor     # inside joint relief where a fillet would bridge

chassis_joint.column_fillet  # boss-base and column/wall merge fillet (mm)

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

