"""ProjectSource — author-supplied references, Vault-first (pure, no I/O).

A reference the user brings resolves against Vault identity FIRST:
a hit reuses the existing Work — never a duplicate
identity; a miss becomes a verified session-local Project Source that can
participate in novelty comparison and citation but never auto-enters the
Vault (formal ingestion later is a separate user-initiated ingest flow).
The external novelty check is a recorded user opt-in bounded to one hop
and ≤20 candidates — this module records and validates the decision; any
live search is orchestrator territory under that record.
"""

from ..expansion.candidates import build_hit_index, candidate_key, vault_hit

PROJECT_SOURCE_PREFIX = "project-source:"
EXTERNAL_HOPS = 1
EXTERNAL_MAX_CANDIDATES = 20


def resolve(reference, vault_identity):
    """Vault Hit (existing work id) or a quarantined Project Source record."""
    slug = vault_hit(reference, build_hit_index(vault_identity))
    if slug:
        return {"kind": "vault-hit", "work": "work:" + slug}
    key = candidate_key(reference)
    if key is None:
        raise ValueError("a reference needs an external id or at least a title")
    ids = {k: v for k, v in (reference.get("ids") or {}).items() if v}
    return {
        "kind": "project-source",
        "ref": PROJECT_SOURCE_PREFIX + key,
        "ids": ids,
        "title": reference.get("title"),
        "year": reference.get("year"),
        # Same mechanical bar as expansion candidates: identity-verified
        # only with at least one external id.
        "verified": bool(ids),
        "project_local": True,
        "auto_ingest": False,
    }


def validate_source(source):
    """Return violations; empty means usable in an IdeaAssessment."""
    if not isinstance(source, dict):
        return ["project source must be a dict"]
    errors = []
    if source.get("kind") != "project-source":
        errors.append("kind must be 'project-source' (vault hits reuse the work id)")
    if not str(source.get("ref") or "").startswith(PROJECT_SOURCE_PREFIX):
        errors.append("ref must carry the %r prefix" % PROJECT_SOURCE_PREFIX)
    if not source.get("verified"):
        errors.append("a project source needs a verified identity (external id)")
    if source.get("project_local") is not True:
        errors.append("a project source must stay project-local")
    if source.get("auto_ingest") is not False:
        errors.append("a project source can never auto-ingest into the Vault")
    return errors


def new_request(session_id, scope, date, user_confirmed=False,
                max_candidates=EXTERNAL_MAX_CANDIDATES):
    """Record the external-novelty opt-in; refuses without confirmation."""
    if not user_confirmed:
        raise ValueError(
            "the external novelty check is a user opt-in: it requires an "
            "explicit user confirmation"
        )
    if not (session_id and scope and date):
        raise ValueError("session_id, scope, and date are required")
    return {
        "session_id": session_id,
        "scope": scope,
        "date": date,
        "hops": EXTERNAL_HOPS,
        "max_candidates": max(1, min(int(max_candidates), EXTERNAL_MAX_CANDIDATES)),
        "user_confirmed": True,
    }


def validate_request(request):
    """Return violations; empty means the recorded opt-in is well-formed."""
    if not isinstance(request, dict):
        return ["request must be a dict"]
    errors = []
    for key in ("session_id", "scope", "date"):
        if not request.get(key):
            errors.append("missing %s" % key)
    if request.get("hops") != EXTERNAL_HOPS:
        errors.append("external search is bounded to exactly %d hop" % EXTERNAL_HOPS)
    try:
        max_candidates = int(request.get("max_candidates") or 0)
    except (TypeError, ValueError):
        max_candidates = 0
    if not 1 <= max_candidates <= EXTERNAL_MAX_CANDIDATES:
        errors.append("max_candidates must be 1..%d" % EXTERNAL_MAX_CANDIDATES)
    if request.get("user_confirmed") is not True:
        errors.append("the opt-in must record an explicit user confirmation")
    return errors
