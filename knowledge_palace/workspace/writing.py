"""Manuscript inputs and precise passage replacement for writing and polishing."""

from .brief import validate_brief


def writing_context(text, analysis, *, brief=None, section=None, evidence=(), materials=()):
    """Combine an analysed manuscript with direct or project evidence.

    The agent supplies the manuscript analysis described in the writing workflow.
    This function does not score that analysis or certify scientific correctness.
    Project evidence is checked once here; direct source reading remains the
    caller's responsibility.
    """
    if brief is not None:
        errors = validate_brief(brief)
        if errors:
            raise ValueError("invalid project evidence: " + "; ".join(errors))
        evidence = brief.get("evidence", [])
        materials = brief.get("materials", [])
        if section and section not in {row["name"] for row in brief["sections"]}:
            raise ValueError("section %r is not in the project outline" % section)
    return {"text": text, "analysis": analysis, "section": section,
            "evidence": list(evidence), "materials": list(materials),
            "project": brief.get("project") if brief is not None else None}


def replace_passage(document, original, revised):
    """Replace one unambiguous passage without rewriting surrounding content."""
    if not original or document.count(original) != 1:
        raise ValueError("select one unique original passage before replacing it")
    return document.replace(original, revised, 1)
