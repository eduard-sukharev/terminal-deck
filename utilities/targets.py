"""Build-target resolution for the cyberdeck pipeline.

A target is either a *bucket* (a named group of solids) or a single component
role prefixed with ``comp:``.  The resolver validates tokens against the set
of loaded component roles and returns the set of buckets and the set of
per-component roles to build.

Buckets
-------
* ``all`` — every bucket below (convenience alias)
* ``assembly`` — full union of all placements
* ``base`` — base shell
* ``lid`` — lid shell
* ``hinge`` — hinge barrels + pin + wire tunnel
* ``display`` — LCD panel + HDMI driver combined (the sub-assembly)
* ``components`` — all per-component debug STLs

Per-component
-------------
* ``comp:<role>`` — a single component's raw STL (e.g. ``comp:driver``,
  ``comp:display`` for the raw LCD panel)
"""

from __future__ import annotations

#: All recognised bucket names.
BUCKETS: frozenset[str] = frozenset({
    "all", "assembly", "base", "lid", "lid_base", "lid_bezel",
    "hinge", "display", "components",
})


def resolve_targets(
    tokens: list[str],
    component_roles: set[str],
) -> tuple[set[str], set[str]]:
    """Resolve a list of target tokens into (buckets, comp_roles).

    Parameters
    ----------
    tokens : list[str]
        Target tokens from the CLI (e.g. ``["display", "comp:driver"]``).
    component_roles : set[str]
        Known component role names (e.g. ``{"display", "driver", …}``).

    Returns
    -------
    tuple[set[str], set[str]]
        ``(buckets, comp_roles)`` — the resolved bucket names and the
        per-component role names to build.

    Raises
    ------
    ValueError
        A token is neither a recognised bucket nor a valid ``comp:<role>``.
    """
    buckets: set[str] = set()
    comp_roles: set[str] = set()

    for token in tokens:
        if token in BUCKETS:
            if token == "all":
                buckets.update(BUCKETS - {"all"})
            else:
                buckets.add(token)
        elif token.startswith("comp:"):
            role = token[len("comp:"):]
            if role not in component_roles:
                raise ValueError(
                    f"unknown component role {role!r} in target {token!r} — "
                    f"known roles: {sorted(component_roles)}"
                )
            comp_roles.add(role)
        else:
            raise ValueError(
                f"unknown target {token!r} — "
                f"buckets: {sorted(BUCKETS)}, "
                f"per-component: comp:<role>"
            )

    return buckets, comp_roles


__all__ = ["BUCKETS", "resolve_targets"]
