# Cyberdeck CAD build — run after activating the miniforge environment.
#   source $HOME/miniforge/bin/activate
#   make data       # data layer only (config → components → layout → validation)
#   make all        # full CAD + exports (STEP/STL/SVG)
#   make display    # display sub-assembly only (LCD + HDMI driver, fast)
#   make base       # base shell only
#   make lid        # combined lid assembly (lid_base + display + lid_bezel)
#   make lid_base   # lid rear shell tray only
#   make lid_bezel  # lid front plate with glass cutout only
#   make hinge      # hinge only
#   make assembly   # full assembly union only
#   make components # per-component debug STLs only
#   make build TARGETS=display,base  # selected targets
#   make test       # run pytest
#   make check      # py_compile all modules
#   make clean      # remove generated files

PYTHON   ?= python
MAIN     ?= main.py
CONFIG   ?= config/default.yaml
LAYOUT   ?= default
GENERATED ?= generated
TARGETS  ?= all

.PHONY: data all build test check clean display base lid lid_base lid_bezel hinge assembly components

data:
	$(PYTHON) $(MAIN) --config $(CONFIG) --layout $(LAYOUT) --steps data

build:
	$(PYTHON) $(MAIN) --config $(CONFIG) --layout $(LAYOUT) --steps all --targets $(TARGETS)

all: TARGETS = all
all: build

display: TARGETS = display
display: build

base: TARGETS = base
base: build

lid: TARGETS = lid
lid: build

lid_base: TARGETS = lid_base
lid_base: build

lid_bezel: TARGETS = lid_bezel
lid_bezel: build

hinge: TARGETS = hinge
hinge: build

assembly: TARGETS = assembly
assembly: build

components: TARGETS = components
components: build

test:
	$(PYTHON) -m pytest

check: data
	$(PYTHON) -m py_compile main.py components/*.py geometry/*.py layouts/*.py \
		assemblies/*.py case/*.py routing/*.py exports/*.py utilities/*.py \
		keyboard/*.py keyboard/*/*.py

clean:
	rm -rf $(GENERATED)/step/*.step $(GENERATED)/stl/*.stl $(GENERATED)/svg/*.svg
	rm -rf __pycache__ */__pycache__ */*/__pycache__
