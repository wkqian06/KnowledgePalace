"""Project learning, research decisions and user observations for the analyst."""

import json
from pathlib import Path

from .project import load_project
from ..semantic.evidence_helpers import read_tables, dependencies


def project_context(workspace, slug, vault):
    """Read the existing project and its optional research notebook as context."""
    root = Path(workspace) / "projects" / slug
    project = load_project(workspace, slug)
    brief_path = root / "outline/brief.json"
    brief = json.loads(brief_path.read_text(encoding="utf-8")) if brief_path.is_file() else {}
    materials_path = root / "materials/materials.json"
    materials = json.loads(materials_path.read_text(encoding="utf-8")) if materials_path.is_file() else []
    notes_path = root / "research.md"
    notes = notes_path.read_text(encoding="utf-8") if notes_path.is_file() else ""
    analysis_path = root / "outline/manuscript-analysis.md"
    analysis = analysis_path.read_text(encoding="utf-8") if analysis_path.is_file() else ""
    tables, errors = read_tables(notes, str(notes_path))
    if errors:
        raise ValueError("; ".join(errors))
    judgments = {row["id"]: row for row in tables["Synthesis"]}
    source_ids = {row["id"] for row in materials}
    feedback = []
    for row in tables["Observations"]:
        if row["judgment"] not in judgments or row["source"] not in source_ids:
            raise ValueError("observation %s needs a declared judgment and project material" % row["id"])
        feedback.append({**row, "dependencies": dependencies(judgments[row["judgment"]]),
                         "provenance": "user observation; review proposal, not a literature Claim"})
    styles = []
    for reference in (brief.get("style_profile") or project.get("style_profile", "")).split(";"):
        reference = reference.strip()
        if not reference:
            continue
        path = Path(reference)
        if not path.is_absolute():
            path = Path(vault) / "styles/profiles" / reference
            if not path.suffix:
                path = path.with_suffix(".md")
        styles.append({"path": str(path), "rules": path.read_text(encoding="utf-8")})
    return {"project": project, "brief": brief, "research_notes": notes,
            "manuscript_analysis": analysis,
            "materials": materials, "judgments": list(judgments.values()),
            "observation_feedback": feedback, "style_profiles": styles}
