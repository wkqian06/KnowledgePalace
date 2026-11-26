"""Style profiles for the writing workspace.

The library owns the style bank under ``styles/profiles/*.md``; a project only
records which profiles it follows in ``project.yaml``'s ``style_profile`` field
(semicolon separated). Reading the bank is public; selecting a profile for a
project is a confirmed project write and replaces only that one manifest line.
"""

import os
import tempfile
from pathlib import Path

from .discovery import _directory, _file, _project
from .project import SLUG, load_project, validate_project


def _front_matter(path):
    """The flat ``key: value`` front matter of a style profile, or {}."""
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end < 0:
        return {}
    fields = {}
    for line in text[3:end].splitlines():
        key, sep, value = line.partition(": ")
        if not sep:
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        fields[key.strip()] = value
    return fields


def list_style_profiles(vault_dir):
    """Every regular profile file, with the few fields the picker needs."""
    root = Path(vault_dir) / "styles" / "profiles"
    profiles = []
    if not _directory(root):
        return {"profiles": profiles, "counts": {"journal": 0, "language": 0}}
    for path in sorted(root.glob("*.md"), key=lambda item: item.name):
        if path.name == "INDEX.md" or not _file(path):
            continue
        try:
            fields = _front_matter(path)
        except (OSError, UnicodeError):
            continue
        name = (fields.get("name") or path.stem).strip()
        if not SLUG.fullmatch(name):
            continue
        kind = (fields.get("type") or "").strip() or "other"
        alias = (fields.get("alias") or "").strip() or name
        profiles.append({
            "name": name,
            "type": kind,
            "alias": alias[:400],
            "description": (fields.get("description") or "").strip()[:800],
            "updated": (fields.get("updated") or "").strip(),
        })
    counts = {"journal": 0, "language": 0}
    for profile in profiles:
        if profile["type"] in counts:
            counts[profile["type"]] += 1
    return {"profiles": profiles, "counts": counts}


def _normalize(vault_dir, profile):
    if not isinstance(profile, str):
        raise ValueError("style profile must be a string")
    if "\x00" in profile or profile.splitlines() not in ([], [profile]):
        raise ValueError("style profile must be a single line without NUL")
    names = []
    for part in profile.split(";"):
        name = part.strip()
        if not name:
            continue
        if not SLUG.fullmatch(name):
            raise ValueError("style profile %r must be ASCII kebab-case" % name)
        path = Path(vault_dir) / "styles" / "profiles" / ("%s.md" % name)
        if not _file(path):
            raise FileNotFoundError("style profile not found: %s" % name)
        if name not in names:
            names.append(name)
    return ";".join(names)


def set_project_style(workspace_dir, vault_dir, slug, profile):
    """Replace the project's ``style_profile`` line; nothing else is touched."""
    root, project = _project(workspace_dir, slug)
    path = root / "project.yaml"
    if path.is_symlink() or not _file(path):
        raise ValueError("project manifest must be a regular file")
    value = _normalize(vault_dir, profile)
    errors = validate_project({**project, "style_profile": value})
    if errors:
        raise ValueError("invalid project: %s" % errors)
    lines = path.read_text(encoding="utf-8").splitlines()
    line = "style_profile: %s" % value
    replaced = False
    kept = []
    for existing in lines:
        if existing.startswith("style_profile:"):
            if not replaced:
                kept.append(line)
                replaced = True
            continue
        kept.append(existing)
    if not replaced:
        kept.append(line)
    # The manifest writer is the single gate; keep the same flat key set.
    manifest = "\n".join(kept) + "\n"
    descriptor, temporary = tempfile.mkstemp(prefix=".project-", suffix=".yaml", dir=str(root))
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(manifest)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return {"project": load_project(workspace_dir, slug), "style_profile": value}
