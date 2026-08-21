"""Write DE-readable filesystem metadata (extended attributes) to files.

Linux file managers read a file's comment/tags from XDG ``user.*`` extended
attributes rather than from anything embedded in the file body:

- ``user.xdg.comment`` — the comment shown in Dolphin's Properties /
  information panel (and other file managers).
- ``user.xdg.tags`` — a CSV tag list (de-facto standard).
- ``user.xdg.creator`` — the application that created the file.

Writing them is best-effort: filesystems without xattr support (or a
permission/space error) raise ``OSError``, which is reported and ignored so a
build never fails because metadata could not be stored.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable

#: XDG extended-attribute names (see xattr(7) / ArchWiki "Extended attributes").
XATTR_COMMENT = "user.xdg.comment"
XATTR_TAGS = "user.xdg.tags"
XATTR_CREATOR = "user.xdg.creator"

#: Application name recorded as the file's creator.
CREATOR = "cyberdeck"


def set_comment(path: Path | str, text: str) -> None:
    """Set the DE comment (``user.xdg.comment``) on ``path``."""
    os.setxattr(path, XATTR_COMMENT, text.encode("utf-8"))


def set_tags(path: Path | str, tags: Iterable[str]) -> None:
    """Set the DE tags (``user.xdg.tags``) on ``path`` as a CSV list."""
    os.setxattr(path, XATTR_TAGS, ",".join(tags).encode("utf-8"))


def set_creator(path: Path | str, creator: str = CREATOR) -> None:
    """Set the DE creator (``user.xdg.creator``) on ``path``."""
    os.setxattr(path, XATTR_CREATOR, creator.encode("utf-8"))


def apply(metadata: dict, path: Path | str) -> bool:
    """Write ``metadata`` to ``path`` as DE-readable extended attributes.

    Maps the exporter provenance dict onto the XDG xattrs:

    - ``layout`` / ``config`` / ``rev`` / ``built`` -> ``user.xdg.comment``
    - ``layout`` -> ``user.xdg.tags`` (with the app name)
    - ``creator`` -> ``user.xdg.creator``

    Returns ``True`` on success, ``False`` if the filesystem rejected the
    write (no xattr support, permission, etc.) — the caller should warn, not
    fail.
    """
    try:
        layout = metadata.get("layout", "")
        parts = [f"layout={layout}"]
        if metadata.get("config"):
            parts.append(f"config={metadata['config']}")
        if metadata.get("rev"):
            parts.append(f"rev={metadata['rev']}")
        if metadata.get("built"):
            parts.append(f"built={metadata['built']}")
        set_comment(path, "cyberdeck " + " ".join(parts))
        set_tags(path, [CREATOR, layout] if layout else [CREATOR])
        set_creator(path, metadata.get("creator", CREATOR))
        return True
    except OSError:
        return False