"""Proposal — aims/approach alignment and the User Material fact boundary.

The Proposal section set extends the writing machinery (same
briefs, packages, loop, revisions). Two extra deterministic rules:
every aim must map to at least one approach element (orphans on either
side are named findings), and budget figures, institutional facts, and
preliminary results validate only when the package carries registered
ProjectMaterial ids — user facts come from User Material, never from
the model.
"""

from .writing import new_package, validate_package

PROPOSAL_SECTION_KINDS = (
    "summary",
    "specific-aims",
    "significance",
    "innovation",
    "approach",
    "evaluation",
    "milestones",
    "risks",
    "broader-impact",
    "preliminary-results",
)
USER_FACT_KINDS = ("budget", "institution", "preliminary-results")


def validate_alignment(aims, approach_map):
    """aims: [aim ids]; approach_map: {approach element: [aim ids]}.

    Returns named findings; empty means aims and approach fully align.
    """
    findings = []
    mapped = set()
    for element in sorted(approach_map):
        refs = approach_map[element]
        if not refs:
            findings.append("approach element %r maps to no aim" % element)
        for ref in refs:
            if ref not in aims:
                findings.append(
                    "approach element %r references unknown aim %r" % (element, ref)
                )
            else:
                mapped.add(ref)
    for aim in aims:
        if aim not in mapped:
            findings.append("aim %r has no approach element (orphan)" % aim)
    return findings


def new_proposal_package(section, brief_fingerprint, evidence_refs=(),
                         material_ids=(), requirement_refs=(), user_facts=(),
                         placeholder_only=False):
    package = new_package(section, brief_fingerprint, evidence_refs,
                          material_ids, placeholder_only)
    package["requirements"] = list(requirement_refs)
    package["user_facts"] = list(user_facts)
    return package


def validate_proposal_package(package, brief, matrix):
    """Writing package rules PLUS matrix refs and the user-fact boundary."""
    errors = list(validate_package(package, brief))
    known = {row["id"] for row in matrix.get("rows") or []}
    for ref in package.get("requirements") or []:
        if ref not in known:
            errors.append("requirement %r is not in the matrix" % ref)
    facts = package.get("user_facts") or []
    for fact in facts:
        if fact not in USER_FACT_KINDS:
            errors.append("user fact %r not in %s" % (fact, list(USER_FACT_KINDS)))
    if facts and not package.get("materials"):
        errors.append(
            "budget/institutional/preliminary-result content requires "
            "registered User Material — user facts never come from the model"
        )
    return errors
