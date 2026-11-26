"""Read-only two-hop hierarchy projection over the rebuildable Graph Index.

This projection is deliberately separate from the frozen five-operation
GraphQueryPort.  Hops follow only the index's parent relation: ancestors are
parents/grandparents and descendants are children/grandchildren.
"""
import argparse
import json
import sys

from .builder import GQP_VERSION, load_index
from ..tools.config_resolver import resolve_roots

DEFAULT_MAX_NODES = 2000
MAX_MAX_NODES = 5000
BAND_ORDER = ("grandparents", "parents", "center", "children", "grandchildren")


def _view(node_id, nodes):
    node = nodes[node_id]
    attrs = node.get("attrs") or {}
    return {
        "id": node_id,
        "kind": node.get("kind") or "unknown",
        "label": node.get("label") or node_id,
        "year": attrs.get("year"),
    }


def build_neighborhood(state, node_id, max_nodes=DEFAULT_MAX_NODES):
    document = load_index(state)
    if document is None:
        raise FileNotFoundError("Graph Index is missing; rebuild it before requesting a neighborhood")
    payload = document["payload"]
    nodes = payload["nodes"]
    if node_id not in nodes:
        return {
            "schema_version": GQP_VERSION,
            "snapshot": dict(document["snapshot"]),
            "error": {"code": "unknown_node", "message": "no node %r" % node_id, "evidence": None},
        }

    cap = max(1, min(int(max_nodes), MAX_MAX_NODES))
    parents = {child: sorted(set(values)) for child, values in payload["parents"].items()}
    children = {}
    for child, values in parents.items():
        for parent in values:
            if parent in nodes and child in nodes:
                children.setdefault(parent, []).append(child)
    for parent in children:
        children[parent] = sorted(set(children[parent]))

    direct_parents = [value for value in parents.get(node_id, []) if value in nodes and value != node_id]
    direct_children = [value for value in children.get(node_id, []) if value != node_id]
    parent_set = set(direct_parents)
    child_set = set(direct_children)
    grandparents = sorted({value for parent in direct_parents for value in parents.get(parent, [])
                           if value in nodes and value != node_id and value not in parent_set})
    grandchildren = sorted({value for child in direct_children for value in children.get(child, [])
                            if value != node_id and value not in child_set})

    raw = {
        "grandparents": grandparents,
        "parents": sorted(parent_set),
        "center": [node_id],
        "children": sorted(child_set),
        "grandchildren": grandchildren,
    }
    warnings = []
    overlaps = (set(grandparents) | parent_set) & (child_set | set(grandchildren))
    if overlaps:
        warnings.append("Hierarchy cycle or bidirectional ancestry detected for: %s" % ", ".join(sorted(overlaps)[:20]))

    # Stable closest-first admission keeps the center and one-hop context useful
    # under the safety cap.  The response exposes exact omitted counts.
    admission_order = ("center", "parents", "children", "grandparents", "grandchildren")
    remaining = cap
    kept = {}
    omitted = {}
    admitted = set()
    for band in admission_order:
        unique = [value for value in raw[band] if value not in admitted]
        take = unique[:remaining]
        kept[band] = take
        admitted.update(take)
        omitted[band] = len(unique) - len(take)
        remaining -= len(take)
    for band in BAND_ORDER:
        kept.setdefault(band, [])
        omitted.setdefault(band, 0)

    links = {}
    for child, values in parents.items():
        if child not in admitted:
            continue
        for parent in values:
            if parent in admitted and parent != child:
                edge_id = "parent|%s|%s" % (parent, child)
                links[edge_id] = {"id": edge_id, "kind": "parent", "from": parent, "to": child}

    bands = []
    distances = {"grandparents": -2, "parents": -1, "center": 0, "children": 1, "grandchildren": 2}
    for band in BAND_ORDER:
        items = [_view(value, nodes) for value in kept[band]]
        by_kind = {}
        for item in items:
            by_kind[item["kind"]] = by_kind.get(item["kind"], 0) + 1
        bands.append({
            "id": band,
            "distance": distances[band],
            "total": len(raw[band]),
            "returned": len(items),
            "omitted": omitted[band],
            "items": items,
            "kind_counts": dict(sorted(by_kind.items())),
        })

    truncated = any(omitted.values())
    if truncated:
        warnings.append("Neighborhood exceeded the %d-node safety cap" % cap)
    return {
        "schema_version": GQP_VERSION,
        "snapshot": dict(document["snapshot"]),
        "center_id": node_id,
        "hop_relation": "parent",
        "max_hops": 2,
        "bands": bands,
        "links": [links[key] for key in sorted(links)],
        "total_nodes": len(set().union(*(set(values) for values in raw.values()))),
        "returned_nodes": len(admitted),
        "truncated": truncated,
        "warnings": warnings,
    }


