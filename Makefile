# Cyberdeck CAD build — run after activating the miniforge environment.
#   source $HOME/miniforge/bin/activate
#   make data       # data layer only (config → components → layout → validation)
#   make all        # full CAD + exports (STEP/STL/SVG)
#   make test       # run pytest
#   make check      # py_compile all modules
#   make clean      # remove generated files

PYTHON   ?= python
MAIN     ?= main.py
CONFIG   ?= config/default.yaml
LAYOUT   ?= default
GENERATED ?= generated

.PHONY: data all test check clean

data:
	$(PYTHON) $(MAIN) --config $(CONFIG) --layout $(LAYOUT) --steps data

all:
	$(PYTHON) $(MAIN) --config $(CONFIG) --layout $(LAYOUT) --steps all

test:
	$(PYTHON) -m pytest

check: data
	$(PYTHON) -m py_compile main.py components/*.py geometry/*.py layouts/*.py \
		assemblies/*.py case/*.py routing/*.py exports/*.py utilities/*.py \
		keyboard/*.py keyboard/*/*.py

clean:
	rm -rf $(GENERATED)/step/*.step $(GENERATED)/stl/*.stl $(GENERATED)/svg/*.svg
	rm -rf __pycache__ */__pycache__ */*/__pycache__
