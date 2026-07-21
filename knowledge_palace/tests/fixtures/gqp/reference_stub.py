"""In-memory reference GraphQueryPort over literal fixture data.

TEST FIXTURE ONLY. This is not a Graph Index and it parses no Vault: every
node, edge, and card body below is a hand-written literal, so the
contract tests can exercise the operation semantics (pagination, entry
parent, stale rejection, brief non-evidence) that the production implementation
must honor.
"""

SCHEMA_VERSION = "1.0"
INDEX_FINGERPRINT = "fp-vault-001"
SNAPSHOT = {
    "snapshot_id": "snap-001",
    "vault_fingerprint": INDEX_FINGERPRINT,
    "built_at": "2026-07-13T00:00:00Z",
}

OPERATIONS = (
    "list_hierarchies",
    "list_levels",
    "query_level",
    "query_context",
    "get_content",
)


def _node(node_id, kind, label, path=None, attrs=None):
    view = {"id": node_id, "kind": kind, "label": label}
    if path is not None:
        view["canonical_ref"] = {"root": "vault", "path": path, "anchor": None}
    if attrs is not None:
        view["attrs"] = attrs
    return view


NODES = {
    "domain-alpha": _node("domain-alpha", "domain", "Alpha Domain", "domains.md"),
    "domain-beta": _node("domain-beta", "domain", "Beta Domain", "domains.md"),
    "concept-echo": _node("concept-echo", "concept", "Echo Cancellation", "concepts.md"),
    "concept-foxtrot": _node("concept-foxtrot", "concept", "Foxtrot Threshold", "concepts.md"),
    "concept-gamma": _node("concept-gamma", "concept", "Gamma Bridging", "concepts.md"),
    "work-alpha-2020-echo": _node(
        "work-alpha-2020-echo", "work", "Alpha 2020 — Echo", "papers/alpha-2020-echo.md"
    ),
    "work-beta-2021-foxtrot": _node(
        "work-beta-2021-foxtrot", "work", "Beta 2021 — Foxtrot", "papers/beta-2021-foxtrot.md"
    ),
    "work-gamma-2022-bridge": _node(
        "work-gamma-2022-bridge", "work", "Gamma 2022 — Bridge", "papers/gamma-2022-bridge.md"
    ),
    "gap-echo-noise": _node("gap-echo-noise", "gap", "Echo noise floor unresolved", "gaps/gap-echo-noise.md"),
    "brief-2026-07-01-gaps": _node(
        "brief-2026-07-01-gaps",
        "brief",
        "Gaps brief (2026-07-01)",
        "briefs/2026-07-01-gaps.md",
        attrs={"role": "view", "evidence_capable": False},
    ),
    # Unknown-kind node: kinds are an open, registry-driven set.
    "vista-echo-panorama": _node(
        "vista-echo-panorama", "hologram-view", "Echo panorama (future kind)", "views/echo.md"
    ),
}

PARENTS = {
    "concept-echo": ["domain-alpha"],
    "concept-foxtrot": ["domain-beta"],
    "concept-gamma": ["domain-alpha", "domain-beta"],  # multi-parent
    "work-alpha-2020-echo": ["concept-echo"],
    "work-beta-2021-foxtrot": ["concept-foxtrot"],
    "work-gamma-2022-bridge": ["concept-gamma"],
    "gap-echo-noise": ["concept-echo"],
    "brief-2026-07-01-gaps": [],
    "vista-echo-panorama": ["concept-echo"],
    "domain-alpha": [],
    "domain-beta": [],
}

EDGES = [
    {"id": "edge-001", "kind": "claims", "from": "work-alpha-2020-echo", "to": "concept-echo"},
    {"id": "edge-002", "kind": "supports", "from": "work-beta-2021-foxtrot", "to": "gap-echo-noise"},
    # A brief may cite (locate) sources — a non-evidence edge kind is legal.
    {"id": "edge-003", "kind": "cites", "from": "brief-2026-07-01-gaps", "to": "work-alpha-2020-echo"},
    {"id": "edge-004", "kind": "bridges", "from": "concept-gamma", "to": "concept-echo"},
    {"id": "edge-005", "kind": "identifies", "from": "work-alpha-2020-echo", "to": "gap-echo-noise"},
]

HIERARCHY = {
    "id": "domain-concept-work",
    "label": "Domain / Concept / Work",
    "levels": [
        {"level": 0, "label": "Domains", "node_kinds": ["domain"]},
        {"level": 1, "label": "Concepts", "node_kinds": ["concept"]},
        {"level": 2, "label": "Works and gaps", "node_kinds": ["work", "gap", "hologram-view"]},
    ],
}

