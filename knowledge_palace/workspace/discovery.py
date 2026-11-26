"""Read-only project and section discovery for the paper editor.

Only regular, non-symlinked workspace entries are exposed. Revision contents are
read for the latest revision, or one explicitly named revision, with a size limit.
"""

import argparse
import json
import sys
from pathlib import Path

from ..tools.config_resolver import resolve_roots
from .argument_graph import changed_paragraphs, read_view
from .project import SLUG, load_project, validate_project
from .revision import _REVISION, save_revision


def _directory(path):
    return not path.is_symlink() and not getattr(path, "is_junction", lambda: False)() and path.is_dir()


def _file(path):
    return not path.is_symlink() and path.is_file()


def _project(workspace, slug):
    if not isinstance(slug, str) or not SLUG.fullmatch(slug):
        raise ValueError("slug must be ASCII kebab-case")
    projects = Path(workspace) / "projects"
    root = projects / slug
    if not _directory(projects) or not _directory(root) or not _file(root / "project.yaml"):
        raise FileNotFoundError("project not found: %s" % slug)
    manifest = load_project(workspace, slug)
    if manifest.get("slug") != slug or validate_project(manifest):
        raise ValueError("invalid project manifest: %s" % slug)
    return root, manifest


def list_projects(workspace):
    projects = Path(workspace) / "projects"
    if not _directory(projects):
        return {"projects": []}
    result = []
    for entry in sorted(projects.iterdir(), key=lambda p: p.name):
        if not SLUG.fullmatch(entry.name):
            continue
        try:
            _, manifest = _project(workspace, entry.name)
        except (OSError, UnicodeError, ValueError):
            continue
        result.append(manifest)
    return {"projects": result}


_PENDING_EVIDENCE = {"待补", "待定", "todo", "tbd", "none", "n/a", "na", "?"}


def _has_evidence(value):
    text = str(value or "").strip().lower()
    return bool(text) and text not in _PENDING_EVIDENCE


def _pending_evidence(value):
    return str(value or "").strip().lower() in _PENDING_EVIDENCE


def _graph_summary(path, revision_path=None):
    """Counts the writing workspace needs to gate and describe the next step."""
    try:
        with path.open("rb") as source:
            data = source.read(2 * 1024 * 1024 + 1)
        if len(data) > 2 * 1024 * 1024:
            return {"error": "graph page exceeds 2 MiB"}
        graph, written = read_view(data.decode("utf-8"))
        changes = changed_paragraphs(graph, written)
        nodes = graph.get("nodes") if isinstance(graph.get("nodes"), list) else []
        with_evidence = sum(1 for node in nodes if isinstance(node, dict)
                            and _has_evidence(node.get("evidence")))
        pending_evidence = sum(1 for node in nodes if isinstance(node, dict)
                               and _pending_evidence(node.get("evidence")))
        without_evidence = sum(1 for node in nodes if isinstance(node, dict)
                               and not str(node.get("evidence") or "").strip())
        stale = False
        updated = None
        try:
            updated = path.stat().st_mtime
        except OSError:
            updated = None
        if revision_path is not None:
            try:
                stale = revision_path.stat().st_mtime > path.stat().st_mtime + 0.5
            except OSError:
                stale = False
        return {
            "paragraphs": len(graph.get("paragraphs") or []),
            "nodes": len(nodes),
            "edges": len(graph.get("edges") or []),
            "updated": updated,
            "with_evidence": with_evidence,
            "pending_evidence": pending_evidence,
            "without_evidence": without_evidence,
            "rewrite": len(changes["rewrite"]),
            "drop": len(changes["drop"]),
            "reordered": bool(changes["reordered"]),
            "unplaced": len(changes["unplaced"]),
            "stale": stale,
        }
    except (OSError, KeyError, TypeError, ValueError, UnicodeError):
        return {"error": "graph page could not be read"}


def project_details(workspace, slug):
    root, manifest = _project(workspace, slug)
    analysis = ""
    analysis_path = root / "outline" / "manuscript-analysis.md"
    if _file(analysis_path):
        with analysis_path.open("rb") as source:
            analysis = source.read(256 * 1024).decode("utf-8", "replace")
    sections = []
    directory = root / "sections"
    if _directory(directory):
        for section in sorted(directory.iterdir(), key=lambda p: p.name):
            if not SLUG.fullmatch(section.name) or not _directory(section):
                continue
            revisions = sorted(p.name for p in section.iterdir()
                               if _REVISION.fullmatch(p.name) and _file(p))
            latest = revisions[-1] if revisions else None
            content = None
            if latest:
                revision = section / latest
                if not _file(revision):
                    raise ValueError("revision is not a regular file")
                with revision.open("rb") as source:
                    data = source.read(1024 * 1024 + 1)
                if len(data) > 1024 * 1024:
                    raise ValueError("latest revision exceeds 1 MiB")
                content = data.decode("utf-8")
            outline = root / "outline"
            graph = outline / ("graph-%s.html" % section.name)
            available = _directory(outline) and _file(graph)
            latest_path = (section / latest) if latest else None
            sections.append({"name": section.name, "revisions": revisions,
                             "latest": latest, "content": content,
                             "graph_available": available,
                             "graph_summary": _graph_summary(graph, latest_path) if available else None})
    return {"project": manifest, "sections": sections, "analysis": analysis}


