"""The new-ingest binding rule: every NEW Claim binds ≥1 concrete Concept.

``acquisition.transaction.save_paper`` applies it to the Claims a save adds;
historical Claims stay valid unchanged. This module never writes anything.
"""


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

