"""Tests for DE-readable filesystem metadata (extended attributes)."""

from __future__ import annotations

import os

import pytest

from utilities import file_metadata as fm


def test_apply_writes_comment_tags_creator(monkeypatch):
    written = {}

    def fake_setxattr(path, name, value):
        written[name] = value

    monkeypatch.setattr(os, "setxattr", fake_setxattr)

    metadata = {
        "layout": "recipe_compact",
        "config": "config/default.yaml",
        "rev": "abc1234",
        "built": "2026-08-07T12:00:00+03:00",
    }
    ok = fm.apply(metadata, "/tmp/out.step")

    assert ok is True
    comment = written[fm.XATTR_COMMENT].decode()
    assert "layout=recipe_compact" in comment
    assert "config=config/default.yaml" in comment
    assert "rev=abc1234" in comment
    assert "built=2026-08-07T12:00:00+03:00" in comment
    assert written[fm.XATTR_TAGS].decode() == "cyberdeck,recipe_compact"
    assert written[fm.XATTR_CREATOR].decode() == "cyberdeck"


def test_apply_omits_missing_provenance(monkeypatch):
    written: dict = {}

    def fake_setxattr(path, name, value):
        written[name] = value

    monkeypatch.setattr(os, "setxattr", fake_setxattr)

    ok = fm.apply({"layout": "compact"}, "/tmp/x.stl")

    assert ok is True
    comment = written[fm.XATTR_COMMENT].decode()
    assert "layout=compact" in comment
    assert "config=" not in comment
    assert "rev=" not in comment
    assert "built=" not in comment


def test_apply_returns_false_on_oserror(monkeypatch):
    def boom(path, name, value):
        raise OSError("no xattr support")

    monkeypatch.setattr(os, "setxattr", boom)

    assert fm.apply({"layout": "recipe"}, "/tmp/x.step") is False


def test_apply_empty_metadata_still_sets_creator(monkeypatch):
    written: dict = {}

    def fake_setxattr(path, name, value):
        written[name] = value

    monkeypatch.setattr(os, "setxattr", fake_setxattr)

    assert fm.apply({}, "/tmp/x.svg") is True
    assert written[fm.XATTR_TAGS].decode() == "cyberdeck"
    assert written[fm.XATTR_CREATOR].decode() == "cyberdeck"