CITATION_BAND_ORDER = ("sources2", "sources", "center", "citing", "citing2")
CITATION_DISTANCES = {"sources2": -2, "sources": -1, "center": 0, "citing": 1, "citing2": 2}


def build_citation_neighborhood(state, vault, node_id, max_nodes=DEFAULT_MAX_NODES):
    """Two citation hops around one work, in knowledge-flow order.

    ``sources`` are works the center cites (its sources), ``sources2`` the works
    those cite; ``citing`` are works citing the center and ``citing2`` works
    citing those. Edges come from the same Bibliographic Cache overlay the
    visualization draws; coverage is whatever the cache holds.
    """
    from .network import MAP_KINDS, _work_bundle
    from ..viewer.export import citation_overlay

    document = load_index(state)
    if document is None:
        raise FileNotFoundError("Graph Index is missing; rebuild it before requesting a neighborhood")
    payload = document["payload"]
    nodes = payload["nodes"]
    if node_id not in nodes or nodes[node_id].get("kind") != "work":
        return None
    selected = {key for key, node in nodes.items() if node.get("kind") in MAP_KINDS}
    bundle = _work_bundle(vault, payload, selected)
    pairs = [tuple(pair) for pair in citation_overlay(bundle, state)["edges"] if pair[0] in nodes and pair[1] in nodes]
    cites, cited_by = {}, {}
    for citing, cited in pairs:
        cites.setdefault(citing, set()).add(cited)
        cited_by.setdefault(cited, set()).add(citing)
    sources = sorted(cites.get(node_id, set()) - {node_id})
    citing = sorted(cited_by.get(node_id, set()) - {node_id})
    near = {node_id, *sources, *citing}
    sources2 = sorted({w for s in sources for w in cites.get(s, set())} - near)
    citing2 = sorted({w for c in citing for w in cited_by.get(c, set())} - near - set(sources2))
    raw = {"sources2": sources2, "sources": sources, "center": [node_id], "citing": citing, "citing2": citing2}

    cap = max(1, min(int(max_nodes), MAX_MAX_NODES))
    remaining, kept, omitted, admitted = cap, {}, {}, set()
    for band in ("center", "sources", "citing", "sources2", "citing2"):
        unique = [value for value in raw[band] if value not in admitted]
        take = unique[:remaining]
        kept[band] = take
        admitted.update(take)
        omitted[band] = len(unique) - len(take)
        remaining -= len(take)
    links = {}
    for citing_id, cited_id in pairs:
        if citing_id in admitted and cited_id in admitted:
            # Knowledge flow: the cited work feeds the citing one.
            edge_id = "cites|%s|%s" % (citing_id, cited_id)
            links[edge_id] = {"id": edge_id, "kind": "cites", "from": cited_id, "to": citing_id}
    bands = []
    for band in CITATION_BAND_ORDER:
        items = [_view(value, nodes) for value in kept[band]]
        bands.append({"id": band, "distance": CITATION_DISTANCES[band], "total": len(raw[band]),
                      "returned": len(items), "omitted": omitted[band], "items": items})
    warnings = []
    if not sources and not citing:
        warnings.append("No cached citation links for this work; run /palace refresh citations --live to fill reference lists.")
    if any(omitted.values()):
        warnings.append("Citation neighborhood exceeded the %d-node safety cap" % cap)
    return {
        "center_id": node_id,
        "hop_relation": "cites",
        "flow": "sources -> center -> citing",
        "bands": bands,
        "links": [links[key] for key in sorted(links)],
        "total_nodes": len(set().union(*(set(values) for values in raw.values()))),
        "returned_nodes": len(admitted),
        "truncated": any(omitted.values()),
        "warnings": warnings,
    }


def run(argv=None):
    parser = argparse.ArgumentParser(description="Two-hop parent/child hierarchy projection")
    parser.add_argument("node_id")
    parser.add_argument("--config")
    parser.add_argument("--max-nodes", type=int, default=DEFAULT_MAX_NODES)
    parser.add_argument("--citations", action="store_true", help="also return the two-hop citation neighborhood of a work")
    args = parser.parse_args(argv)
    roots = resolve_roots(args.config)
    result = build_neighborhood(roots["state_dir"], args.node_id, args.max_nodes)
    if args.citations and "error" not in result:
        citation = build_citation_neighborhood(roots["state_dir"], roots["vault_dir"], args.node_id, args.max_nodes)
        if citation is not None:
            result["citation"] = citation
    print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(run())
