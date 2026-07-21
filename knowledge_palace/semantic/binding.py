"""The new-ingest binding rule: every NEW Claim binds ≥1 concrete Concept.

Applies to paper-card DRAFTS at ingest-validation time (the orchestrator
runs it before the packaged confirmation). Historical cards are exempt by
design — their backfill arrives via separate migration packets. This module
never writes anything.
"""

from ..graph.identity import parse_claims


def validate_claims(claims, registry):
    """Validate parsed claims against the concept registry.

    Returns a typed report:
    ``{"ok", "bound": [n], "unbound": [(n, reason)], "unknown": [(n, [slugs])]}``
    — a draft with ANY unbound claim or unknown slug fails the rule.
    """
    report = {"bound": [], "unbound": [], "unknown": []}
    for claim in claims:
        concepts = claim.get("concepts") or []
        if not concepts:
            report["unbound"].append((claim["n"], "no concept binding"))
            continue
        missing = sorted(slug for slug in concepts if slug not in registry)
        if missing:
            report["unknown"].append((claim["n"], missing))
            continue
        report["bound"].append(claim["n"])
    report["ok"] = not report["unbound"] and not report["unknown"]
    return report


def validate_draft(body, registry, origin="draft"):
    """Parse a draft body's claims and apply the binding rule in one step."""
    claims, parse_problems = parse_claims(body, origin)
    report = validate_claims(claims, registry)
    report["parse_problems"] = parse_problems
    report["claims"] = len(claims)
    report["ok"] = report["ok"] and not parse_problems and bool(claims)
    if not claims:
        report["unbound"].append((0, "draft contains no claims"))
    return report
