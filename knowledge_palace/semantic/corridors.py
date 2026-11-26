"""Typed corridor prefilter over the Graph Index payload (index-only).

A corridor is a typed cross-domain connection: either a Bridge node whose
endpoint domain-closure covers both domains (a single multi-domain endpoint
suffices), or a shared-axis Concept (pattern / function / failure-mode)
attached to nodes on both sides.
Descriptors carry node ids and edge kinds ONLY — never card content.
Corridors are ranked bridge cards first, then shared-axis concepts by strength.
``find_corridors`` is the capped prefilter (≤15) for Idea/Ask prompts;
``corridor_view`` is the bridges view, paged by a byte budget and an offset, so
every corridor can be reached.
This is an internal prefilter, NOT a GraphQueryPort operation: the frozen
frozen port contract is untouched.
"""

SHARED_AXES = ("pattern", "function", "failure-mode")
CORRIDOR_CAP = 15
_ATTACH_KINDS = tuple("tag:" + axis for axis in SHARED_AXES) + ("concerns",)
_ENDPOINT_KINDS = ("work", "gap")
_SAMPLE = 3


def domain_resolver(payload):
    """node id → frozenset of domain node ids (memoized).

    A node belongs to the domains reached through its parents and through its
    own `tag:domain` targets. A tagged target may be a sub-domain concept, so it
    is resolved the same way rather than counted as a domain itself.
    """
    nodes = payload["nodes"]
    upward = {node_id: list(parents) for node_id, parents in payload["parents"].items()}
    for edge in payload["edges"]:
        if edge["kind"] == "tag:domain":
            upward.setdefault(edge["from"], []).append(edge["to"])
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
        found = frozenset().union(*(roots(up) for up in upward.get(node_id, [])))
        memo[node_id] = found
        return found

    return roots


def find_corridors(payload, domain_a, domain_b, cap=CORRIDOR_CAP):
    """Bounded, deterministic typed corridors between two domain slugs.

    Returns {"total", "returned", "truncated", "corridors": [...]} where each
    corridor is {"kind": "bridge"|"shared-axis", ...id-only fields...}.
    Bridge cards come first, then shared-axis concepts by strength (see
    ``all_corridors``), so a capped result keeps the strongest corridors.
    """
    cap = max(1, min(int(cap), CORRIDOR_CAP))
    corridors = all_corridors(payload, domain_a, domain_b)
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


def corridor_view(payload, domain_a, domain_b, budget=24000, offset=0, axis=None, full=False):
    """The bridges view: every corridor between two domains, paged by bytes.

    Detailed rows start at ``offset`` and fill ``budget`` bytes of compact JSON.
    Corridors past the detailed rows still appear in ``more`` as one short row
    each (via, axis, endpoint counts) while the budget lasts, so the reader sees
    the whole list; ``next_offset`` continues the detailed rows. ``by_axis``
    counts every corridor, shown or not. ``axis`` keeps one shared axis (or
    ``bridge``); ``full`` returns every corridor in detail.
    """
    import json

    corridors = all_corridors(payload, domain_a, domain_b)
    counts = {}
    for corridor in corridors:
        key = "bridge" if corridor["kind"] == "bridge" else corridor["axis"]
        counts[key] = counts.get(key, 0) + 1
    if axis:
        corridors = [c for c in corridors if (c["kind"] == "bridge" and axis == "bridge") or c.get("axis") == axis]
    total = len(corridors)
    offset = max(0, min(int(offset or 0), total))
    base = {"domain_a": domain_a, "domain_b": domain_b, "total": total, "by_axis": counts,
            "order": "bridge cards first, then shared-axis concepts by min(endpoints_a, endpoints_b), then total endpoints"}
    if axis:
        base["axis"] = axis
    if full:
        return {**base, "offset": 0, "returned": total, "truncated": False, "corridors": corridors, "more": [],
                "next_offset": None, "note": "Complete list."}
    size = lambda value: len(json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
    used, detailed = 0, []
    for corridor in corridors[offset:]:
        cost = size(corridor) + 1
        if detailed and used + cost > budget * 0.75:
            break
        detailed.append(corridor)
        used += cost
    rest = corridors[offset + len(detailed):]
    more = []
    for corridor in rest:
        row = ({"via": corridor["via"], "kind": "bridge"} if corridor["kind"] == "bridge" else
               {"via": corridor["via"], "axis": corridor["axis"], "a": corridor["endpoints_a"], "b": corridor["endpoints_b"]})
        cost = size(row) + 1
        if used + cost > budget:
            break
        more.append(row)
        used += cost
    unseen = len(rest) - len(more)
    next_offset = offset + len(detailed) if rest else None
    note = "Showing corridors %d–%d of %d in detail." % (offset + 1, offset + len(detailed), total) if detailed else "No corridors at this offset."
    if more:
        note += " %d more are listed briefly in `more`." % len(more)
    if unseen:
        note += " %d more are beyond the byte budget." % unseen
    if offset:
        note += " %d stronger corridors precede this page." % offset
    if next_offset is not None:
        note += " Continue with offset=%d (or filter with axis=pattern|function|failure-mode|bridge)." % next_offset
    return {**base, "offset": offset, "returned": len(detailed), "truncated": bool(rest) or offset > 0,
            "corridors": detailed, "more": more, "unseen": unseen, "next_offset": next_offset, "note": note}


def all_corridors(payload, domain_a, domain_b):
    """Every typed corridor between two domain slugs, strongest first."""
    node_a, node_b = "domain:" + domain_a, "domain:" + domain_b
    domains_of = domain_resolver(payload)
    corridors = []

    # 1) Bridge corridors: a bridge node whose edge endpoints span both.
    bridge_targets = {}
    for edge in payload["edges"]:
        if payload["nodes"].get(edge["from"], {}).get("kind") == "bridge":
            bridge_targets.setdefault(edge["from"], []).append(edge)
    for bridge_id in sorted(bridge_targets):
        touched = frozenset().union(
            *(domains_of(edge["to"]) for edge in bridge_targets[bridge_id])
        )
        if node_a in touched and node_b in touched:
            corridors.append(
                {
                    "kind": "bridge",
                    "via": bridge_id,
                    "edges": sorted(
                        "%s->%s" % (edge["kind"], edge["to"])
                        for edge in bridge_targets[bridge_id]
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
    # Strongest first: a concept attached on both sides by many works is a wider
    # corridor than one with a single endpoint on either side.
    def strength(item):
        rank, concept_id, entry = item
        weakest = min(entry["endpoints_a"], entry["endpoints_b"])
        return (-weakest, -(entry["endpoints_a"] + entry["endpoints_b"]), rank, concept_id)

    corridors.extend(entry for _, _, entry in sorted(shared, key=strength))
    return corridors
