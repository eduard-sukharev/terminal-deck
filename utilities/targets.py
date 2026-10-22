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
* ``lid`` — combined lid assembly (lid_shell + display + lid_bezel)
* ``lid_shell`` — the Lid shell (rear tray); ``lid_bezel`` — the Bezel
* ``<part>_left`` / ``<part>_right`` — one Half of ``base_bottom``,
  ``base_top``, ``lid_shell`` or ``lid_bezel`` (see :data:`SPLIT_PARTS`).
  They resolve to the part's bucket; :func:`requested_halves` then narrows
  the export to just the named Halves.
* ``hinge`` — hinge barrels + pin + wire tunnel
* ``keyboard_plate`` — bare switch plate (printed as two Halves)
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
    "all", "assembly", "assembly_opened", "base", "base_bottom", "base_top",
    "lid", "lid_shell", "lid_bezel", "keyboard_plate",
    "hinge", "display", "components",
})


#: Parts printed as left/right Halves (ADR 0001).
SPLIT_PARTS: frozenset[str] = frozenset({
    "base_bottom", "base_top", "lid_shell", "lid_bezel", "keyboard_plate",
})

_HALF_ALIASES: dict[str, str] = {
    f"{part}_{side}": part for part in SPLIT_PARTS for side in ("left", "right")
}


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
        if token in _HALF_ALIASES:
            buckets.add(_HALF_ALIASES[token])
        elif token in BUCKETS:
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


#: Buckets that, when requested, include a split part as a whole.
_PART_CONTAINERS: dict[str, frozenset[str]] = {
    "base_bottom": frozenset({"base_bottom", "base", "all"}),
    "base_top": frozenset({"base_top", "base", "all"}),
    "lid_shell": frozenset({"lid_shell", "lid", "all"}),
    "lid_bezel": frozenset({"lid_bezel", "lid", "all"}),
    "keyboard_plate": frozenset({"keyboard_plate", "all"}),
}


def requested_halves(tokens: list[str]) -> set[str]:
    """Half names (``<part>_left``/``_right``) that were asked for alone.

    A Half is dropped from the result when its part is also wanted as a whole
    (directly or via a bucket such as ``lid``, ``base`` or ``all``), because
    then every Half is built anyway.  An empty result means "no narrowing".
    """
    wanted = set(tokens)
    return {
        token for token in tokens
        if token in _HALF_ALIASES
        and not wanted & _PART_CONTAINERS[_HALF_ALIASES[token]]
    }


__all__ = ["BUCKETS", "SPLIT_PARTS", "requested_halves", "resolve_targets"]
