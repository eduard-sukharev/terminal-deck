# Move to build123d; port Core components, rebuild case parts from scratch

CadQuery is being replaced by build123d. Core components (SBC, USB hub,
battery cells, display panel, driver, controller, keyboard plate) are ported
and checked against `tests/data/baseline_metrics.json`. Case parts (Tray,
Deck, Lid shell, Bezel, hinge geometry) are *not* ported: the form factor
changed (MobilePro 900 / Jornada P6 reference, Visor, Well, split Halves), so
they are rewritten in build123d against the new spec, and the CadQuery
versions are deleted once the new ones pass validation. The layout/constraint
system, validation, fasteners, hinge math, cable routing and keyboard
subsystem are kept.
