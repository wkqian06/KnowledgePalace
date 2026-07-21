"""Walk the frozen GraphQueryPort into one canonical JSON payload.

Every read goes through the port's five operations — never a raw Vault
scan, never Source Cache. A stale index at any call aborts the whole
walk (no partial payload). ``query_level`` pagination is followed to
completion via cursors; ``query_context``'s ``children``/``edges`` are
single-page by the frozen port contract itself (the port hardcodes
``cursor=None`` there — only level queries and ``siblings`` accept a
cursor), so the walk takes one best-effort page per node at the max
limit and preserves ``truncated``/``total`` honestly rather than
pretending completeness the contract does not offer.

Some node kinds (e.g. ``transfer``, ``brief``) have no parent and are
nobody's child — the hierarchy levels and children/siblings links never
surface them. They are reachable only as an edge endpoint on some other
node's ``edges`` list, so the walk schedules BOTH endpoints of every
edge it sees, not just parent/sibling/child views.
"""

import json

from ..graph.port import GraphQueryPort

WALK_PAGE_LIMIT = 500  # port caps at 500; minimizes pagination round-trips


class StaleIndexError(Exception):
    pass


def _unwrap(response):
    error = response.get("error")
    if error:
        if error["code"] == "stale_index":
            raise StaleIndexError(error["message"])
        raise RuntimeError("%s: %s" % (error["code"], error["message"]))
    return response


def _walk_pages(call):
    """Follow `next_cursor` to completion; return every item across pages."""
    items, cursor = [], None
    while True:
        page = _unwrap(call(cursor))["page"]
        items.extend(page["items"])
        if not page["truncated"]:
            return items
        cursor = page["next_cursor"]


def build_bundle(vault, state, page_limit=WALK_PAGE_LIMIT):
    """Full read-only walk → canonical JSON payload (dict, not bytes).

    Raises StaleIndexError if the index goes stale mid-walk (never
    returns a partial payload).
    """
    port = GraphQueryPort(vault, state, page_limit=page_limit)

    hierarchies_response = _unwrap(port.list_hierarchies())
    schema_version = hierarchies_response["schema_version"]

    nodes, contexts, contents = {}, {}, {}
    scheduled = set()
    worklist = []

    def schedule(node_id):
        if node_id not in scheduled:
            scheduled.add(node_id)
            worklist.append(node_id)

    def record_node(view):
        nodes.setdefault(view["id"], view)
        schedule(view["id"])

    levels_out = []
    for hierarchy in hierarchies_response["hierarchies"]:
        hid = hierarchy["id"]
        levels = _unwrap(port.list_levels(hid))["levels"]
        level_entries = []
        for level_spec in levels:
            level = level_spec["level"]
            items = _walk_pages(
                lambda cursor, hid=hid, level=level: port.query_level(
                    hid, level, cursor=cursor, limit=page_limit
                )
            )
            level_entries.append(
                {
                    "level": level,
                    "label": level_spec["label"],
                    "node_ids": [item["id"] for item in items],
                }
            )
            for view in items:
                record_node(view)
        levels_out.append(
            {"id": hid, "label": hierarchy["label"], "levels": level_entries}
        )

    # Worklist walk (order doesn't matter — canonical_bytes sort_keys makes
    # the output order-independent) via query_context/get_content: one
    # best-effort page per node at the max limit (see module docstring on
    # the children/edges pagination ceiling); newly-discovered parents/
    # siblings/children/edge-endpoints re-enter the worklist so
    # non-hierarchy kinds (claim/transfer/…) are reached transitively.
    seen = set()
    while worklist:
        node_id = worklist.pop()
        if node_id in seen:
            continue
        seen.add(node_id)
        ctx = _unwrap(port.query_context(node_id, limit=page_limit))
        contexts[node_id] = ctx
        nodes.setdefault(node_id, ctx["node"])  # covers edge-only-reached nodes
        for view in ctx["parents"]:
            record_node(view)
        if ctx["siblings"]:
            for view in ctx["siblings"]["items"]:
                record_node(view)
        for group in ctx.get("sibling_groups") or []:
            for view in group["page"]["items"]:
                record_node(view)
        for view in ctx["children"]["items"]:
            record_node(view)
        for edge in ctx["edges"]["items"]:
            schedule(edge["from"])
            schedule(edge["to"])
        content = _unwrap(port.get_content(node_id))
        contents[node_id] = {
            "canonical_ref": content["canonical_ref"],
            "media_type": content["media_type"],
            "content": content["content"],
            "truncated": content["truncated"],
        }

    return {
        "schema_version": schema_version,
        "hierarchies": levels_out,
        "nodes": nodes,
        "contexts": contexts,
        "contents": contents,
    }


def canonical_bytes(payload):
    return json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
