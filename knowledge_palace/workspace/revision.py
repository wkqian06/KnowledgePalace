"""Append-only rNNN revisions — confirmed saves only, never overwrites.

Each confirmed save of a section becomes ``sections/<section>/rNNN.md``
with the next number; prior revisions are immutable (exports and later
edits never touch them). The assembled full document is the reserved
section name ``assembled``.
Exclusive creation via temp + os.link —
complete content AND collision refusal, atomically.
"""

import os
import re
import tempfile
from pathlib import Path

from .project import SLUG

ASSEMBLED = "assembled"
_REVISION = re.compile(r"^r(\d{3})\.md$")


def _section_dir(project_dir, section):
    if not SLUG.match(section):
        raise ValueError("section %r must be ASCII kebab-case" % section)
    return Path(project_dir) / "sections" / section


def list_revisions(project_dir, section):
    directory = _section_dir(project_dir, section)
    if not directory.is_dir():
        return []
    return sorted(p.name for p in directory.iterdir()
                  if _REVISION.match(p.name) and not p.is_symlink() and p.is_file())


def latest(project_dir, section):
    revisions = list_revisions(project_dir, section)
    return revisions[-1] if revisions else None


def save_revision(project_dir, section, text, expected_latest=...):
    """Publish a complete immutable revision; optionally reject stale editors.

    A unique temporary file avoids concurrent writers sharing temporary bytes.
    Atomic link creation ensures only one writer can publish a particular next
    revision. On collision the caller must reload rather than overwrite.
    """
    directory = _section_dir(project_dir, section)
    directory.mkdir(parents=True, exist_ok=True)
    revisions = list_revisions(project_dir, section)
    current = revisions[-1] if revisions else None
    if expected_latest is not ... and expected_latest != current:
        raise ValueError("revision conflict: expected %r, latest is %r" % (expected_latest, current))
    number = int(_REVISION.match(current).group(1)) + 1 if current else 1
    if number > 999:
        raise ValueError("revision limit reached")
    target = directory / ("r%03d.md" % number)
    fd, temporary = tempfile.mkstemp(prefix=".revision-", suffix=".tmp", dir=directory)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as output:
            output.write(text)
        try:
            os.link(temporary, target)
        except FileExistsError:
            raise ValueError("revision conflict: another writer saved %s; reload before saving" % target.name)
    finally:
        os.unlink(temporary)
    return target
