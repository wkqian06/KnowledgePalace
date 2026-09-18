"""ProjectBrief — the evidence contract a project section is written from.

A brief carries the genre parameters, the section plan and the evidence
package: id-shaped refs (index ids or ``project-source:``), each with a
verbatim quote AND its anchor. Material ids may enter as writing input but
are not legal evidence refs.
"""

from ..interaction.project_source import ID_PREFIXES, PROJECT_SOURCE_PREFIX
from .material import MATERIAL_PREFIX
from .revision import ASSEMBLED

EVIDENCE_PREFIXES = ID_PREFIXES + (PROJECT_SOURCE_PREFIX,)


def new_brief(project, problem, contribution, sections, evidence=(),
              bibliography=(), materials=(), audience="", venue="",
              language="en", length="", citation_style="apa",
              style_profile=""):
    """sections: [{"name", "kind", "depends_on": [...]}] in writing order."""
    return {
        "project": project,
        "problem": problem,
        "contribution": contribution,
        "sections": list(sections),
        "evidence": list(evidence),
        "bibliography": list(bibliography),
        "materials": list(materials),
        "audience": audience,
        "venue": venue,
        "language": language,
        "length": length,
        "citation_style": citation_style,
        "style_profile": style_profile,
    }


def validate_brief(brief):
    """Return violations; empty means the brief can be written from."""
    if not isinstance(brief, dict):
        return ["brief must be a dict"]
    errors = []
    sections = brief.get("sections")
    if not isinstance(sections, list) or not sections:
        errors.append("sections must be a non-empty plan")
        sections = []
    names = [s.get("name") for s in sections if isinstance(s, dict)]
    if len(set(names)) != len(names) or not all(names):
        errors.append("section names must be present and unique")
    if ASSEMBLED in names:
        errors.append(
            "%r is the reserved name for the assembled full document" % ASSEMBLED
        )
    for section in sections:
        if not isinstance(section, dict):
            errors.append("each section must be a dict")
            continue
        for dependency in section.get("depends_on") or []:
            if dependency not in names:
                errors.append(
                    "section %r depends on unknown %r" % (section.get("name"), dependency)
                )
    for index, entry in enumerate(brief.get("evidence") or []):
        where = "evidence[%d]" % index
        if not isinstance(entry, dict):
            errors.append("%s: must be a dict" % where)
            continue
        ref = str(entry.get("ref") or "")
        if ref.startswith(MATERIAL_PREFIX):
            errors.append(
                "%s: %r is a ProjectMaterial — materials feed writing, "
                "never Claim evidence" % (where, ref)
            )
        elif not ref.startswith(EVIDENCE_PREFIXES):
            errors.append("%s: ref %r is not id-shaped" % (where, ref))
        if not entry.get("quote"):
            errors.append("%s: verbatim quote required" % where)
        if not entry.get("anchor"):
            errors.append("%s: evidence anchor required" % where)
    for index, material_id in enumerate(brief.get("materials") or []):
        if not str(material_id).startswith(MATERIAL_PREFIX):
            errors.append("materials[%d]: %r lacks the %r prefix"
                          % (index, material_id, MATERIAL_PREFIX))
    return errors

