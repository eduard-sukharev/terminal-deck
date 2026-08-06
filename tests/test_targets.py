"""Tests for build-target resolution."""

import pytest
from utilities.targets import BUCKETS, resolve_targets


def test_all_expands_to_all_buckets():
    buckets, comp_roles = resolve_targets(["all"], {"display", "driver"})
    assert buckets == BUCKETS - {"all"}
    assert comp_roles == set()


def test_single_bucket():
    buckets, comp_roles = resolve_targets(["display"], {"display", "driver"})
    assert buckets == {"display"}
    assert comp_roles == set()


def test_multiple_buckets():
    buckets, comp_roles = resolve_targets(
        ["display", "base"], {"display", "driver"}
    )
    assert buckets == {"display", "base"}
    assert comp_roles == set()


def test_comp_role():
    buckets, comp_roles = resolve_targets(
        ["comp:driver"], {"display", "driver"}
    )
    assert buckets == set()
    assert comp_roles == {"driver"}


def test_comp_role_unknown_raises():
    with pytest.raises(ValueError, match="unknown component role"):
        resolve_targets(["comp:nonexistent"], {"display", "driver"})


def test_unknown_token_raises():
    with pytest.raises(ValueError, match="unknown target"):
        resolve_targets(["garbage"], {"display", "driver"})


def test_components_bucket():
    buckets, comp_roles = resolve_targets(["components"], {"display", "driver"})
    assert buckets == {"components"}
    assert comp_roles == set()


def test_mixed_buckets_and_comp_roles():
    buckets, comp_roles = resolve_targets(
        ["display", "comp:driver"], {"display", "driver", "sbc"}
    )
    assert buckets == {"display"}
    assert comp_roles == {"driver"}


def test_all_buckets_are_recognised():
    for bucket in BUCKETS:
        buckets, _ = resolve_targets([bucket], {"display"})
        if bucket == "all":
            assert buckets == BUCKETS - {"all"}
        else:
            assert buckets == {bucket}
