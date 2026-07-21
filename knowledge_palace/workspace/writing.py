"""The section writing loop — bounded packages, two rounds, honest delivery.

A writer package may only cite evidence and materials the frozen brief
already carries, pinned by fingerprint; a Results-kind section without
user-supplied materials is a validation error unless explicitly
placeholder-only (structure + analysis plan + marked placeholders — the
one documented allowed shape). The review loop terminates: at most TWO
automatic Writer revision rounds, then delivery lists the unresolved
findings instead of looping.
"""

from .brief import freeze

RESULTS_KINDS = ("results", "preliminary-results")
MAX_AUTO_ROUNDS = 2


# -- writer packages ----------------------------------------------------------

def new_package(section, brief_fingerprint, evidence_refs=(), material_ids=(),
                placeholder_only=False):
    return {
        "section": section,
        "brief_fingerprint": brief_fingerprint,
        "evidence": list(evidence_refs),
        "materials": list(material_ids),
        "placeholder_only": bool(placeholder_only),
    }


def validate_package(package, brief):
    """Return violations; empty means the package may go to palace-writer."""
    if not isinstance(package, dict):
        return ["package must be a dict"]
    errors = []
    try:
        fingerprint = freeze(brief)["fingerprint"]
    except ValueError as error:
        return ["brief is not freezable: %s" % error]
    if package.get("brief_fingerprint") != fingerprint:
        errors.append("package is pinned to a different (stale?) brief fingerprint")
    sections = {s["name"]: s for s in brief["sections"]}
    section = sections.get(package.get("section"))
    if section is None:
        errors.append("section %r is not in the brief's plan" % package.get("section"))
    allowed_refs = {entry["ref"] for entry in brief.get("evidence") or []}
    for ref in package.get("evidence") or []:
        if ref not in allowed_refs:
            errors.append(
                "evidence %r is outside the frozen brief — writers never "
                "expand retrieval scope" % ref
            )
    allowed_materials = set(brief.get("materials") or [])
    for material_id in package.get("materials") or []:
        if material_id not in allowed_materials:
            errors.append("material %r is not in the frozen brief" % material_id)
    if (
        section is not None
        and section.get("kind") in RESULTS_KINDS
        and not package.get("materials")
        and not package.get("placeholder_only")
    ):
        errors.append(
            "a %s section without user-supplied materials must be "
            "placeholder_only (structure, analysis plan, marked "
            "placeholders) — results are never fabricated" % section["kind"]
        )
    return errors


# -- the two-round review loop -------------------------------------------------

class SectionLoop:
    """draft → review → (revise → review, at most twice) → deliver."""

    def __init__(self, section):
        self.section = section
        self.state = "planned"
        self.rounds = 0
        self.findings = []
        self.history = []

    def _step(self, event, allowed):
        if self.state not in allowed:
            raise ValueError(
                "%s not allowed in state %r" % (event, self.state)
            )
        self.history.append(event)

    def record_draft(self):
        self._step("draft", ("planned",))
        self.state = "drafted"

    def record_review(self, findings):
        self._step("review", ("drafted", "revised"))
        self.findings = list(findings)
        self.state = "reviewed"

    def record_revision(self):
        self._step("revise", ("reviewed",))
        if not self.findings:
            raise ValueError("nothing to revise: the last review was clean")
        if self.rounds >= MAX_AUTO_ROUNDS:
            raise ValueError(
                "at most %d automatic revision rounds — deliver with the "
                "unresolved findings listed" % MAX_AUTO_ROUNDS
            )
        self.rounds += 1
        self.state = "revised"

    def deliver(self):
        self._step("deliver", ("reviewed",))
        self.state = "delivered"
        return {
            "section": self.section,
            "status": "clean" if not self.findings else "unresolved",
            "unresolved": list(self.findings),
            "rounds": self.rounds,
        }
