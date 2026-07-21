"""CoverageReport — the answer gate. Schema + validator (pure, no I/O).

The analyst judges coverage; this module enforces what a verdict may
imply: ``sufficient`` answers everything from evidence, ``partial`` answers
the covered part and MUST name its holes, ``insufficient`` answers nothing
as Vault-grounded and MUST carry an ExpansionProposal reference. Evidence
is id-shaped (index node ids), never card text. External sources are
session-local by construction and never Vault-eligible.
"""

VERDICTS = ("sufficient", "partial", "insufficient")
SUB_STATUSES = ("covered", "hole")
ID_PREFIXES = ("claim:", "work:", "gap:", "concept:", "transfer:", "domain:")


def new_subquestion(text, status, evidence=()):
    return {"text": text, "status": status, "evidence": list(evidence)}


def new_external_source(locator, note=""):
    """External material carries its quarantine flags from birth."""
    return {
        "locator": locator,
        "note": note,
        "session_local": True,
        "vault_eligible": False,
    }


def new_report(verdict, subquestions, proposal_ref=None, external_sources=None):
    return {
        "verdict": verdict,
        "subquestions": list(subquestions),
        "proposal_ref": proposal_ref,
        "external_sources": list(external_sources or []),
    }


def holes(report):
    return [s["text"] for s in report.get("subquestions", []) if s.get("status") == "hole"]


def validate_report(report, payload=None):
    """Return a list of violations; empty means conforming.

    ``payload`` (a Graph Index payload) is optional: when given, evidence
    ids must resolve to existing nodes.
    """
    errors = []
    if not isinstance(report, dict):
        return ["report must be a dict"]
    verdict = report.get("verdict")
    if verdict not in VERDICTS:
        errors.append("verdict %r not in %s" % (verdict, list(VERDICTS)))
    subquestions = report.get("subquestions")
    if not isinstance(subquestions, list) or not subquestions:
        return errors + ["subquestions must be a non-empty list"]

    covered = 0
    hole_count = 0
    for index, sub in enumerate(subquestions):
        where = "subquestions[%d]" % index
        if not (isinstance(sub, dict) and sub.get("text")):
            errors.append("%s: needs a text" % where)
            continue
        status = sub.get("status")
        if status not in SUB_STATUSES:
            errors.append("%s: status %r not in %s" % (where, status, list(SUB_STATUSES)))
            continue
        evidence = sub.get("evidence") or []
        if status == "covered":
            covered += 1
            if not evidence:
                errors.append("%s: covered without evidence" % where)
        else:
            hole_count += 1
        for ref in evidence:
            if not (isinstance(ref, str) and ref.startswith(ID_PREFIXES)):
                errors.append("%s: evidence %r is not an index id" % (where, ref))
            elif payload is not None and ref not in payload["nodes"]:
                errors.append("%s: evidence %r not in the index" % (where, ref))

    if verdict == "sufficient" and hole_count:
        errors.append("sufficient verdict cannot carry holes (%d found)" % hole_count)
    if verdict == "partial" and (covered == 0 or hole_count == 0):
        errors.append(
            "partial verdict requires >=1 covered AND >=1 hole "
            "(covered=%d holes=%d)" % (covered, hole_count)
        )
    if verdict == "insufficient":
        if covered:
            errors.append(
                "insufficient verdict must not present Vault-grounded answers "
                "(%d covered subquestions)" % covered
            )
        if not report.get("proposal_ref"):
            errors.append("insufficient verdict requires an ExpansionProposal reference")

    for index, source in enumerate(report.get("external_sources") or []):
        where = "external_sources[%d]" % index
        if not isinstance(source, dict) or not source.get("locator"):
            errors.append("%s: needs a locator" % where)
            continue
        if source.get("session_local") is not True:
            errors.append("%s: external material must be session_local" % where)
        if source.get("vault_eligible") is not False:
            errors.append("%s: external material can never be vault_eligible" % where)
    return errors
