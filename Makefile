# Cyberdeck CAD build — run inside the `cyberdeck` conda env.
#   conda activate cyberdeck   (setup: see AGENTS.md)
#   make data       # data layer only (config → components → layout → validation)
#   make all        # full CAD + exports (STEP/STL/SVG/glTF)
#   make display    # display sub-assembly only (LCD + HDMI driver, fast)
#   make base       # combined base assembly (base_bottom + keyboard + base_top)
#   make base_bottom # base bottom tray only
#   make base_top   # base top deck with keyboard cutout only
#   make lid        # combined lid assembly (lid_shell + display + lid_bezel)
#   make lid_shell   # lid rear shell tray only
#   make keyboard_plate  # bare switch plate, split into Halves
#   make lid_bezel  # lid front plate with glass cutout only
#   make hinge      # hinge only
#   make assembly   # full assembly union only
#   make components # per-component debug STLs only
#   make build TARGETS=display,base  # selected targets
#   make test       # run pytest
#   make check      # py_compile all modules
#   make clean      # remove generated files
#   make build IGNORE_VALIDATION=1   # build/export despite a failing hard
#                                     # constraint (collision, clearance,
#                                     # etc.), instead of aborting — for
#                                     # inspecting a known-bad layout while
#                                     # iterating on a fix, not for shipping
#                                     # the result. Works with `data` too.

PYTHON   ?= python
MAIN     ?= main.py
CONFIG   ?= config/default.yaml
LAYOUT   ?= compact
GENERATED ?= generated
TARGETS  ?= all
IGNORE_VALIDATION ?=

.PHONY: data all build test check clean display base base_bottom base_top lid lid_shell lid_bezel keyboard_plate hinge assembly assembly_opened components

ifneq ($(strip $(IGNORE_VALIDATION)),)
IGNORE_VALIDATION_FLAG := --ignore-validation
else
IGNORE_VALIDATION_FLAG :=
endif

data:
	$(PYTHON) $(MAIN) --config $(CONFIG) --layout $(LAYOUT) --steps data $(IGNORE_VALIDATION_FLAG)

build:
	$(PYTHON) $(MAIN) --config $(CONFIG) --layout $(LAYOUT) --steps all --targets $(TARGETS) $(IGNORE_VALIDATION_FLAG)

all: TARGETS = all
all: build

display: TARGETS = display
display: build

base: TARGETS = base
base: build

base_bottom: TARGETS = base_bottom
base_bottom: build

base_top: TARGETS = base_top
base_top: build

lid: TARGETS = lid
lid: build

lid_shell: TARGETS = lid_shell
lid_shell: build

lid_bezel: TARGETS = lid_bezel
lid_bezel: build

keyboard_plate: TARGETS = keyboard_plate
keyboard_plate: build

hinge: TARGETS = hinge
hinge: build

assembly: TARGETS = assembly
assembly: build

assembly_opened: TARGETS = assembly_opened
assembly_opened: build

components: TARGETS = components
components: build

test:
	$(PYTHON) -m pytest

check: data
	$(PYTHON) -m py_compile main.py components/*.py geometry/*.py layouts/*.py \
		assemblies/*.py case/*.py routing/*.py exports/*.py utilities/*.py \
		keyboard/*.py keyboard/*/*.py

clean:
	rm -rf $(GENERATED)/step/*.step $(GENERATED)/stl/*.stl $(GENERATED)/svg/*.svg $(GENERATED)/gltf/*.gltf
	rm -rf __pycache__ */__pycache__ */*/__pycache__