def section_graph_summary(workspace, slug, section):
    """One section's graph counts, without reloading the project editor."""
    root, _ = _project(workspace, slug)
    if not isinstance(section, str) or not SLUG.fullmatch(section):
        raise ValueError("section must be ASCII kebab-case")
    outline = root / "outline"
    page = outline / ("graph-%s.html" % section)
    if not _directory(outline) or not _file(page):
        return {"graph_available": False, "graph_summary": None}
    latest_path = None
    section_dir = root / "sections" / section
    if _directory(section_dir):
        revisions = sorted(p.name for p in section_dir.iterdir()
                           if _REVISION.fullmatch(p.name) and _file(p))
        if revisions:
            latest_path = section_dir / revisions[-1]
    return {"graph_available": True, "graph_summary": _graph_summary(page, latest_path)}


def read_revision(workspace, slug, section, revision):
    """Read one named revision of an existing section, with a size limit."""
    root, _ = _project(workspace, slug)
    if not isinstance(section, str) or not SLUG.fullmatch(section):
        raise ValueError("section must be ASCII kebab-case")
    if not isinstance(revision, str) or not _REVISION.fullmatch(revision):
        raise ValueError("invalid revision name")
    directory = root / "sections"
    section_dir = directory / section
    if not _directory(directory) or not _directory(section_dir):
        raise FileNotFoundError("existing section not found")
    path = section_dir / revision
    if not _file(path):
        raise FileNotFoundError("revision not found: %s" % revision)
    with path.open("rb") as source:
        data = source.read(1024 * 1024 + 1)
    if len(data) > 1024 * 1024:
        raise ValueError("revision exceeds 1 MiB")
    return {"section": section, "revision": revision, "content": data.decode("utf-8")}


def create_section(workspace, slug, section):
    """Create one empty section directory without overwriting an existing one."""
    root, _ = _project(workspace, slug)
    if not isinstance(section, str) or not SLUG.fullmatch(section):
        raise ValueError("section must be ASCII kebab-case")
    directory = root / "sections"
    if not _directory(directory):
        raise FileNotFoundError("sections directory not found")
    (directory / section).mkdir(exist_ok=False)
    return {"section": section}


def save_section(workspace, slug, section, text, expected_latest):
    """Append one confirmed editor revision, rejecting stale source versions."""
    root, _ = _project(workspace, slug)
    if not isinstance(section, str) or not SLUG.fullmatch(section):
        raise ValueError("section must be ASCII kebab-case")
    directory = root / "sections"
    section_dir = directory / section
    if not _directory(directory) or not _directory(section_dir):
        raise FileNotFoundError("existing section not found")
    if not isinstance(text, str) or len(text.encode("utf-8")) > 1024 * 1024:
        raise ValueError("text must be UTF-8 and at most 1 MiB")
    if expected_latest is not None and (not isinstance(expected_latest, str) or not _REVISION.fullmatch(expected_latest)):
        raise ValueError("invalid expected revision")
    path = save_revision(root, section, text, expected_latest=expected_latest)
    return {"section": section, "revision": path.name}


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--config")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("list")
    commands.add_parser("details").add_argument("slug")
    summary = commands.add_parser("graph-summary")
    summary.add_argument("slug")
    summary.add_argument("section")
    read = commands.add_parser("read-revision")
    read.add_argument("slug")
    read.add_argument("section")
    read.add_argument("revision")
    create = commands.add_parser("create-section")
    create.add_argument("slug")
    create.add_argument("section")
    save = commands.add_parser("save-section")
    save.add_argument("slug")
    save.add_argument("section")
    save.add_argument("--expected", required=True, help="base revision, or NONE for a new section")
    save.add_argument("--file", required=True, help="temporary UTF-8 input")
    args = parser.parse_args()
    workspace = resolve_roots(args.config)["workspace_dir"]
    if args.command == "list":
        result = list_projects(workspace)
    elif args.command == "details":
        result = project_details(workspace, args.slug)
    elif args.command == "graph-summary":
        result = section_graph_summary(workspace, args.slug, args.section)
    elif args.command == "read-revision":
        result = read_revision(workspace, args.slug, args.section, args.revision)
    elif args.command == "create-section":
        result = create_section(workspace, args.slug, args.section)
    else:
        with Path(args.file).open("r", encoding="utf-8", newline="") as source:
            text = source.read()
        result = save_section(workspace, args.slug, args.section, text, None if args.expected == "NONE" else args.expected)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
