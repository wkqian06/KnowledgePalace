"""Novelty — profile-relative, bounded, vault-relative by default.

Novelty is never a uniform "is the method new": a
per-project NoveltyProfile selects the dimensions on which novelty is even
claimed. The coarse-to-fine pipeline bounds what reaches the prompt —
≤10 novelty corridors → ≤15 closest works → ≤30 related claims,
deterministic and id-only with honest per-stage truncation counts. The
IdeaAssessment schema controls what a judgment may claim: falsifiers and
a minimal experiment are required, novelty verdicts land only on selected
dimensions and are vault-relative by definition of the field,
graph-synthesis "possible novelty" stays separate from literature fact,
and external-novelty statements validate only under a recorded opt-in
request whose scope and date the wording must reference.
"""

from itertools import combinations

from ..semantic.corridors import _domain_resolver, find_corridors
from .coverage import ID_PREFIXES
from .prefilter import find_candidates
from .project_source import PROJECT_SOURCE_PREFIX, validate_request

NOVELTY_DIMENSIONS = (
    "theory",
    "mechanism",
    "method",
    "data",
    "evaluation",
    "empirical-finding",
    "system-integration",
    "application-transfer",
    "scale-generalization",
)
CORRIDOR_CAP = 10
WORK_CAP = 15
CLAIM_CAP = 30
_REF_PREFIXES = ID_PREFIXES + (PROJECT_SOURCE_PREFIX,)


# -- NoveltyProfile -----------------------------------------------------------

def new_profile(project_id, dimensions):
    return {"project_id": project_id, "dimensions": list(dimensions)}


def validate_profile(profile):
    """Return violations; empty means novelty may be claimed on these dims."""
    if not isinstance(profile, dict):
        return ["profile must be a dict"]
    errors = []
    if not profile.get("project_id"):
        errors.append("missing project_id")
    dimensions = profile.get("dimensions")
    if not isinstance(dimensions, list) or not dimensions:
        errors.append("dimensions must be a non-empty selection")
        return errors
    for dimension in dimensions:
        if dimension not in NOVELTY_DIMENSIONS:
            errors.append(
                "dimension %r not in %s" % (dimension, list(NOVELTY_DIMENSIONS))
            )
    if len(set(dimensions)) != len(dimensions):
        errors.append("duplicate dimensions")
    return errors


# -- Coarse-to-fine pipeline --------------------------------------------------

def novelty_pipeline(payload, idea_text, stopwords=()):
    """Bounded id-only drill: corridors → closest works → related claims.

    Each stage reports {total, returned, truncated} honestly; nothing in
    the result is card text — the analyst drills ids through the port.
    """
    hits = find_candidates(payload, idea_text, stopwords)
    domains_of = _domain_resolver(payload)
    hit_domains = sorted(
        {d.split(":", 1)[1] for hit in hits for d in domains_of(hit["node_id"])}
    )

    corridors = []
    for domain_a, domain_b in combinations(hit_domains, 2):
        for corridor in find_corridors(payload, domain_a, domain_b)["corridors"]:
            # A transfer spanning 3+ hit domains repeats identically for
            # every pair — dedup by descriptor (shared-axis entries carry
            # distinct sides per pair and survive naturally).
            if corridor not in corridors:
                corridors.append(corridor)
    corridor_total = len(corridors)  # distinct corridors enumerated
    corridors = corridors[:CORRIDOR_CAP]

    seen, works = set(), []

    def add_work(node_id, why):
        node = payload["nodes"].get(node_id)
        if not node or node["kind"] != "work" or node_id in seen:
            return
        seen.add(node_id)
        works.append(
            {
                "node_id": node_id,
                "canonical_ref": dict(node.get("canonical_ref") or {}),
                "why": why,
            }
        )

    for hit in hits:
        add_work(hit["node_id"], list(hit["why"]))
    for corridor in corridors:
        reason = ["corridor:%s" % corridor["via"]]
        for side in ("side_a", "side_b"):
            for node_id in corridor.get(side) or []:
                add_work(node_id, reason)
        for spec in corridor.get("edges") or []:  # transfer endpoints
            add_work(spec.split("->", 1)[1], reason)
    work_total = len(works)
    works = works[:WORK_CAP]

    claims_by_work = {}
    for edge in payload["edges"]:
        if edge["kind"] == "claims":
            claims_by_work.setdefault(edge["from"], []).append(edge["to"])
    claims, claim_total = [], 0
    for work in works:
        for claim_id in sorted(claims_by_work.get(work["node_id"], [])):
            claim_total += 1
            if len(claims) < CLAIM_CAP:
                claims.append(claim_id)

    return {
        "corridors": {
            "total": corridor_total,
            "returned": corridors,
            "truncated": corridor_total > len(corridors),
        },
        "works": {
            "total": work_total,
            "returned": works,
            "truncated": work_total > len(works),
        },
        "claims": {
            "total": claim_total,
            "returned": claims,
            "truncated": claim_total > len(claims),
        },
    }


