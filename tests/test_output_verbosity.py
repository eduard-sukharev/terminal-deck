"""Quiet-by-default output: reports and the data pipeline.

By default the build prints only errors, warnings and one summary line per
report; the per-check detail appears with ``--verbose`` / ``VERBOSE=1``.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

from layouts.composer import ConstraintReport, ConstraintResult
from layouts.constraints import Constraint
from utilities.validation import ValidationReport

REPO_ROOT = Path(__file__).resolve().parent.parent


def _report() -> ValidationReport:
    report = ValidationReport()
    report.add("no-collisions", True, "")
    report.add("lid-closes", True, "component_z=56.4")
    report.add("minimum-wall-thickness", False, "wall_thickness=1.0")
    report.add("minimum-cable-bend", True, "bend_radius=0.0")
    report.goals["front_margin"] = 7.65
    report.warn("a soft finding")
    return report


def test_quiet_summary_keeps_header_failures_and_warnings():
    text = _report().summary(verbose=False)
    lines = text.splitlines()
    assert lines[0] == "4 checks: FAIL"
    # Passed checks are hidden in quiet mode…
    assert "[ok  ]" not in text
    assert "no-collisions" not in text
    # …but FAIL lines, warnings and the header always show.
    assert "[FAIL] minimum-wall-thickness: wall_thickness=1.0" in text
    assert "[warn] a soft finding" in text


def test_verbose_summary_shows_every_check_and_goals():
    text = _report().summary(verbose=True)
    assert "[ok  ] no-collisions: " in text
    assert "[ok  ] lid-closes: component_z=56.4" in text
    assert "[FAIL] minimum-wall-thickness: wall_thickness=1.0" in text
    assert "[goal] front_margin: 7.65" in text
    assert "[warn] a soft finding" in text


def test_all_pass_quiet_summary_is_a_single_line():
    report = ValidationReport()
    report.add("no-collisions", True, "")
    report.add("lid-closes", True, "")
    assert report.summary(verbose=False) == "2 checks: PASS"
    assert "2 checks: PASS" in report.summary(verbose=False).splitlines()[0]


def _creport() -> ConstraintReport:
    report = ConstraintReport()
    report.results.append(
        ConstraintResult(constraint=Constraint(), satisfied=True, message="ok")
    )
    report.results.append(
        ConstraintResult(
            constraint=Constraint(), satisfied=False, message="overlap"
        )
    )
    return report


def test_constraint_report_quiet_and_verbose():
    quiet = _creport().summary(verbose=False)
    assert quiet.splitlines()[0] == "2 constraints: FAIL"
    assert "[ok  ]" not in quiet
    assert "[FAIL] constraint: overlap" in quiet
    verbose = _creport().summary(verbose=True)
    assert "[ok  ] constraint: ok" in verbose


def test_data_stage_is_quiet_by_default_and_verbose_with_flag():
    def run_data(*extra: str) -> str:
        result = subprocess.run(
            [sys.executable, "main.py", "--steps", "data", *extra],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=180,
        )
        assert result.returncode == 0, result.stderr
        return result.stdout

    quiet = run_data()
    # A fully passing run prints no per-report PASS headers…
    assert "checks: PASS" not in quiet
    assert "constraints: PASS" not in quiet
    assert "slide budget" not in quiet
    # …and no per-check detail.
    assert "[ok  ]" not in quiet
    # Warnings stay visible.
    assert "[warn]" in quiet

    verbose = run_data("--verbose")
    assert re.search(r"placement validation:\n\d+ checks: PASS", verbose)
    assert re.search(r"slider validation:\n\d+ checks: PASS", verbose)
    assert "[ok  ] no-collisions" in verbose
    assert re.search(r"travel: \d+\.\d+ mm", verbose)
