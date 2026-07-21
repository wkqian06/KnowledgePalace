"""ResearchProject — the projects/<slug>/ skeleton and its flat manifest.

Everything is resolved against the handed workspace_dir, never the CWD;
project.yaml stores flat single-line ``key: value`` strings only (strict
stdlib subset, same spirit as the TOML subset in config_resolver). The
current revision is never stored — it is computed live from the revision
files (store decisions, compute counts).
"""

import re
from pathlib import Path

PROJECT_DIRS = (
    "materials",
    "sources",
    "requirements",
    "outline",
    "sections",
    "reviews",
    "bibliography",
    "exports",
)
KINDS = ("paper", "proposal")
_SLUG = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*\Z")
_FIELDS = (
    "slug",
    "kind",
    "audience",
    "venue",
    "language",
    "length",
    "citation_style",
    "style_profile",
    "status",
)


def new_project(slug, kind, audience, venue="", language="en", length="",
                citation_style="apa", style_profile="", status="active"):
    return {
        "slug": slug,
        "kind": kind,
        "audience": audience,
        "venue": venue,
        "language": language,
        "length": length,
        "citation_style": citation_style,
        "style_profile": style_profile,
        "status": status,
    }


def validate_project(project):
    """Return violations; empty means the project record is writable."""
    if not isinstance(project, dict):
        return ["project must be a dict"]
    errors = []
    if not _SLUG.match(str(project.get("slug") or "")):
        errors.append("slug must be ASCII kebab-case")
    if project.get("kind") not in KINDS:
        errors.append("kind %r not in %s" % (project.get("kind"), list(KINDS)))
    if not project.get("audience"):
        errors.append("missing audience")
    if not project.get("citation_style"):
        errors.append("missing citation_style")
    for field in _FIELDS:
        value = project.get(field, "")
        # The write guard must match the load parser: splitlines() splits
        # on every Unicode line boundary (CR, VT, U+2028, ...), not just \n.
        if not isinstance(value, str) or value.splitlines() not in ([], [value]):
            errors.append("%s must be a single-line string" % field)
    return errors


def create_project(workspace_dir, project):
    """Materialize the skeleton + project.yaml; refuses to overwrite."""
    errors = validate_project(project)
    if errors:
        raise ValueError("invalid project: %s" % errors)
    root = Path(workspace_dir) / "projects" / project["slug"]
    if root.exists():
        raise ValueError("project %r already exists" % project["slug"])
    for name in PROJECT_DIRS:
        (root / name).mkdir(parents=True)
    manifest = "".join(
        "%s: %s\n" % (field, project.get(field, "")) for field in _FIELDS
    )
    (root / "project.yaml").write_text(manifest, encoding="utf-8")
    return root


def load_project(workspace_dir, slug):
    """Parse the flat manifest back into a project dict (strict subset)."""
    path = Path(workspace_dir) / "projects" / slug / "project.yaml"
    project = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        key, sep, value = line.partition(": ")
        if not sep:
            raise ValueError("unparseable manifest line %r in %s" % (line, path))
        project[key] = value
    return project
