"""Bounded global keyword search over the derived index, outside GraphQueryPort."""

import argparse
import json
import sys

from .builder import GQP_VERSION, load_index
from ..tools.config_resolver import resolve_roots


def search_nodes(state, query, limit=50):
    """Search all indexed nodes by case-folded ID, label, or alias substring."""
    if not isinstance(query, str) or not query.strip():
        raise ValueError("query is required")
    if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 100:
        raise ValueError("limit must be an integer between 1 and 100")
    document = load_index(state)
    if document is None:
        raise FileNotFoundError("Graph Index is missing; rebuild it before searching")
    needle = query.strip().casefold()
    nodes = []
    total = 0
    for node_id, node in sorted(document["payload"]["nodes"].items()):
        label = node.get("label") or node_id
        aliases = (node.get("attrs") or {}).get("aliases") or []
        if any(needle in text.casefold() for text in [node_id, label, *aliases] if isinstance(text, str)):
            total += 1
            if len(nodes) < limit:
                nodes.append({"id": node_id, "kind": node["kind"], "label": label, "aliases": aliases})
    return {"schema_version": GQP_VERSION, "snapshot": dict(document["snapshot"]),
            "query": query.strip(), "total": total, "nodes": nodes}


def run(argv=None):
    parser = argparse.ArgumentParser(description="Search all indexed graph node IDs, labels and aliases")
    parser.add_argument("--config")
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("query")
    args = parser.parse_args(argv)
    if not 1 <= args.limit <= 100:
        parser.error("--limit must be between 1 and 100")
    if not args.query.strip():
        parser.error("query is required")
    roots = resolve_roots(args.config)
    print(json.dumps(search_nodes(roots["state_dir"], args.query, args.limit), ensure_ascii=False, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(run())
