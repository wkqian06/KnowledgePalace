"""Walk the frozen GraphQueryPort into one canonical JSON payload.

Every read goes through the port's five operations — never a raw Vault
scan, never Source Cache. Level, child and edge pagination is followed to
completion via the port's separate cursors. Sibling pages remain bounded;
hierarchy levels and child/edge walks supply graph reachability.

Some node kinds (e.g. ``transfer``, ``brief``) have no parent and are
nobody's child — the hierarchy levels and children/siblings links never
surface them. They are reachable only as an edge endpoint on some other
node's ``edges`` list, so the walk schedules BOTH endpoints of every
edge it sees, not just parent/sibling/child views.
"""

import json
import re
from pathlib import Path

from ..graph.builder import canonical_bytes
from ..graph.port import GraphQueryPort
from ..metadata.cache import CACHE_DIRNAME
from ..metadata.providers import _clean_doi

WALK_PAGE_LIMIT = 500  # port caps at 500; minimizes pagination round-trips

_SOURCE_LINE = re.compile(r"^source:(.*)$", re.MULTILINE)
_DOI = re.compile(r"\b(10\.\d{4,9}/[^\s\"']+)")
_ARXIV = re.compile(r"arxiv(?:\.org)?[.:/]+(?:abs/|pdf/)?(\d{4}\.\d{4,5})", re.IGNORECASE)


def _unwrap(response):
    error = response.get("error")
    if error:
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
    """Full read-only walk → canonical JSON payload (dict, not bytes)."""
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

    # Parents, children and edge endpoints extend the worklist, reaching
    # non-hierarchy kinds such as Claims and dependency-linked Briefs.
    seen = set()
    while worklist:
        node_id = worklist.pop()
        if node_id in seen:
            continue
        seen.add(node_id)
        ctx = _unwrap(port.query_context(node_id, limit=page_limit))
        for field, argument in (("children", "children_cursor"), ("edges", "edges_cursor")):
            page = ctx[field]
            items = list(page["items"])
            while page["truncated"]:
                response = _unwrap(port.query_context(node_id, limit=page_limit,
                                                      **{argument: page["next_cursor"]}))
                page = response[field]
                items.extend(page["items"])
            ctx[field] = {"total": page["total"], "returned": len(items),
                          "items": items, "truncated": False, "next_cursor": None}
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


def _work_doi(payload, node_id):
    """Normalized DOI from the card's frontmatter ``source:`` line, or None."""
    content = (payload["contents"].get(node_id) or {}).get("content") or ""
    front = content.split("\n---", 1)[0]  # frontmatter only — body quotes may cite other DOIs
    match = _SOURCE_LINE.search(front)
    if not match:
        return None
    line = match.group(1)
    doi = _DOI.search(line)
    if doi:
        return _clean_doi(doi.group(1)).rstrip(".")
    arxiv = _ARXIV.search(line)
    if arxiv:
        return "10.48550/arxiv." + arxiv.group(1)
    return None


def citation_overlay(payload, state):
    """Work-to-work citation edges from the Bibliographic Cache (read-only).

    Joins cached OpenAlex ``referenced_works`` lists against the bundle's
    work DOIs. Purely Derived State — no network, no Vault scan; a missing
    or empty cache yields an empty overlay. Coverage is whatever the cache
    holds (``/palace refresh`` / expansion runs populate it).
    """
    cache_dir = Path(state) / CACHE_DIRNAME / "openalex"
    if not cache_dir.is_dir():
        return {"edges": []}

    work_by_doi = {}
    doi_collisions = set()
    for node_id, view in payload["nodes"].items():
        if view["kind"] != "work":
            continue
        doi = _work_doi(payload, node_id)
        if doi in doi_collisions or doi is None:
            continue
        if doi in work_by_doi:  # duplicate DOI: attribute edges to neither card
            work_by_doi.pop(doi)
            doi_collisions.add(doi)
            continue
        work_by_doi[doi] = node_id

    def norm_cache_doi(raw):
        cleaned = _clean_doi(raw)
        return cleaned.rstrip(".") if cleaned else None

    work_by_oa_id = {}
    refs_by_work = {}
    entries = []
    for path in sorted(cache_dir.glob("*.json")):
        try:
            record = json.loads(path.read_text(encoding="utf-8")).get("payload") or {}
        except ValueError as err:
            raise ValueError("corrupt bibliographic cache entry %s: %s" % (path, err))
        entries.append(record)
        node_id = work_by_doi.get(norm_cache_doi(record.get("doi")))
        if node_id and record.get("id"):
            work_by_oa_id[record["id"]] = node_id
    for record in entries:
        node_id = work_by_doi.get(norm_cache_doi(record.get("doi")))
        if node_id and record.get("referenced_works"):
            refs_by_work[node_id] = record["referenced_works"]

    edges = set()
    for source_id, referenced in refs_by_work.items():
        for oa_id in referenced:
            target_id = work_by_oa_id.get(oa_id)
            if target_id and target_id != source_id:
                edges.add((source_id, target_id))
    return {"edges": [list(pair) for pair in sorted(edges)]}
