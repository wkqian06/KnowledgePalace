"""Rich read-only network projection over the rebuildable Graph Index.

The projection keeps hierarchy, semantic, citation and derived-similarity links
separate. It never writes the Vault or Graph Index. A bounded overview selects
nodes before citation joins and pairwise similarity, so UI startup and overview
cost do not grow with the complete semantic graph.
"""

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

from .builder import GQP_VERSION, load_index
from ..tools.config_resolver import resolve_roots

MAP_KINDS = {"domain", "concept", "work", "gap", "bridge"}
_CITATIONS = re.compile(r"^citations:\s*(\d+)", re.MULTILINE)
_DOMAIN = re.compile(r"^domain:\s*\[([^\]]+)\]", re.MULTILINE)


def _work_metrics(bundle, node_id):
    record = ((bundle or {}).get("contents", {}).get(node_id) or {}).get("content") or ""
    front = record.split("\n---", 1)[0]
    match = _CITATIONS.search(front)
    return int(match.group(1)) if match else None


def _work_primary_domain(bundle, node_id, visible):
    """First domain tag on the card is the author's primary domain.

    The Graph Index keeps every domain tag as an edge but loses tag order, so
    read the selected work's frontmatter instead of guessing from edge order.
    """
    record = ((bundle or {}).get("contents", {}).get(node_id) or {}).get("content") or ""
    match = _DOMAIN.search(record)
    if not match:
        return None
    first = match.group(1).split(",")[0].strip().strip("'\"")
    candidate = "domain:%s" % first if first else None
    return candidate if candidate in visible else None


def _work_bundle(vault, payload, node_ids):
    """Small citation-overlay input for only the works in a bounded overview."""
    root = Path(vault)
    nodes, contents = {}, {}
    for node_id in sorted(node_ids):
        node = payload["nodes"][node_id]
        if node.get("kind") != "work":
            continue
        nodes[node_id] = node
        ref = node.get("canonical_ref") or {}
        relative = ref.get("path")
        if not relative:
            continue
        path = root / relative
        if path.is_file():
            contents[node_id] = {"content": path.read_text(encoding="utf-8")}
    return {"nodes": nodes, "contents": contents}


def _select_overview(visible, payload, adjacency, max_nodes):
    if max_nodes is None or len(visible) <= max_nodes:
        return set(visible)
    kind_rank = {"domain": 0, "concept": 1, "gap": 2, "bridge": 3, "work": 4}
    # Keep every domain when possible, then choose globally connected nodes.
    # The kind rank only breaks equal-degree ties, so prominent works are not
    # starved as concept/gap collections grow.
    domains = sorted(node_id for node_id in visible if payload["nodes"][node_id]["kind"] == "domain")[:max_nodes]
    selected = set(domains)
    candidates = sorted(
        visible - selected,
        key=lambda node_id: (
            -len(adjacency[node_id]),
            kind_rank.get(payload["nodes"][node_id]["kind"], 9),
            node_id,
        ),
    )
    selected.update(candidates[:max_nodes - len(selected)])
    return selected


