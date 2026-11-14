# Cyberdeck CAD build. Every Python target runs inside the `cyberdeck` conda
# env via `conda run`, so no manual `conda activate` is needed.
#   make env        # create the env (python 3.12 + requirements-dev.txt) if missing
#   make data       # data layer only (config → components → layout → validation)
#   make all        # full CAD + exports (STEP/STL/SVG/glTF)
#   make display    # display sub-assembly only (LCD + HDMI driver, fast)
#   make chassis    # chassis shell + keyboard/SBC/controller AND its cuts
#                   #   (Tray/Deck and their left/right Sections)
#   make screen_lid # screen-lid shell + display + driver AND its cuts
#                   #   (Bezel/Back and their left/right Sections)
#   make slide      # guide rods + LM...LUU bearings
#   make keyboard_plate  # bare switch plate AND its left/right Sections
#   make assembly   # closed assembly
#   make assembly_opened  # open pose (lid slid by the travel)
#   make components # per-component debug STLs only
#   make build TARGETS=assembly,chassis  # selected targets
#   make test       # run pytest
#   make check      # py_compile all modules
#   make render     # SVG (keyboard plate) + PNG previews of generated STLs
#   make render_svg # keyboard plate SVG -> generated/svg/plate_top.svg
#   make render_stl # shaded PNG per generated STL -> generated/png/
#   make verify     # check that expected STEP/STL/SVG/glTF artifacts exist and are non-empty
#   make clean      # remove generated files
#   make env-remove # delete the conda env
#   make build IGNORE_VALIDATION=1   # build/export despite a failing hard
#                                     # constraint (collision, clearance,
#                                     # etc.), instead of aborting — for
#                                     # inspecting a known-bad layout while
#                                     # iterating on a fix, not for shipping
#                                     # the result. Works with `data` too.

ENV_NAME ?= cyberdeck
PY_VERSION ?= 3.12
CONDA    ?= conda
# `conda run` activates $(ENV_NAME) for the command; --no-capture-output streams logs live.
PYTHON   ?= $(CONDA) run --no-capture-output -n $(ENV_NAME) python
MAIN     ?= main.py
CONFIG   ?= config/default.yaml
LAYOUT   ?= slider
GENERATED ?= generated
PLATE_LAYOUT ?= keyboard/layouts/jd40.json
RENDER_ELEV ?= 45
RENDER_AZIM ?= -90
TARGETS  ?= all
IGNORE_VALIDATION ?=

# Convenience targets ship the whole part AND its printable cuts, matching what
# `make all` produces for that sub-assembly (ADR-0015): the shell, its left/right
# reference halves, and each real Section.
CHASSIS_TARGETS  := chassis,chassis_left,chassis_right,chassis_tray,chassis_tray_left,chassis_tray_right,chassis_deck,chassis_deck_left,chassis_deck_right
LID_TARGETS      := screen_lid,screen_lid_left,screen_lid_right,screen_lid_bezel,screen_lid_bezel_left,screen_lid_bezel_right,screen_lid_back,screen_lid_back_left,screen_lid_back_right
PLATE_TARGETS    := keyboard_plate,keyboard_plate_left,keyboard_plate_right

.PHONY: env env-remove render render_svg render_stl verify data data-slider slider all build test check clean display chassis screen_lid slide keyboard_plate assembly assembly_opened components

ifneq ($(strip $(IGNORE_VALIDATION)),)
IGNORE_VALIDATION_FLAG := --ignore-validation
else
IGNORE_VALIDATION_FLAG :=
endif

# Create the conda env only if it does not exist; stamp re-runs pip when requirements change.
env: .env-stamp

.env-stamp: requirements.txt requirements-dev.txt
	@$(CONDA) env list | awk '{print $$1}' | grep -qx '$(ENV_NAME)' \
		|| $(CONDA) create -y -n $(ENV_NAME) python=$(PY_VERSION)
	$(CONDA) run --no-capture-output -n $(ENV_NAME) python -m pip install -r requirements-dev.txt
	@touch $@

env-remove:
	$(CONDA) env remove -y -n $(ENV_NAME)
	rm -f .env-stamp

# Every target that runs Python needs the env.
data build test check render_svg render_stl: env

data:
	$(PYTHON) $(MAIN) --config $(CONFIG) --layout $(LAYOUT) --steps data $(IGNORE_VALIDATION_FLAG)

# Explicit slider data stage (same as the default).
data-slider:
	$(PYTHON) $(MAIN) --config $(CONFIG) --layout slider --steps data $(IGNORE_VALIDATION_FLAG)

# Slider CAD + exports (first-generation shell).
slider:
	$(PYTHON) $(MAIN) --config $(CONFIG) --layout slider --steps all --targets $(TARGETS) $(IGNORE_VALIDATION_FLAG)

build:
	$(PYTHON) $(MAIN) --config $(CONFIG) --layout $(LAYOUT) --steps all --targets $(TARGETS) $(IGNORE_VALIDATION_FLAG)

all: TARGETS = all
all: build

display: TARGETS = display
display: build

chassis: TARGETS = $(CHASSIS_TARGETS)
chassis: build

screen_lid: TARGETS = $(LID_TARGETS)
screen_lid: build

slide: TARGETS = slide
slide: build

keyboard_plate: TARGETS = $(PLATE_TARGETS)
keyboard_plate: build

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

render: render_svg render_stl

render_svg:
	@mkdir -p $(GENERATED)/svg
	$(PYTHON) utilities/render_plate_svg.py --layout $(PLATE_LAYOUT) -o $(GENERATED)/svg/plate_top.svg

# Shaded PNG preview of every generated STL (run `make all` first).
render_stl:
	@mkdir -p $(GENERATED)/png
	@set -e; found=0; for f in $(GENERATED)/stl/cyberdeck_*.stl; do \
		[ -e "$$f" ] || continue; found=1; \
		$(PYTHON) utilities/render_stl.py $$f -o $(GENERATED)/png/$$(basename $$f .stl).png \
			--elev $(RENDER_ELEV) --azim $(RENDER_AZIM); \
	done; \
	[ $$found = 1 ] || { echo "no STLs in $(GENERATED)/stl - run 'make all' first"; exit 1; }

# Fail if any of the four export formats is missing/empty for a built part.
verify:
	@set -e; bad=0; \
	for ext in step stl gltf; do \
		n=$$(find $(GENERATED)/$$ext -name "cyberdeck_*.$$ext" -size +0 2>/dev/null | wc -l); \
		echo "$$ext: $$n files"; [ $$n -gt 0 ] || bad=1; \
	done; \
	for f in $$(find $(GENERATED) -type f \( -name '*.step' -o -name '*.stl' -o -name '*.svg' -o -name '*.gltf' \) -empty); do \
		echo "EMPTY: $$f"; bad=1; \
	done; \
	[ $$bad = 0 ] && echo "artifacts OK" || { echo "artifact check FAILED"; exit 1; }

clean:
	rm -rf $(GENERATED)/step/*.step $(GENERATED)/stl/*.stl $(GENERATED)/svg/*.svg $(GENERATED)/gltf/*.gltf
	rm -rf $(GENERATED)/png
	rm -rf __pycache__ */__pycache__ */*/__pycache__
