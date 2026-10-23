"""Golden-master geometry regression test.

Rebuilds every CAD target through the real pipeline (``main.py --metrics``)
and compares volume / bounding box / center of mass against a recorded
baseline (``tests/data/baseline_metrics.json``). This is the safety net for
refactors that touch geometry code without meaning to change any geometry —
most notably the CadQuery -> build123d port (see AGENTS.md) — since nothing
else in the suite ever builds a solid.

The baseline was recorded on ``main`` at commit a1a273e with:

    python main.py --config config/default.yaml --layout compact \
        --steps all --targets all --metrics tests/data/baseline_metrics.json

Re-record it (deliberately, when a geometry change is intended) the same way.

It was re-recorded for the ADR 0003/0004 case redesign (Sections, Parting
plane, Deck columns, Seam fastening, Merged bosses, edge treatment, friction
hinge): every case target changed, the Core components did not.

The five ``component_*`` bounding boxes were updated after the build123d port:
volume and center of mass still matched to 1e-6, but build123d measures a
tighter box than CadQuery did (CadQuery padded by shape tolerance, ~0.0005 mm,
and over-estimated the spline-lofted keycaps by ~0.7 mm). Every other value is
unchanged from the CadQuery recording.

Keycaps were later simplified to 10-face chamfered lofts (``components/keycap_set``),
so the four keyboard-containing targets (``component_keyboard``, ``base``,
``assembly``, ``assembly_opened``) were re-recorded; each gained the same
5553.7 mm^3 and no other target moved.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from utilities import cad_helpers

REPO_ROOT = Path(__file__).resolve().parent.parent
BASELINE_PATH = REPO_ROOT / "tests" / "data" / "baseline_metrics.json"

# Relative tolerance for volume/bbox/center-of-mass comparisons. Tight enough
# to catch a dropped feature or a wrong translate, loose enough to tolerate
# floating point noise from a different boolean operation ordering.
REL_TOL = 1e-6
# Absolute tolerance floor for near-zero values (e.g. a center-of-mass
# component that should be ~0 on a symmetric part) where relative tolerance
# alone is meaningless.
ABS_TOL = 1e-9


def _rel_close(a: float, b: float) -> bool:
    return abs(a - b) <= max(REL_TOL * max(abs(a), abs(b)), ABS_TOL)


@pytest.fixture(scope="module")
def rebuilt_metrics(tmp_path_factory) -> dict:
    if not cad_helpers.cad_available():
        pytest.skip("build123d not available in this environment")
    out_path = tmp_path_factory.mktemp("metrics") / "rebuilt_metrics.json"
    result = subprocess.run(
        [
            sys.executable, "main.py",
            "--config", "config/default.yaml",
            "--layout", "compact",
            "--steps", "all",
            "--targets", "all",
            "--metrics", str(out_path),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"pipeline build failed (exit {result.returncode})\n"
        f"stdout:\n{result.stdout[-4000:]}\nstderr:\n{result.stderr[-4000:]}"
    )
    return json.loads(out_path.read_text())


@pytest.fixture(scope="module")
def baseline_metrics() -> dict:
    if not BASELINE_PATH.exists():
        pytest.skip(f"no baseline recorded at {BASELINE_PATH}")
    return json.loads(BASELINE_PATH.read_text())


#: Sections per split part (ADR 0003), left to right.
SECTIONS = {
    "base_bottom": ("left", "center", "right"),
    "base_top": ("left", "right"),
    "lid_shell": ("left", "center", "right"),
    "lid_bezel": ("left", "right"),
    "keyboard_plate": ("left", "right"),
}
BUILD_BED = (220.0, 220.0)
BUILD_HEIGHT = 256.0


def _section_names():
    return [f"{part}_{s}" for part, names in SECTIONS.items() for s in names]


def test_every_part_is_split_into_its_sections(rebuilt_metrics):
    info = rebuilt_metrics["_pipeline"]["sections"]
    for part, names in SECTIONS.items():
        assert info[part]["sections"] == len(names), part


def test_every_section_is_one_connected_solid(rebuilt_metrics):
    for name in _section_names():
        assert rebuilt_metrics[name]["n_solids"] == 1, name


def test_every_section_fits_the_build_volume(rebuilt_metrics):
    for name in _section_names() + ["base_knuckle"]:
        x, y, z = rebuilt_metrics[name]["bbox"]
        assert sorted((x, y)) <= sorted(BUILD_BED), f"{name} footprint {x} x {y}"
        assert z <= BUILD_HEIGHT


def test_sections_rejoin_to_their_part(rebuilt_metrics):
    # Checked on the untreated split (edge treatment follows it, see main.py).
    for part, info in rebuilt_metrics["_pipeline"]["sections"].items():
        assert info["rejoin"], part


def test_every_section_declares_an_orientation_and_has_a_bed_face(rebuilt_metrics):
    pipe = rebuilt_metrics["_pipeline"]
    for name in _section_names():
        assert pipe["print_orientation"][name] == [0.0, 0.0, -1.0], name
        assert pipe["bed_face_mm2"][name] > 0.0, name


def test_screw_counts(rebuilt_metrics):
    screws = rebuilt_metrics["_pipeline"]["screws"]
    assert screws["plate"] == 8
    assert screws["bezel"] == 8
    assert screws["deck"] >= 2
    assert screws["hinge_bolts"] == 2
    assert screws["hinge_flange"] >= 1


def test_no_hard_check_fails(rebuilt_metrics):
    pipe = rebuilt_metrics["_pipeline"]
    assert pipe["hard_failures"] == 0
    assert all(pipe["checks"].values()), [k for k, v in pipe["checks"].items() if not v]


def test_baseline_covers_expected_targets(baseline_metrics):
    # A quick canary: the baseline should at minimum cover every top-level
    # case/lid/assembly target. If this shrinks, the baseline is stale.
    expected = {
        "assembly", "assembly_opened", "base", "base_bottom", "base_top",
        "base_knuckle", "display", "hinge", "lid", "lid_shell", "lid_bezel",
    }
    missing = expected - set(baseline_metrics)
    assert not missing, f"baseline is missing targets: {sorted(missing)}"


def test_geometry_matches_baseline(rebuilt_metrics, baseline_metrics):
    # "_pipeline" holds pipeline results, not shape metrics (see the tests above).
    baseline_metrics = {k: v for k, v in baseline_metrics.items() if not k.startswith("_")}
    missing = set(baseline_metrics) - set(rebuilt_metrics)
    extra = set(rebuilt_metrics) - set(baseline_metrics)
    assert not missing, f"targets missing from rebuild: {sorted(missing)}"
    # New targets are fine (e.g. a newly added component); only regressions
    # in existing ones fail the test.
    if extra:
        print(f"[geometry regression] note: new targets not in baseline: {sorted(extra)}")

    failures = []
    for name, base in baseline_metrics.items():
        got = rebuilt_metrics[name]
        if not _rel_close(got["volume"], base["volume"]):
            failures.append(
                f"{name}: volume {got['volume']!r} != baseline {base['volume']!r}"
            )
        for axis, label in enumerate(("x", "y", "z")):
            if not _rel_close(got["bbox"][axis], base["bbox"][axis]):
                failures.append(
                    f"{name}: bbox.{label} {got['bbox'][axis]!r} != "
                    f"baseline {base['bbox'][axis]!r}"
                )
            if not _rel_close(got["com"][axis], base["com"][axis]):
                failures.append(
                    f"{name}: com.{label} {got['com'][axis]!r} != "
                    f"baseline {base['com'][axis]!r}"
                )
        # Face count can legitimately shift with boolean ordering without the
        # solid itself changing — warn only, never fail on it.
        if got["n_faces"] != base["n_faces"]:
            print(
                f"[geometry regression] note: {name} face count changed "
                f"{base['n_faces']} -> {got['n_faces']} (volume/bbox/com "
                "unaffected)"
            )

    assert not failures, "geometry drift detected:\n" + "\n".join(failures)
