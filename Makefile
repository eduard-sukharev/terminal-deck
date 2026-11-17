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
#   make chassis_tray       # one chassis piece AND its left/right Sections
#   make chassis_deck       #   (neither builds the screen lid)
#   make screen_lid_bezel   # one lid piece AND its left/right Sections
#   make screen_lid_back    #   (neither builds the chassis)
#   make slide      # guide rods + LM...LUU bearings
#   make keyboard_plate  # bare switch plate AND its left/right Sections
#   make assembly   # closed assembly
#   make assembly_opened  # open pose (lid slid by the travel)
#   make components # per-component debug STLs only
#   make build TARGETS=assembly,chassis  # selected targets
#
# Builds are incremental: every target is fingerprinted from its inputs (the
# pipeline sources, the config tree, the layout recipe and the modules that
# build that piece) and its exports are reused when nothing moved. Editing one
# piece rebuilds that piece and the assemblies that embed it, nothing else;
# `make all` with no changes takes seconds. The cache lives in
# generated/.build-cache.json; `make rebuild` ignores it and `make clean`
# removes it.
#   make rebuild    # force a full rebuild of $(TARGETS), ignoring the cache
#   make build NO_CACHE=1  # same, per invocation
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
#
# Every Python target is quiet by default: only errors and warnings are
# printed, so a fully passing run is silent (exit code 0). Pass VERBOSE=1
# (e.g. `make all VERBOSE=1`, `make test VERBOSE=1`) for the full output —
# per-check report lines, per-target export lines, pytest -v.

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
NO_CACHE ?=
VERBOSE  ?=
CACHE_FILE ?= .build-cache.json

# VERBOSE=1 forwards --verbose to main.py/render scripts and -v to pytest;
# without it the build is quiet (errors and warnings only).
VERBOSE_FLAG = $(if $(strip $(VERBOSE)),--verbose,)
PYTEST_FLAGS = $(if $(strip $(VERBOSE)),-v,-q)

# Convenience targets ship the whole part AND its printable cuts, matching what
# `make all` produces for that sub-assembly (ADR-0015): the shell, its left/right
# reference halves, and each real Section. `chassis` and `screen_lid` are
# disjoint sets, so either half rebuilds without touching the other; the
# per-piece targets (`chassis_tray`, `chassis_deck`, `screen_lid_bezel`,
# `screen_lid_back`) go one level finer, again with their own Sections.
TRAY_TARGETS     := chassis_tray,chassis_tray_left,chassis_tray_right
DECK_TARGETS     := chassis_deck,chassis_deck_left,chassis_deck_right
BEZEL_TARGETS    := screen_lid_bezel,screen_lid_bezel_left,screen_lid_bezel_right
BACK_TARGETS     := screen_lid_back,screen_lid_back_left,screen_lid_back_right
CHASSIS_TARGETS  := chassis,chassis_left,chassis_right,$(TRAY_TARGETS),$(DECK_TARGETS)
LID_TARGETS      := screen_lid,screen_lid_left,screen_lid_right,$(BEZEL_TARGETS),$(BACK_TARGETS)
PLATE_TARGETS    := keyboard_plate,keyboard_plate_left,keyboard_plate_right

.PHONY: env env-remove render render_svg render_stl verify data all build rebuild test check clean display chassis chassis_tray chassis_deck screen_lid screen_lid_bezel screen_lid_back slide keyboard_plate assembly assembly_opened components

ifneq ($(strip $(IGNORE_VALIDATION)),)
IGNORE_VALIDATION_FLAG := --ignore-validation
else
IGNORE_VALIDATION_FLAG :=
endif

# Recursive on purpose: `rebuild` sets NO_CACHE as a target-specific variable,
# which only an expanded-at-recipe-time reference picks up.
NO_CACHE_FLAG = $(if $(strip $(NO_CACHE)),--no-cache,)

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
	$(PYTHON) $(MAIN) --config $(CONFIG) --layout $(LAYOUT) --steps data $(IGNORE_VALIDATION_FLAG) $(VERBOSE_FLAG)

# One shared recipe: the convenience targets below assign TARGETS per goal and
# run it themselves. A common `build` prerequisite would be made only once, so
# `make chassis screen_lid` would silently skip the second target.
define BUILD_CMD
$(PYTHON) $(MAIN) --config $(CONFIG) --layout $(LAYOUT) --steps all --targets $(TARGETS) $(IGNORE_VALIDATION_FLAG) $(NO_CACHE_FLAG) $(VERBOSE_FLAG)
endef

build:
	$(BUILD_CMD)

# Force a full rebuild of $(TARGETS) (or `make rebuild TARGETS=chassis`).
rebuild: NO_CACHE = 1
rebuild: build

all: TARGETS = all
all: env
	$(BUILD_CMD)

display: TARGETS = display
display: env
	$(BUILD_CMD)

chassis: TARGETS = $(CHASSIS_TARGETS)
chassis: env
	$(BUILD_CMD)

chassis_tray: TARGETS = $(TRAY_TARGETS)
chassis_tray: env
	$(BUILD_CMD)

chassis_deck: TARGETS = $(DECK_TARGETS)
chassis_deck: env
	$(BUILD_CMD)

screen_lid: TARGETS = $(LID_TARGETS)
screen_lid: env
	$(BUILD_CMD)

screen_lid_bezel: TARGETS = $(BEZEL_TARGETS)
screen_lid_bezel: env
	$(BUILD_CMD)

screen_lid_back: TARGETS = $(BACK_TARGETS)
screen_lid_back: env
	$(BUILD_CMD)

slide: TARGETS = slide
slide: env
	$(BUILD_CMD)

keyboard_plate: TARGETS = $(PLATE_TARGETS)
keyboard_plate: env
	$(BUILD_CMD)

assembly: TARGETS = assembly
assembly: env
	$(BUILD_CMD)

assembly_opened: TARGETS = assembly_opened
assembly_opened: env
	$(BUILD_CMD)

components: TARGETS = components
components: env
	$(BUILD_CMD)

test:
	$(PYTHON) -m pytest $(PYTEST_FLAGS)

check: data
	$(PYTHON) -m py_compile main.py components/*.py geometry/*.py layouts/*.py \
		assemblies/*.py case/*.py routing/*.py exports/*.py utilities/*.py \
		keyboard/*.py keyboard/*/*.py

render: render_svg render_stl

render_svg:
	@mkdir -p $(GENERATED)/svg
	$(PYTHON) utilities/render_plate_svg.py --layout $(PLATE_LAYOUT) -o $(GENERATED)/svg/plate_top.svg $(VERBOSE_FLAG)

# Shaded PNG preview of every generated STL (run `make all` first).
render_stl:
	@mkdir -p $(GENERATED)/png
	@set -e; found=0; for f in $(GENERATED)/stl/cyberdeck_*.stl; do \
		[ -e "$$f" ] || continue; found=1; \
		$(PYTHON) utilities/render_stl.py $$f -o $(GENERATED)/png/$$(basename $$f .stl).png \
			--elev $(RENDER_ELEV) --azim $(RENDER_AZIM) $(VERBOSE_FLAG); \
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
	rm -f $(GENERATED)/$(CACHE_FILE)
	rm -rf $(GENERATED)/png
	rm -rf __pycache__ */__pycache__ */*/__pycache__
