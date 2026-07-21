"""Deterministic id-only retrieval over the Graph Index payload.

Question terms (minus injected policy stopwords) match concept/work/gap
labels and slugs by substring (recall-over-precision; rank + cap
deprioritize accidental hits); matched concepts pull in their attached
works/gaps; when the hits span multiple domains, shared-axis corridors add
their sampled endpoints so cross-domain questions reach foreign material. Output is a
bounded (≤15), deterministically ordered list of id/locator descriptors —
the whole Vault never loads, and palace-analyst receives ids to drill
selectively through the port.
"""

import re
from itertools import combinations

from ..semantic.corridors import _domain_resolver, find_corridors

CANDIDATE_CAP = 15
_TOKEN = re.compile(r"[a-z0-9][a-z0-9-]{2,}")
# Question scaffolding only — DOMAIN policy stopwords (PALACE.md hub list)
# are injected by the orchestrator, never hard-coded here.
DEFAULT_STOPWORDS = frozenset(
    "the and for are was were what how why when where which does with from "
    "into over under between about can could should would there their this "
    "that these those has have had been being will its our your".split()
)
_CANDIDATE_KINDS = ("work", "gap")


def extract_terms(question, stopwords=()):
    """Ordered, deduplicated lowercase tokens, policy stopwords removed."""
    banned = DEFAULT_STOPWORDS | {str(s).lower() for s in stopwords}
    seen = []
    for token in _TOKEN.findall(question.lower()):
        if token not in banned and token not in seen:
            seen.append(token)
    return seen


def _matches(term, node_id, node):
    return term in node["label"].lower() or term in node_id.lower()


def find_candidates(payload, question, stopwords=(), cap=CANDIDATE_CAP):
    """Bounded deterministic candidate descriptors for one question."""
    cap = max(1, min(int(cap), CANDIDATE_CAP))
    terms = extract_terms(question, stopwords)
    reasons = {}  # node_id -> set of reason strings

    def add(node_id, reason):
        node = payload["nodes"].get(node_id)
        if node and node["kind"] in _CANDIDATE_KINDS:
            reasons.setdefault(node_id, set()).add(reason)

    for node_id in sorted(payload["nodes"]):
        node = payload["nodes"][node_id]
        for term in terms:
            if not _matches(term, node_id, node):
                continue
            if node["kind"] in _CANDIDATE_KINDS:
                add(node_id, "term:" + term)
            elif node["kind"] == "concept":
                # Attached works/gaps join via edges and placement parents.
                # ponytail: O(terms×concepts×edges) rescans — fine under the
                # cap at personal scale; pre-index edges by target if the
                # 5k-work ceiling ever makes this measurable.
                for edge in payload["edges"]:
                    if edge["to"] == node_id:
                        add(edge["from"], "concept:%s (term:%s)" % (node_id, term))
                for child, parents in payload["parents"].items():
                    if node_id in parents:
                        add(child, "concept:%s (term:%s)" % (node_id, term))

    # Cross-domain augmentation: when hits span domains, typed corridors
    # contribute their sampled endpoints.
    domains_of = _domain_resolver(payload)
    hit_domains = sorted(
        {d.split(":", 1)[1] for nid in reasons for d in domains_of(nid)}
    )
    for domain_a, domain_b in combinations(hit_domains, 2):
        result = find_corridors(payload, domain_a, domain_b)
        for corridor in result["corridors"]:
            if corridor["kind"] != "shared-axis":
                continue
            for side in ("side_a", "side_b"):
                for node_id in corridor[side]:
                    add(node_id, "corridor:%s" % corridor["via"])

    ranked = sorted(
        reasons.items(), key=lambda item: (-len(item[1]), item[0])
    )[:cap]
    return [
        {
            "node_id": node_id,
            "canonical_ref": dict(payload["nodes"][node_id].get("canonical_ref") or {}),
            "why": sorted(why),
        }
        for node_id, why in ranked
    ]
