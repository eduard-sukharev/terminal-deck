"""The incremental build cache: fingerprints, staleness and persistence."""

from __future__ import annotations

import json
from pathlib import Path

from utilities.build_cache import (
    CACHE_VERSION,
    BuildCache,
    sources_for,
    unit_for,
)


def _tree(root: Path, files: dict[str, str]) -> Path:
    for rel, text in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    return root


def test_section_targets_fingerprint_with_their_whole_piece():
    assert unit_for("chassis_tray") == "chassis_tray"
    assert unit_for("chassis_tray_left") == "chassis_tray"
    assert unit_for("chassis_tray_right") == "chassis_tray"
    assert unit_for("display") == "display"
    assert sources_for("chassis_tray_left") == sources_for("chassis_tray")
    assert sources_for("rod_clamp") == ()


def test_fingerprint_is_stable_and_follows_its_sources(tmp_path):
    _tree(tmp_path, {"main.py": "x", "case/chassis.py": "a"})
    cache = BuildCache(tmp_path / "cache.json", root=tmp_path)

    before = cache.fingerprint("chassis_tray")
    assert before == cache.fingerprint("chassis_tray")

    (tmp_path / "case/chassis.py").write_text("b")
    changed = BuildCache(tmp_path / "cache.json", root=tmp_path)
    assert changed.fingerprint("chassis_tray") != before


def test_fingerprint_ignores_another_pieces_sources(tmp_path):
    _tree(
        tmp_path,
        {"main.py": "x", "case/chassis.py": "a", "case/screen_lid.py": "a"},
    )
    cache = BuildCache(tmp_path / "cache.json", root=tmp_path)
    before = cache.fingerprint("screen_lid_bezel")

    (tmp_path / "case/chassis.py").write_text("changed")
    reloaded = BuildCache(tmp_path / "cache.json", root=tmp_path)
    assert reloaded.fingerprint("screen_lid_bezel") == before


def test_artifacts_gate_freshness(tmp_path):
    _tree(tmp_path, {"main.py": "x"})
    artifact = tmp_path / "out.step"
    cache = BuildCache(tmp_path / "cache.json", root=tmp_path)

    assert not cache.is_fresh("display", [artifact])

    artifact.write_text("solid")
    cache.record("display", [artifact])
    assert cache.is_fresh("display", [artifact])

    artifact.unlink()
    assert not cache.is_fresh("display", [artifact])

    artifact.write_text("")  # an empty export is as good as missing
    assert not cache.is_fresh("display", [artifact])


def test_cache_round_trips_through_the_file(tmp_path):
    _tree(tmp_path, {"main.py": "x"})
    artifact = tmp_path / "out.step"
    artifact.write_text("solid")
    path = tmp_path / "cache.json"

    cache = BuildCache(path, root=tmp_path)
    cache.record("display", [artifact])
    cache.save()

    data = json.loads(path.read_text())
    assert data["version"] == CACHE_VERSION
    assert "display" in data["targets"]
    assert BuildCache(path, root=tmp_path).is_fresh("display", [artifact])


def test_changed_input_makes_a_recorded_target_stale(tmp_path):
    _tree(tmp_path, {"main.py": "x"})
    artifact = tmp_path / "out.step"
    artifact.write_text("solid")
    path = tmp_path / "cache.json"

    cache = BuildCache(path, root=tmp_path)
    cache.record("display", [artifact])
    cache.save()

    (tmp_path / "main.py").write_text("changed")
    assert not BuildCache(path, root=tmp_path).is_fresh("display", [artifact])


def test_cache_file_from_another_version_is_ignored(tmp_path):
    _tree(tmp_path, {"main.py": "x"})
    artifact = tmp_path / "out.step"
    artifact.write_text("solid")
    path = tmp_path / "cache.json"
    path.write_text(
        json.dumps(
            {
                "version": CACHE_VERSION - 1,
                "targets": {"display": {"fingerprint": "x", "artifacts": []}},
            }
        )
    )

    assert not BuildCache(path, root=tmp_path).is_fresh("display", [artifact])


def test_no_reuse_still_refreshes_the_cache(tmp_path):
    _tree(tmp_path, {"main.py": "x"})
    artifact = tmp_path / "out.step"
    artifact.write_text("solid")
    path = tmp_path / "cache.json"

    cache = BuildCache(path, root=tmp_path, reuse=False)
    cache.record("display", [artifact])
    cache.save()

    assert not cache.is_fresh("display", [artifact])
    assert json.loads(path.read_text())["targets"].keys() == {"display"}
    assert BuildCache(path, root=tmp_path).is_fresh("display", [artifact])
