"""Content-addressed cache for the CAD build targets.

Building a shell piece with OCC takes seconds to tens of seconds, and a run
that changes one piece should not rebuild the rest. Every exported target
carries a fingerprint of the inputs that can move it: the pipeline sources
(the frame, the slide budget, the placements), the configuration tree and the
layout recipe, plus the modules that build that particular piece. A target
whose fingerprint matches the run that produced its exports, and whose
artifacts are still present and non-empty, is left alone.

The dependency lists are deliberately conservative: a module named for a
target invalidates that target even for a comment-only edit. Shipping stale
geometry is the failure mode worth avoiding; rebuilding too much only costs
time.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Iterator
from pathlib import Path

#: Bump when the fingerprint scheme or the export layout changes. It is part of
#: every fingerprint, so an older cache file is simply ignored.
CACHE_VERSION = 1

#: Written next to the exports; ``make clean`` removes it.
CACHE_FILE_NAME = ".build-cache.json"

ROOT: Path = Path(__file__).resolve().parent.parent

#: Inputs shared by every target: they feed the slider frame, the slide budget
#: and the placements, so touching any of them can move any part. The render
#: helpers are left out on purpose — they only draw what was already built.
PIPELINE_SOURCES: tuple[str, ...] = (
    "main.py",
    "assemblies",
    "components",
    "config",
    "exports",
    "keyboard",
    "layouts",
    "routing",
    "utilities/cad_helpers.py",
    "utilities/colors.py",
    "utilities/config_loader.py",
    "utilities/fasteners.py",
    "utilities/file_metadata.py",
    "utilities/metrics.py",
    "utilities/slider_validation.py",
    "utilities/validation.py",
)

_CHASSIS_SOURCES: tuple[str, ...] = (
    "case/chassis.py",
    "case/slider_frame.py",
    "geometry/base_taper.py",
    "geometry/chassis_joint.py",
    "geometry/joint.py",
    "geometry/ribs.py",
    "geometry/seam_joint.py",
    "geometry/split.py",
)
_DECK_SOURCES: tuple[str, ...] = _CHASSIS_SOURCES + ("geometry/well_mounts.py",)
_LID_SOURCES: tuple[str, ...] = (
    "case/screen_lid.py",
    "case/slider_frame.py",
    "geometry/joint.py",
    "geometry/seam_joint.py",
    "geometry/split.py",
)

#: Per-build-unit geometry sources, on top of :data:`PIPELINE_SOURCES`. A unit
#: that is not listed (a guide rod, a clamp, a component) is fully described by
#: the pipeline sources. The assembled targets embed every printed piece, so
#: they depend on the chassis and the lid alike.
PART_SOURCES: dict[str, tuple[str, ...]] = {
    "chassis_tray": _CHASSIS_SOURCES,
    "chassis_deck": _DECK_SOURCES,
    "chassis": _DECK_SOURCES,
    "screen_lid_bezel": _LID_SOURCES,
    "screen_lid_back": _LID_SOURCES,
    "screen_lid": _LID_SOURCES,
    "fpc_guard": ("case/screen_lid.py", "case/slider_frame.py"),
    "keyboard_plate": ("geometry/well_mounts.py",),
    "assembly": _DECK_SOURCES + _LID_SOURCES,
    "assembly_opened": _DECK_SOURCES + _LID_SOURCES,
}

#: Printable Sections are produced by their whole piece's build unit, so they
#: fingerprint (and therefore invalidate) together with it.
_SECTION_UNITS: dict[str, str] = {
    "chassis_tray_left": "chassis_tray",
    "chassis_tray_right": "chassis_tray",
    "chassis_deck_left": "chassis_deck",
    "chassis_deck_right": "chassis_deck",
    "chassis_left": "chassis",
    "chassis_right": "chassis",
    "screen_lid_left": "screen_lid",
    "screen_lid_right": "screen_lid",
    "screen_lid_bezel_left": "screen_lid_bezel",
    "screen_lid_bezel_right": "screen_lid_bezel",
    "screen_lid_back_left": "screen_lid_back",
    "screen_lid_back_right": "screen_lid_back",
    "keyboard_plate_left": "keyboard_plate",
    "keyboard_plate_right": "keyboard_plate",
}


def unit_for(target: str) -> str:
    """Return the build unit whose fingerprint covers *target*."""
    return _SECTION_UNITS.get(target, target)


def sources_for(target: str) -> tuple[str, ...]:
    """Return the geometry sources *target* is built from (beyond the pipeline)."""
    return PART_SOURCES.get(unit_for(target), ())


class BuildCache:
    """Persisted fingerprints of built targets, keyed by target name."""

    def __init__(
        self,
        path: Path,
        *,
        root: Path = ROOT,
        reuse: bool = True,
    ) -> None:
        self.path = Path(path)
        self.root = Path(root)
        #: Trust the recorded fingerprints. ``False`` (``--no-cache``) forces a
        #: rebuild but still refreshes the cache afterwards, so a forced build
        #: leaves the next incremental run in sync.
        self.reuse = reuse
        self._entries: dict[str, dict] = {}
        self._file_digests: dict[Path, str] = {}
        self._dirty = False
        self._load()

    # --- persistence -----------------------------------------------------
    def _load(self) -> None:
        if not self.path.is_file():
            return
        try:
            data = json.loads(self.path.read_text())
        except (OSError, ValueError):
            return
        if data.get("version") != CACHE_VERSION:
            return
        entries = data.get("targets")
        if isinstance(entries, dict):
            self._entries = entries

    def save(self) -> None:
        """Write the cache file, if anything changed since the last save."""
        if not self._dirty:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(
                {"version": CACHE_VERSION, "targets": self._entries},
                indent=2,
                sort_keys=True,
            )
            + "\n"
        )
        self._dirty = False

    # --- fingerprints ----------------------------------------------------
    def _sources(self, entries: Iterable[str]) -> Iterator[Path]:
        for entry in entries:
            path = self.root / entry
            if path.is_dir():
                for item in sorted(path.rglob("*")):
                    if item.is_file() and "__pycache__" not in item.parts:
                        yield item
            elif path.is_file():
                yield path

    def _file_digest(self, path: Path) -> str:
        digest = self._file_digests.get(path)
        if digest is None:
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            self._file_digests[path] = digest
        return digest

    def fingerprint(self, target: str) -> str:
        """Return the content fingerprint of everything *target* is built from."""
        hasher = hashlib.sha256()
        hasher.update(f"cyberdeck-cache-v{CACHE_VERSION}\0{unit_for(target)}\0".encode())
        files = PIPELINE_SOURCES + sources_for(target)
        for path in sorted(set(self._sources(files))):
            hasher.update(str(path.relative_to(self.root)).encode())
            hasher.update(b"\0")
            hasher.update(self._file_digest(path).encode())
            hasher.update(b"\0")
        return hasher.hexdigest()

    # --- freshness -------------------------------------------------------
    def is_fresh(self, target: str, artifacts: Iterable[Path]) -> bool:
        """True when *target*'s inputs and every artifact are unchanged."""
        if not self.reuse:
            return False
        entry = self._entries.get(target)
        if not isinstance(entry, dict):
            return False
        if entry.get("fingerprint") != self.fingerprint(target):
            return False
        return all(p.is_file() and p.stat().st_size > 0 for p in artifacts)

    def record(self, target: str, artifacts: Iterable[Path]) -> None:
        """Remember the current fingerprint and artifacts of *target*."""
        entry = {
            "fingerprint": self.fingerprint(target),
            "artifacts": [str(p) for p in artifacts],
        }
        if self._entries.get(target) != entry:
            self._entries[target] = entry
            self._dirty = True

    def __len__(self) -> int:
        return len(self._entries)
