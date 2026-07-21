"""Typed corridor prefilter over the Graph Index payload (index-only).

A corridor is a typed cross-domain connection: either a Transfer node whose
endpoint domain-closure covers both domains (a single multi-domain endpoint
suffices), or a shared-axis Concept (pattern / function / failure-mode)
attached to nodes on both sides.
Descriptors carry node ids and edge kinds ONLY — never card content — and
the result is bounded (≤15 by default) with honest truncation counts, so an
Idea/Ask prompt can drill selectively instead of loading the Vault.
This is an internal prefilter, NOT a GraphQueryPort operation: the frozen
frozen port contract is untouched.
"""

SHARED_AXES = ("pattern", "function", "failure-mode")
CORRIDOR_CAP = 15
_ATTACH_KINDS = tuple("tag:" + axis for axis in SHARED_AXES) + ("concerns",)
_ENDPOINT_KINDS = ("work", "gap")
_SAMPLE = 3


def _domain_resolver(payload):
    """node id → frozenset of domain node ids, via the parents DAG (memoized)."""
    parents = payload["parents"]
    nodes = payload["nodes"]
    memo = {}

    def roots(node_id):
        if node_id in memo:
            return memo[node_id]
        node = nodes.get(node_id)
        if node is None:
            return frozenset()
        if node["kind"] == "domain":
            memo[node_id] = frozenset((node_id,))
            return memo[node_id]
        memo[node_id] = frozenset()  # cycle guard; parents form a DAG
        found = frozenset().union(
            *(roots(parent) for parent in parents.get(node_id, []))
        ) if parents.get(node_id) else frozenset()
        memo[node_id] = found
        return found

    return roots


def find_corridors(payload, domain_a, domain_b, cap=CORRIDOR_CAP):
    """Bounded, deterministic typed corridors between two domain slugs.

    Returns {"total", "returned", "truncated", "corridors": [...]} where each
    corridor is {"kind": "transfer"|"shared-axis", ...id-only fields...}.
    """
    node_a, node_b = "domain:" + domain_a, "domain:" + domain_b
    cap = max(1, min(int(cap), CORRIDOR_CAP))
    domains_of = _domain_resolver(payload)
    corridors = []

    # 1) Transfer corridors: a transfer node whose edge endpoints span both.
    transfer_targets = {}
    for edge in payload["edges"]:
        if payload["nodes"].get(edge["from"], {}).get("kind") == "transfer":
            transfer_targets.setdefault(edge["from"], []).append(edge)
    for transfer_id in sorted(transfer_targets):
        touched = frozenset().union(
            *(domains_of(edge["to"]) for edge in transfer_targets[transfer_id])
        )
        if node_a in touched and node_b in touched:
            corridors.append(
                {
                    "kind": "transfer",
                    "via": transfer_id,
                    "edges": sorted(
                        "%s->%s" % (edge["kind"], edge["to"])
                        for edge in transfer_targets[transfer_id]
                    ),
                }
            )

    # 2) Shared-axis corridors: one concept attached from both domains.
    attached = {}
    for edge in payload["edges"]:
        if edge["kind"] not in _ATTACH_KINDS:
            continue
        concept = payload["nodes"].get(edge["to"])
        if not concept or concept["kind"] != "concept":
            continue
        if (concept.get("attrs") or {}).get("axis") not in SHARED_AXES:
            continue
        source = payload["nodes"].get(edge["from"], {})
        if source.get("kind") not in _ENDPOINT_KINDS:
            continue
        attached.setdefault(edge["to"], []).append(edge["from"])
    axis_rank = {axis: rank for rank, axis in enumerate(SHARED_AXES)}
    shared = []
    for concept_id in sorted(attached):
        side_a = sorted(
            n for n in set(attached[concept_id]) if node_a in domains_of(n)
        )
        side_b = sorted(
            n for n in set(attached[concept_id]) if node_b in domains_of(n)
        )
        if not side_a or not side_b:
            continue
        axis = (payload["nodes"][concept_id].get("attrs") or {}).get("axis")
        shared.append(
            (
                axis_rank[axis],
                concept_id,
                {
                    "kind": "shared-axis",
                    "axis": axis,
                    "via": concept_id,
                    "side_a": side_a[:_SAMPLE],
                    "side_b": side_b[:_SAMPLE],
                    "endpoints_a": len(side_a),
                    "endpoints_b": len(side_b),
                },
            )
        )
    corridors.extend(entry for _, _, entry in sorted(shared, key=lambda t: (t[0], t[1])))

    total = len(corridors)
    returned = corridors[:cap]
    return {
        "domain_a": domain_a,
        "domain_b": domain_b,
        "total": total,
        "returned": len(returned),
        "truncated": total > len(returned),
        "corridors": returned,
    }
