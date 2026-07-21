"""StudyProfile — an optional methodology VIEW, never a second store.

Roles are claim references only; every field resolves back to an anchored
Claim of the same work. A work whose roles fit no set (or that has no
roles) gets no profile. Role vocabularies:
empirical / review / theoretical.
"""

import re

ROLE_SETS = {
    "empirical": ("subjects", "method", "comparator", "outcomes", "limitations"),
    "review": ("corpus", "selection", "synthesis"),
    "theoretical": ("assumptions", "mechanism", "predictions", "validation"),
}
_CLAIM_REF = re.compile(r"^C\d+$")


def classify_roles(roles):
    """(profile kind, errors). Roles must fit exactly one role set."""
    if not roles:
        return None, []
    matches = [
        kind
        for kind, fields in ROLE_SETS.items()
        if set(roles) <= set(fields)
    ]
    if not matches:
        return None, [
            "roles %s fit no role set (empirical/review/theoretical)"
            % sorted(roles)
        ]
    return matches[0], []


def validate_profile(work_slug, roles, claims):
    """Typed report for one work's profile roles against its parsed claims.

    ``claims`` is the identity claims dict (``<slug>#C<n>`` keys).
    """
    kind, errors = classify_roles(roles)
    for role, refs in sorted(roles.items()):
        if not refs:
            errors.append("role %r has no claim references" % role)
        for ref in refs:
            if not _CLAIM_REF.match(ref):
                errors.append(
                    "role %r value %r is not a claim reference — profiles "
                    "never carry free-text facts" % (role, ref)
                )
                continue
            if "%s#%s" % (work_slug, ref) not in claims:
                errors.append("role %r references missing claim %s" % (role, ref))
    return {"ok": not errors and kind is not None, "kind": kind, "errors": errors}


def build_profile_view(work_slug, roles, claims):
    """Resolve a VALID profile to quotes+anchors. Returns None when the work
    has no roles; raises ValueError on an invalid profile."""
    if not roles:
        return None
    report = validate_profile(work_slug, roles, claims)
    if not report["ok"]:
        raise ValueError("invalid profile for %s: %s" % (work_slug, report["errors"]))
    resolved = {}
    for role, refs in sorted(roles.items()):
        resolved[role] = [
            {
                "claim": "%s#%s" % (work_slug, ref),
                "quote": claims["%s#%s" % (work_slug, ref)]["quote"],
                "anchor": claims["%s#%s" % (work_slug, ref)]["anchor"],
            }
            for ref in refs
        ]
    return {"work": work_slug, "kind": report["kind"], "roles": resolved}
