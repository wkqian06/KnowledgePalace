"""RequirementsMatrix — anchored rows, named coverage, honest degradation.

A solicitation becomes checkable rows: each carries its source anchor,
coverage names every uncovered requirement (never summarizes), and the
no-solicitation fallback is BORN compliance-unverifiable — a flag the
validator enforces, not a footnote. The line extractor is a documented
recall-over-precision prefilter (modal markers); full solicitation
UNDERSTANDING stays LLM territory, and this schema controls what any
extraction may claim.
"""

import re

_MODAL = re.compile(r"\b(must|shall|required|should)\b", re.IGNORECASE)

# ponytail: five generic rows cover the universal proposal skeleton; a
# richer sponsor-neutral profile is protocol work, not code.
GENERIC_ROWS = (
    {"id": "G1", "text": "State the problem and a concise summary", "anchor": "generic"},
    {"id": "G2", "text": "Name specific aims or objectives", "anchor": "generic"},
    {"id": "G3", "text": "Argue significance and innovation", "anchor": "generic"},
    {"id": "G4", "text": "Describe the approach and its evaluation", "anchor": "generic"},
    {"id": "G5", "text": "Address risks and broader impact", "anchor": "generic"},
)


def extract_requirements(text):
    """Modal-marker lines → anchored rows (recall-over-precision prefilter)."""
    rows = []
    for lineno, line in enumerate(text.splitlines(), 1):
        if _MODAL.search(line):
            rows.append(
                {
                    "id": "R%d" % (len(rows) + 1),
                    "text": line.strip(),
                    "anchor": "line %d" % lineno,
                }
            )
    return rows


def new_matrix(source, rows):
    """A matrix from a real solicitation (source names the document)."""
    return {
        "source": source,
        "rows": list(rows),
        "compliance_verifiable": True,
        "degradation_note": "",
    }


def generic_matrix(reason, rows=GENERIC_ROWS):
    """The no-solicitation fallback: compliance is unverifiable from birth."""
    return {
        "source": "",
        "rows": [dict(row) for row in rows],
        "compliance_verifiable": False,
        "degradation_note": reason,
    }


def validate_matrix(matrix):
    """Return violations; empty means the matrix may govern a proposal."""
    if not isinstance(matrix, dict):
        return ["matrix must be a dict"]
    errors = []
    rows = matrix.get("rows")
    if not isinstance(rows, list) or not rows:
        errors.append("rows must be a non-empty list")
        rows = []
    seen = set()
    for index, row in enumerate(rows):
        where = "rows[%d]" % index
        if not isinstance(row, dict):
            errors.append("%s: must be a dict" % where)
            continue
        for key in ("id", "text", "anchor"):
            if not row.get(key):
                errors.append("%s: missing %s" % (where, key))
        identifier = row.get("id")
        if identifier:
            if identifier in seen:
                errors.append("%s: duplicate id %r" % (where, identifier))
            seen.add(identifier)
    if matrix.get("source"):
        if matrix.get("compliance_verifiable") is not True:
            errors.append("a sourced matrix is compliance-verifiable")
    else:
        if matrix.get("compliance_verifiable") is not False:
            errors.append(
                "without a solicitation, sponsor compliance is unverifiable "
                "— the flag must say so"
            )
        if not matrix.get("degradation_note"):
            errors.append("the generic fallback must name why it degraded")
    return errors


def coverage(matrix, mapping):
    """{section: [requirement ids]} → named covered/uncovered/unknown."""
    known = {row["id"] for row in matrix.get("rows") or []}
    covered, unknown = set(), []
    for section in sorted(mapping):
        for ref in mapping[section]:
            if ref in known:
                covered.add(ref)
            else:
                unknown.append("%s -> %s" % (section, ref))
    return {
        "covered": sorted(covered),
        "uncovered": sorted(known - covered),
        "unknown_refs": unknown,
    }