# -- IdeaAssessment -----------------------------------------------------------

def new_assessment(
    profile,
    minimal_experiment,
    falsifiers,
    supporting=(),
    opposing=(),
    unknown=(),
    closest_prior_work=(),
    alternative_hypotheses=(),
    novelty=None,
    possible_novelty=(),
    external=None,
):
    return {
        "profile": profile,
        "minimal_experiment": minimal_experiment,
        "falsifiers": list(falsifiers),
        "supporting": list(supporting),
        "opposing": list(opposing),
        "unknown": list(unknown),
        "closest_prior_work": list(closest_prior_work),
        "alternative_hypotheses": list(alternative_hypotheses),
        # Vault-relative by definition of the field; external-scope claims
        # live ONLY under `external` and its recorded opt-in.
        "novelty": dict(novelty or {}),
        "possible_novelty": list(possible_novelty),
        "external": external,
    }


def _check_refs(refs, field, payload, errors):
    for ref in refs:
        if not (isinstance(ref, str) and ref.startswith(_REF_PREFIXES)):
            errors.append(
                "%s: %r is not an index id or project-source ref" % (field, ref)
            )
        elif (
            payload is not None
            and not ref.startswith(PROJECT_SOURCE_PREFIX)
            and ref not in payload["nodes"]
        ):
            errors.append("%s: %r not in the index" % (field, ref))


def validate_assessment(assessment, payload=None):
    """Return a list of violations; empty means conforming.

    ``payload`` (a Graph Index payload) is optional: when given, index
    evidence refs must resolve to existing nodes.
    """
    if not isinstance(assessment, dict):
        return ["assessment must be a dict"]
    errors = []
    profile = assessment.get("profile")
    errors.extend(validate_profile(profile))
    if not assessment.get("minimal_experiment"):
        errors.append("a minimal validation experiment is required")
    if not assessment.get("falsifiers"):
        errors.append("falsifiers/kill criteria are required")
    for field in ("supporting", "opposing", "closest_prior_work"):
        _check_refs(assessment.get(field) or [], field, payload, errors)

    selected = set((profile or {}).get("dimensions") or []) if isinstance(profile, dict) else set()
    novelty = assessment.get("novelty") or {}
    if not isinstance(novelty, dict):
        errors.append("novelty must be a dict of dimension -> verdict")
        novelty = {}
    for dimension, statement in sorted(novelty.items()):
        if dimension not in selected:
            errors.append(
                "novelty verdict on %r, which the profile did not select" % dimension
            )
        if not statement:
            errors.append("novelty[%s]: empty verdict" % dimension)

    external = assessment.get("external")
    if external is not None:
        request = external.get("request") if isinstance(external, dict) else None
        request_errors = (
            validate_request(request) if request else ["missing request record"]
        )
        if request_errors:
            errors.append(
                "external novelty without a confirmed opt-in request: %s"
                % request_errors
            )
        else:
            statements = external.get("statements") or []
            if not isinstance(statements, list):
                errors.append("external statements must be a list")
                statements = []
            for statement in statements:
                if request["scope"] not in statement or request["date"] not in statement:
                    errors.append(
                        "external statement must reference the recorded search "
                        "scope and date: %r" % statement
                    )
    return errors
