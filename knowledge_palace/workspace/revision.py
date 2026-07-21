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
from pathlib import Path

from .project import _SLUG

ASSEMBLED = "assembled"
_REVISION = re.compile(r"^r(\d{3})\.md$")


def _section_dir(project_dir, section):
    if not _SLUG.match(section):
        raise ValueError("section %r must be ASCII kebab-case" % section)
    return Path(project_dir) / "sections" / section


def list_revisions(project_dir, section):
    directory = _section_dir(project_dir, section)
    if not directory.is_dir():
        return []
    return sorted(p.name for p in directory.iterdir() if _REVISION.match(p.name))


def latest(project_dir, section):
    revisions = list_revisions(project_dir, section)
    return revisions[-1] if revisions else None


def save_revision(project_dir, section, text):
    """One confirmed save → the next rNNN.md; existing bytes never change."""
    directory = _section_dir(project_dir, section)
    directory.mkdir(parents=True, exist_ok=True)
    numbers = [int(_REVISION.match(name).group(1)) for name in list_revisions(project_dir, section)]
    target = directory / ("r%03d.md" % (max(numbers, default=0) + 1))
    temp = directory / (".%s.tmp" % target.name)
    temp.write_text(text, encoding="utf-8")
    try:
        os.link(temp, target)  # refuses if target exists; content complete
    except FileExistsError:
        raise ValueError("revision %s already exists — revisions are immutable" % target.name)
    finally:
        temp.unlink()
    return target