_LEVEL_KINDS = {spec["level"]: spec["node_kinds"] for spec in HIERARCHY["levels"]}


class ReferenceGraphQueryPort:
    """Answers the five operations from the literals above. Read-only."""

    def __init__(self, current_vault_fingerprint=INDEX_FINGERPRINT, page_limit=2):
        self._current = current_vault_fingerprint
        self._limit = max(1, page_limit)

    # -- helpers -----------------------------------------------------------

    def _envelope(self, payload):
        message = {"schema_version": SCHEMA_VERSION, "snapshot": dict(SNAPSHOT)}
        message.update(payload)
        return message

    def _error(self, code, message, evidence=None):
        return {
            "schema_version": SCHEMA_VERSION,
            "snapshot": dict(SNAPSHOT),
            "error": {"code": code, "message": message, "evidence": evidence},
        }

    def _stale(self):
        if self._current != SNAPSHOT["vault_fingerprint"]:
            return self._error(
                "stale_index",
                "index snapshot %s (vault %s) does not match current vault "
                "fingerprint %s; rebuild the Graph Index"
                % (SNAPSHOT["snapshot_id"], SNAPSHOT["vault_fingerprint"], self._current),
            )
        return None

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

    def _children_of(self, node_id):
        return sorted(child for child, parents in PARENTS.items() if node_id in parents)

    # -- operations (the complete surface) ---------------------------------

    def list_hierarchies(self):
        stale = self._stale()
        if stale:
            return stale
        return self._envelope({"hierarchies": [HIERARCHY]})

    def list_levels(self, hierarchy_id):
        stale = self._stale()
        if stale:
            return stale
        if hierarchy_id != HIERARCHY["id"]:
            return self._error("unknown_hierarchy", "no hierarchy %r" % hierarchy_id)
        return self._envelope(
            {"hierarchy_id": hierarchy_id, "levels": HIERARCHY["levels"]}
        )

    def query_level(self, hierarchy_id, level, cursor=None, limit=None):
        stale = self._stale()
        if stale:
            return stale
        if hierarchy_id != HIERARCHY["id"]:
            return self._error("unknown_hierarchy", "no hierarchy %r" % hierarchy_id)
        if level not in _LEVEL_KINDS:
            return self._error(
                "invalid_request", "hierarchy %r has no level %r" % (hierarchy_id, level)
            )
        ids = sorted(
            node_id
            for node_id, view in NODES.items()
            if view["kind"] in _LEVEL_KINDS[level]
        )
        page = self._page(ids, cursor, limit, lambda node_id: dict(NODES[node_id]))
        if page is None:
            return self._error("bad_cursor", "cursor %r is not usable" % cursor)
        return self._envelope(
            {"hierarchy_id": hierarchy_id, "level": level, "page": page}
        )

    def query_context(self, node_id, entry_parent=None, cursor=None, limit=None):
        stale = self._stale()
        if stale:
            return stale
        if node_id not in NODES:
            return self._error("unknown_node", "no node %r" % node_id)
        parent_ids = PARENTS.get(node_id, [])
        siblings = None
        sibling_groups = None
        entry = None

        def sibling_page(parent_id):
            others = [c for c in self._children_of(parent_id) if c != node_id]
            return self._page(others, cursor, limit, lambda n: dict(NODES[n]))

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
            self._children_of(node_id), None, limit, lambda n: dict(NODES[n])
        )
        touching = sorted(
            (edge for edge in EDGES if node_id in (edge["from"], edge["to"])),
            key=lambda edge: edge["id"],
        )
        edge_ids = [edge["id"] for edge in touching]
        by_id = {edge["id"]: edge for edge in touching}
        edges = self._page(edge_ids, None, limit, lambda e: dict(by_id[e]))
        return self._envelope(
            {
                "node": dict(NODES[node_id]),
                "parents": [dict(NODES[p]) for p in sorted(parent_ids)],
                "entry_parent": entry,
                "siblings": siblings,
                "sibling_groups": sibling_groups,
                "children": children,
                "edges": edges,
            }
        )

    def get_content(self, node_id):
        stale = self._stale()
        if stale:
            return stale
        if node_id not in NODES:
            return self._error("unknown_node", "no node %r" % node_id)
        view = NODES[node_id]
        ref = view.get("canonical_ref") or {
            "root": "vault",
            "path": "cards/%s.md" % node_id,
            "anchor": None,
        }
        return self._envelope(
            {
                "node_id": node_id,
                "canonical_ref": dict(ref),
                "media_type": "text/markdown",
                "content": "# %s\n\nSynthetic card body for %s (fixture)." % (view["label"], node_id),
                "truncated": False,
            }
        )