def build_network(state, vault=None, max_nodes=None, max_links=None):
    document = load_index(state)
    if document is None:
        raise FileNotFoundError("Graph Index is missing; rebuild it before requesting the network")
    payload = document["payload"]
    visible = {
        node_id for node_id, node in payload["nodes"].items()
        if node.get("kind") in MAP_KINDS
    }

    base_links = {}

    def base_link(kind, source, target, link_id=None, attrs=None):
        if source not in visible or target not in visible or source == target:
            return
        key = link_id or "%s|%s|%s" % (kind, source, target)
        base_links[key] = {
            "id": key, "kind": kind, "from": source, "to": target,
            **({"attrs": attrs} if attrs else {}),
        }

    for child, parents in payload["parents"].items():
        for parent in parents:
            base_link("parent", parent, child)
    for edge in payload["edges"]:
        base_link(edge["kind"], edge["from"], edge["to"], edge["id"], edge.get("attrs"))

    base_adjacency = defaultdict(set)
    for link in base_links.values():
        base_adjacency[link["from"]].add(link["to"])
        base_adjacency[link["to"]].add(link["from"])
    selected = _select_overview(visible, payload, base_adjacency, max_nodes)
    bounded = len(selected) < len(visible)

    links = {
        key: link for key, link in base_links.items()
        if link["from"] in selected and link["to"] in selected
    }

    bundle = None
    citation_pairs = []
    if vault is not None:
        from ..viewer.export import citation_overlay
        # A browser overview always uses selected work cards, even when today's
        # library happens to be below the cap; its cost remains tied to the
        # requested overview rather than a recursive GraphQueryPort walk.
        if max_nodes is not None:
            bundle = _work_bundle(vault, payload, selected)
        else:
            from ..viewer.export import build_bundle
            bundle = build_bundle(vault, state, lean=True)
        citation_pairs = citation_overlay(bundle, state)["edges"]

    def add_link(kind, source, target, link_id=None, attrs=None):
        if source not in selected or target not in selected or source == target:
            return
        key = link_id or "%s|%s|%s" % (kind, source, target)
        links[key] = {
            "id": key, "kind": kind, "from": source, "to": target,
            **({"attrs": attrs} if attrs else {}),
        }

    for source, target in citation_pairs:
        add_link("cites", source, target)

    # Connected-Papers-style similarity is derived only inside the selected
    # overview. This bounds the pairwise stage by max_nodes rather than Vault size.
    tagged = defaultdict(set)
    for link in links.values():
        if not link["kind"].startswith("tag:") or link["kind"] == "tag:domain":
            continue
        source, target = link["from"], link["to"]
        work = source if payload["nodes"][source]["kind"] == "work" else target if payload["nodes"][target]["kind"] == "work" else None
        concept = target if work == source else source
        if work and payload["nodes"][concept]["kind"] == "concept":
            tagged[concept].add(work)
    shared = Counter()
    for works in tagged.values():
        ordered = sorted(works)
        for index, left in enumerate(ordered):
            for right in ordered[index + 1:]:
                shared[(left, right)] += 1
    for (left, right), count in sorted(shared.items()):
        if count >= 2:
            add_link("similar", left, right, attrs={"shared_concepts": count, "derived": True})

    adjacency = defaultdict(set)
    citation_in = Counter()
    citation_out = Counter()
    for link in links.values():
        if link["kind"] != "similar":
            adjacency[link["from"]].add(link["to"])
            adjacency[link["to"]].add(link["from"])
        if link["kind"] == "cites":
            citation_out[link["from"]] += 1
            citation_in[link["to"]] += 1

    nodes = []
    for node_id in sorted(selected):
        node = payload["nodes"][node_id]
        attrs = node.get("attrs") or {}
        nodes.append({
            "id": node_id,
            "kind": node["kind"],
            "label": node.get("label") or node_id,
            "year": int(attrs["year"]) if str(attrs.get("year", "")).isdigit() else attrs.get("year"),
            "citations": _work_metrics(bundle, node_id) if node["kind"] == "work" else None,
            "primary_domain": _work_primary_domain(bundle, node_id, visible) if node["kind"] == "work" else None,
            "degree": len(adjacency[node_id]),
            "read_depth": attrs.get("read_depth") if node["kind"] == "work" else None,
            "source_coverage": attrs.get("source_coverage") if node["kind"] == "work" else None,
            "publication_status": attrs.get("publication_status") if node["kind"] == "work" else None,
            "citation_in": citation_in[node_id],
            "citation_out": citation_out[node_id],
        })

    ordered_links = [links[key] for key in sorted(links)]
    before_link_cap = len(ordered_links)
    truncated = bounded
    if max_links is not None and len(ordered_links) > max_links:
        link_rank = {"parent": 0, "cites": 2, "similar": 3}
        ordered_links = sorted(ordered_links, key=lambda link: (link_rank.get(link["kind"], 1), link["id"]))[:max_links]
        ordered_links.sort(key=lambda link: link["id"])
        truncated = True
    counts = Counter(link["kind"] for link in ordered_links)
    works = sum(node["kind"] == "work" for node in nodes)
    works_with_metrics = sum(node["kind"] == "work" and node["citations"] is not None for node in nodes)
    return {
        "schema_version": GQP_VERSION,
        "snapshot": dict(document["snapshot"]),
        "nodes": nodes,
        "links": ordered_links,
        "completeness": {
            "node_count": len(nodes),
            "link_count": len(ordered_links),
            "total_node_count": len(visible),
            # Exact all-graph derived/citation totals require doing the work this
            # overview intentionally avoids. The canonical base total is exact.
            "total_link_count": before_link_cap if not bounded else len(base_links),
            "total_link_count_scope": "selected enriched graph" if not bounded else "complete canonical base graph; omitted citation/similarity links are not generated",
            "total_base_link_count": len(base_links),
            "selected_link_count_before_cap": before_link_cap,
            "truncated": truncated,
            "max_nodes": max_nodes,
            "max_links": max_links,
            "link_kind_counts": dict(sorted(counts.items())),
            "citation_overlay": "bibliographic-cache-selected-works" if vault is not None and max_nodes is not None else "bibliographic-cache" if vault is not None else "not_requested",
            "works_total": works,
            "works_with_citation_metrics": works_with_metrics,
            "citation_metric_coverage": (works_with_metrics / works) if works else 1.0,
            "similarity_rule": "works sharing at least 2 distinct non-domain concept tags",
            "overview_rule": "all domains first, then highest canonical degree with deterministic kind/id tie breaks; citation and similarity are derived only inside the selected set",
        },
    }


def run(argv=None):
    parser = argparse.ArgumentParser(description="Rich read-only graph visualization projection")
    parser.add_argument("--config")
    parser.add_argument("--max-nodes", type=int)
    parser.add_argument("--max-links", type=int)
    args = parser.parse_args(argv)
    if args.max_nodes is not None and not 1 <= args.max_nodes <= 5000:
        parser.error("--max-nodes must be between 1 and 5000")
    if args.max_links is not None and not 0 <= args.max_links <= 50000:
        parser.error("--max-links must be between 0 and 50000")
    roots = resolve_roots(args.config)
    print(json.dumps(build_network(roots["state_dir"], roots["vault_dir"], args.max_nodes, args.max_links), ensure_ascii=False, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(run())
