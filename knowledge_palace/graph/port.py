"""Production GraphQueryPort over the Derived State index snapshot.

Read-only. The surface is exactly the five contract operations; every
response carries schema_version + the index snapshot. Callers run
``builder.ensure_index`` first so the snapshot on disk matches the Vault.
"""

from pathlib import Path

from .builder import GQP_VERSION, INDEX_RELPATH, load_index

_MAX_CONTENT = 200_000


class GraphQueryPort:
    def __init__(self, vault, state, page_limit=50):
        document = load_index(state)
        if document is None:
            raise FileNotFoundError(
                "no Graph Index at %s — run `python3 -m knowledge_palace.graph.builder "
                "--rebuild`" % (Path(state) / INDEX_RELPATH)
            )
        self._vault = Path(vault)
        self._snapshot = document["snapshot"]
        self._payload = document["payload"]
        self._limit = max(1, min(int(page_limit), 500))
        self._children = {}
        for child, parent_ids in self._payload["parents"].items():
            for parent in parent_ids:
                self._children.setdefault(parent, []).append(child)
        for parent in self._children:
            self._children[parent].sort()
        self._level_kinds = {
            spec["level"]: spec["node_kinds"]
            for spec in self._payload["hierarchies"][0]["levels"]
        }

    # -- envelope helpers ---------------------------------------------------

    def _envelope(self, body):
        message = {"schema_version": GQP_VERSION, "snapshot": dict(self._snapshot)}
        message.update(body)
        return message

    def _error(self, code, text, evidence=None):
        return {
            "schema_version": GQP_VERSION,
            "snapshot": dict(self._snapshot),
            "error": {"code": code, "message": text, "evidence": evidence},
        }

    def _page(self, ordered_ids, cursor, limit, to_item):
        if cursor is not None and cursor not in ordered_ids:
            return None
        start = 0 if cursor is None else ordered_ids.index(cursor) + 1
        size = self._limit if limit is None else max(1, min(int(limit), 500))
        chunk = ordered_ids[start : start + size]
        has_more = (start + len(chunk)) < len(ordered_ids)
        return {
            "total": len(ordered_ids),
            "returned": len(chunk),
            "truncated": has_more,
            "next_cursor": chunk[-1] if (has_more and chunk) else None,
            "items": [to_item(item_id) for item_id in chunk],
        }

    def _node_view(self, node_id):
        return dict(self._payload["nodes"][node_id])

    # -- the five operations (the complete surface) --------------------------

    def list_hierarchies(self):
        return self._envelope({"hierarchies": list(self._payload["hierarchies"])})

    def list_levels(self, hierarchy_id):
        spec = self._payload["hierarchies"][0]
        if hierarchy_id != spec["id"]:
            return self._error("unknown_hierarchy", "no hierarchy %r" % hierarchy_id)
        return self._envelope({"hierarchy_id": hierarchy_id, "levels": spec["levels"]})

    def query_level(self, hierarchy_id, level, cursor=None, limit=None):
        spec = self._payload["hierarchies"][0]
        if hierarchy_id != spec["id"]:
            return self._error("unknown_hierarchy", "no hierarchy %r" % hierarchy_id)
        if level not in self._level_kinds:
            return self._error(
                "invalid_request", "hierarchy %r has no level %r" % (hierarchy_id, level)
            )
        kinds = self._level_kinds[level]
        ids = sorted(
            node_id
            for node_id, view in self._payload["nodes"].items()
            if view["kind"] in kinds
        )
        page = self._page(ids, cursor, limit, self._node_view)
        if page is None:
            return self._error("bad_cursor", "cursor %r is not usable" % cursor)
        return self._envelope({"hierarchy_id": hierarchy_id, "level": level, "page": page})

    def query_context(self, node_id, entry_parent=None, cursor=None, limit=None,
                      children_cursor=None, edges_cursor=None):
        if node_id not in self._payload["nodes"]:
            return self._error("unknown_node", "no node %r" % node_id)
        parent_ids = self._payload["parents"].get(node_id, [])
        siblings = None
        sibling_groups = None
        entry = None

        def sibling_page(parent_id):
            others = [c for c in self._children.get(parent_id, []) if c != node_id]
            return self._page(others, cursor, limit, self._node_view)

        if entry_parent is not None:
            if entry_parent not in parent_ids:
                return self._error(
                    "invalid_request",
                    "entry_parent %r is not a parent of %r" % (entry_parent, node_id),
                )
            entry = entry_parent
            siblings = sibling_page(entry_parent)
            if siblings is None:
                return self._error("bad_cursor", "cursor %r is not usable" % cursor)
        elif len(parent_ids) == 1:
            entry = parent_ids[0]
            siblings = sibling_page(entry)
            if siblings is None:
                return self._error("bad_cursor", "cursor %r is not usable" % cursor)
        elif len(parent_ids) > 1:
            sibling_groups = []
            for parent_id in sorted(parent_ids):
                page = sibling_page(parent_id)
                if page is None:
                    return self._error("bad_cursor", "cursor %r is not usable" % cursor)
                sibling_groups.append({"parent_id": parent_id, "page": page})

        children = self._page(
            self._children.get(node_id, []), children_cursor, limit, self._node_view
        )
        touching = sorted(
            edge["id"]
            for edge in self._payload["edges"]
            if node_id in (edge["from"], edge["to"])
        )
        by_id = {edge["id"]: edge for edge in self._payload["edges"]}
        edges = self._page(touching, edges_cursor, limit, lambda e: dict(by_id[e]))
        if children is None or edges is None:
            return self._error("bad_cursor", "child or edge cursor is not usable")
        return self._envelope(
            {
                "node": self._node_view(node_id),
                "parents": [self._node_view(p) for p in sorted(parent_ids)],
                "entry_parent": entry,
                "siblings": siblings,
                "sibling_groups": sibling_groups,
                "children": children,
                "edges": edges,
            }
        )

    def get_content(self, node_id):
        if node_id not in self._payload["nodes"]:
            return self._error("unknown_node", "no node %r" % node_id)
        view = self._payload["nodes"][node_id]
        ref = view["canonical_ref"]
        if view["kind"] == "claim":
            attrs = view.get("attrs") or {}
            content = "%s — %s" % (attrs.get("quote") or "", attrs.get("anchor") or "")
            truncated = False
        else:
            text = (self._vault / ref["path"]).read_text(encoding="utf-8")
            truncated = len(text) > _MAX_CONTENT
            content = text[:_MAX_CONTENT]
        return self._envelope(
            {
                "node_id": node_id,
                "canonical_ref": dict(ref),
                "media_type": "text/markdown",
                "content": content,
                "truncated": truncated,
            }
        )
