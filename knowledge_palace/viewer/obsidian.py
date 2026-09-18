"""``/palace wiki export`` — thin Obsidian hub pages linking into Vault cards.

Generates ``wiki/`` next to the Vault (both under one Obsidian root) from the
same frozen-GraphQueryPort walk the HTML viewer uses: ``overview.md`` plus one
hub page per domain/concept/gap/transfer, all cross-references as
path-qualified ``[[wikilinks]]``. Cards are the single source of truth — no
per-work pages, no card prose copied; hub pages carry only link topology and
index metadata.

Regeneration is marker-scoped: only files whose frontmatter says
``palace_generated: true`` are ever rewritten or deleted. ``briefs/`` and
dot-directories (``.obsidian``) are never touched, except that each run flips
a ``stale:`` frontmatter flag on briefs whose recorded ``snapshot_id`` no
longer matches — body bytes stay identical. Output is deterministic (no
timestamps): same index state, same bytes.
"""

import argparse
import os
import sys
import tempfile
from pathlib import Path

from ..tools.config_resolver import ConfigError, resolve_roots
from .cli import _is_inside
from .export import build_bundle

DEFAULT_DIRNAME = "wiki"
MARKER_KEY = "palace_generated"
PAGE_DIRS = {"domain": "domains", "concept": "concepts", "gap": "gaps", "transfer": "transfers"}
GAP_RELATIONS = ("identifies", "supports", "partially_addresses", "disputes", "reframes")


def resolve_wiki_dir(output, roots):
    """Target directory: explicit, or the Vault's sibling ``wiki/``."""
    target = Path(output).resolve() if output else roots["vault_dir"].parent / DEFAULT_DIRNAME
    for key in ("vault_dir", "state_dir", "source_dir", "workspace_dir"):
        if _is_inside(target, roots[key]):
            raise ValueError(
                "wiki dir %s is inside the private root %s=%s — choose a "
                "location outside all four roots" % (target, key, roots[key])
            )
        if _is_inside(roots[key], target):
            raise ValueError(
                "wiki dir %s contains the private root %s=%s — choose a "
                "directory of its own" % (target, key, roots[key])
            )
    if target.name == roots["vault_dir"].name:
        raise ValueError(
            "wiki dir basename %r collides with the Vault directory name — "
            "wikilink prefixes would be ambiguous" % target.name
        )
    return target


def split_frontmatter(lines):
    """(dict, end_index) over splitlines(keepends=True), or None.

    ``end_index`` is the line index AFTER the closing ``---`` fence; parsing
    is the flat ``key: value`` subset — all this export ever writes or reads.
    """
    if not lines or lines[0].strip() != "---":
        return None
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            fields = {}
            for raw in lines[1:index]:
                key, sep, value = raw.strip().partition(":")
                if sep:
                    fields[key.strip()] = value.strip()
            return fields, index + 1
    return None


def _label(text):
    """Wikilink display text: strip characters that break ``[[t|l]]`` syntax."""
    clean = str(text).replace("|", "/").replace("[", "(").replace("]", ")")
    return " ".join(clean.split())


def _card_ref(view, vault_name, text):
    """Wikilink straight to the node's vault card."""
    return "[[%s/%s|%s]]" % (vault_name, view["canonical_ref"]["path"][:-3], _label(text))


def node_link(view, vault_name, wiki_name, label=None):
    """Path-qualified wikilink: hub page when one exists, else the card."""
    kind, node_id = view["kind"], view["id"]
    if kind in PAGE_DIRS:
        slug = node_id.split(":", 1)[1]
        target = "%s/%s/%s" % (wiki_name, PAGE_DIRS[kind], slug)
        return "[[%s|%s]]" % (target, _label(label or view["label"]))
    if kind == "claim":
        work_slug, _, claim_n = node_id.split(":", 1)[1].partition("#")
        return _card_ref(view, vault_name, label or ("%s %s" % (work_slug, claim_n)))
    # work (and any future card-backed kind): link the card itself
    return _card_ref(view, vault_name, label or view["label"])


def collect_edges(payload):
    """Union of every context's edges page, deduped by edge id."""
    edges = {}
    for ctx in payload["contexts"].values():
        for edge in ctx["edges"]["items"]:
            edges[edge["id"]] = edge
    return edges


def _snapshot_id(payload):
    for ctx in payload["contexts"].values():
        return ctx["snapshot"]["snapshot_id"]
    return "snap-empty"


def _frontmatter(kind, node_id, snapshot):
    lines = ["---", "%s: true" % MARKER_KEY, "palace_kind: %s" % kind]
    if node_id:
        lines.append("palace_id: %s" % node_id)
    lines += ["snapshot_id: %s" % snapshot, "---", ""]
    return "\n".join(lines)


def build_pages(payload, vault_name, wiki_name):
    """Pure, deterministic: payload -> {posix relpath: file text}."""
    nodes = payload["nodes"]
    contexts = payload["contexts"]
    edges = collect_edges(payload)
    snapshot = _snapshot_id(payload)

    def link(node_id, label=None):
        return node_link(nodes[node_id], vault_name, wiki_name, label)

    def children_of(node_id, *kinds):
        ctx = contexts.get(node_id)
        items = ctx["children"]["items"] if ctx else []
        return sorted(
            (v for v in items if v["kind"] in kinds), key=lambda v: v["id"]
        )

    def edge_targets(kind_filter, endpoint, node_id):
        """Sorted other-endpoint ids of edges matching kind at endpoint."""
        other = "from" if endpoint == "to" else "to"
        return sorted(
            edge[other]
            for edge in edges.values()
            if edge[endpoint] == node_id and kind_filter(edge["kind"])
        )

    def section(title, node_ids):
        if not node_ids:
            return []
        # a dangling id here means a broken bundle — let link() raise KeyError
        return ["## " + title, ""] + ["- " + link(nid) for nid in node_ids] + [""]

    def truncation_note(node_id):
        ctx = contexts.get(node_id)
        if ctx and (ctx["children"]["truncated"] or ctx["edges"]["truncated"]):
            return ["> Some links may be missing: this node's context page was truncated.", ""]
        return []

    pages = {}

    for node_id, view in sorted(nodes.items()):
        kind = view["kind"]
        if kind not in PAGE_DIRS:
            continue
        slug = node_id.split(":", 1)[1]
        body = [_frontmatter(kind, node_id, snapshot), "# " + _label(view["label"]), ""]
        body += truncation_note(node_id)
        attrs = view.get("attrs") or {}

        if kind == "domain":
            body += ["**Source:** [[%s/domains|domains.md]]" % vault_name, ""]
            body += section("Concepts", [v["id"] for v in children_of(node_id, "concept")])
            body += section(
                "Works", edge_targets(lambda k: k == "tag:domain", "to", node_id)
            )
            body += section("Gaps", [v["id"] for v in children_of(node_id, "gap")])

        elif kind == "concept":
            axis = attrs.get("axis", "")
            body += [
                "axis: %s — **Source:** [[%s/concepts#%s|concepts.md § %s]]"
                % (axis, vault_name, axis, axis),
                "",
            ]
            ctx = contexts.get(node_id)
            parent_ids = sorted(v["id"] for v in (ctx["parents"] if ctx else []))
            body += section("Parents", parent_ids)
            body += section(
                "Child concepts", [v["id"] for v in children_of(node_id, "concept")]
            )
            tag_axes = sorted(
                {
                    edge["kind"][4:]
                    for edge in edges.values()
                    if edge["to"] == node_id and edge["kind"].startswith("tag:")
                }
            )
            for tag_axis in tag_axes:
                body += section(
                    "Works (%s)" % tag_axis,
                    edge_targets(lambda k, a=tag_axis: k == "tag:" + a, "to", node_id),
                )
            body += section(
                "Claims binding here", edge_targets(lambda k: k == "binds", "to", node_id)
            )
            body += section(
                "Gaps concerning this", edge_targets(lambda k: k == "concerns", "to", node_id)
            )
            body += section(
                "Transfer bridges", edge_targets(lambda k: k == "bridge", "to", node_id)
            )

        elif kind == "gap":
            body += [
                "status: %s — type: %s" % (attrs.get("status", "?"), attrs.get("type", "?")),
                "",
                "**Card:** %s" % _card_ref(view, vault_name, slug),
                "",
            ]
            for relation in GAP_RELATIONS:
                body += section(
                    relation, edge_targets(lambda k, r=relation: k == r, "to", node_id)
                )
            body += section("Concerns", edge_targets(lambda k: k == "concerns", "from", node_id))
            related = sorted(
                set(edge_targets(lambda k: k == "related", "from", node_id))
                | set(edge_targets(lambda k: k == "related", "to", node_id))
            )
            body += section("Related gaps", related)
            body += section(
                "Addressed by transfers",
                edge_targets(lambda k: k == "addresses", "to", node_id),
            )

        elif kind == "transfer":
            body += [
                "status: %s" % attrs.get("status", "?"),
                "",
                "**Card:** %s" % _card_ref(view, vault_name, slug),
                "",
            ]
            body += section("From", edge_targets(lambda k: k == "transfer-from", "from", node_id))
            body += section("To", edge_targets(lambda k: k == "transfer-to", "from", node_id))
            body += section("Bridges", edge_targets(lambda k: k == "bridge", "from", node_id))
            body += section("Addresses", edge_targets(lambda k: k == "addresses", "from", node_id))
            body += section(
                "Evidence papers", edge_targets(lambda k: k == "evidence-paper", "from", node_id)
            )

        pages["%s/%s.md" % (PAGE_DIRS[kind], slug)] = "\n".join(body).rstrip("\n") + "\n"

    pages["overview.md"] = _overview_page(payload, snapshot, link, children_of)
    return pages


def _overview_page(payload, snapshot, link, children_of):
    nodes = payload["nodes"]
    counts = {}
    for view in nodes.values():
        counts[view["kind"]] = counts.get(view["kind"], 0) + 1
    body = [
        _frontmatter("overview", None, snapshot),
        "# Palace Wiki",
        "",
        "snapshot: %s" % snapshot,
        "",
        "counts: " + " · ".join("%s %d" % (k, counts[k]) for k in sorted(counts)),
        "",
        "## Hierarchy",
        "",
    ]

    truncated = any(
        ctx["children"]["truncated"] or ctx["edges"]["truncated"]
        for ctx in payload["contexts"].values()
    )

    def tree(node_id, depth, seen):
        if node_id in seen or depth > 6:
            return []
        lines = ["    " * depth + "- " + link(node_id)]
        if nodes[node_id]["kind"] in ("domain", "concept"):
            for child in children_of(node_id, "concept", "work", "gap"):
                lines += tree(child["id"], depth + 1, seen | {node_id})
        return lines

    for hierarchy in payload["hierarchies"]:
        for level in hierarchy["levels"]:
            if level["level"] != 0:
                continue
            for node_id in sorted(level["node_ids"]):
                body += tree(node_id, 0, set())
    body += [""]

    body += ["## Map", "", "```mermaid", "flowchart TD"]
    map_ids = sorted(
        nid for nid, v in nodes.items() if v["kind"] in ("domain", "concept", "gap")
    )
    mermaid_id = {nid: "n%d" % i for i, nid in enumerate(map_ids)}
    for nid in map_ids:
        body.append(
            '    %s["%s"]' % (mermaid_id[nid], _label(nodes[nid]["label"]).replace('"', "'"))
        )
    for nid in map_ids:
        ctx = payload["contexts"].get(nid)
        for parent in ctx["parents"] if ctx else []:
            if parent["id"] in mermaid_id:
                body.append("    %s --> %s" % (mermaid_id[parent["id"]], mermaid_id[nid]))
    body += ["```", ""]

    if truncated:
        body += ["> Some links may be missing: at least one context page was truncated.", ""]
    return "\n".join(body).rstrip("\n") + "\n"


def scan_generated(wiki_dir):
    """Marker-carrying files; ``briefs/`` and dot-directories are exempt."""
    wiki_dir = Path(wiki_dir)
    managed = set()
    if not wiki_dir.is_dir():
        return managed
    for path in wiki_dir.rglob("*.md"):
        rel = path.relative_to(wiki_dir)
        if rel.parts[0] == "briefs" or any(part.startswith(".") for part in rel.parts):
            continue
        parsed = split_frontmatter(
            path.read_text(encoding="utf-8").splitlines(keepends=True)
        )
        if parsed and parsed[0].get(MARKER_KEY) == "true":
            managed.add(path)
    return managed


def _atomic_write(target, data):
    target.parent.mkdir(parents=True, exist_ok=True)
    handle, temp_name = tempfile.mkstemp(dir=str(target.parent), suffix=".part")
    try:
        with os.fdopen(handle, "wb") as fh:
            fh.write(data)
        os.replace(temp_name, str(target))
    except BaseException:
        Path(temp_name).unlink(missing_ok=True)
        raise


def write_pages(wiki_dir, pages):
    """Write current set, delete orphaned generated files. (written, deleted)."""
    wiki_dir = Path(wiki_dir)
    managed = scan_generated(wiki_dir)
    current = {wiki_dir / relpath for relpath in pages}
    conflicts = sorted(
        str(t) for t in current if t.exists() and t not in managed
    )
    if conflicts:
        raise ValueError(
            "refusing to overwrite files without the %s marker: %s"
            % (MARKER_KEY, ", ".join(conflicts))
        )
    for relpath, text in sorted(pages.items()):
        _atomic_write(wiki_dir / relpath, text.encode("utf-8"))
    orphans = managed - current
    for path in sorted(orphans):
        path.unlink()
    for name in sorted(PAGE_DIRS.values()):
        subdir = wiki_dir / name
        if subdir.is_dir() and not any(subdir.iterdir()):
            subdir.rmdir()
    return len(current), len(orphans)


def mark_brief_staleness(wiki_dir, snapshot_id):
    """Flip ``stale:`` on briefs whose snapshot moved; bodies stay byte-identical."""
    briefs = Path(wiki_dir) / "briefs"
    flipped = []
    if not briefs.is_dir():
        return flipped
    for path in sorted(briefs.glob("*.md")):
        lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
        parsed = split_frontmatter(lines)
        if not parsed or "snapshot_id" not in parsed[0]:
            continue
        fields, end = parsed
        stale = "true" if fields["snapshot_id"] != snapshot_id else "false"
        if fields.get("stale") == stale or ("stale" not in fields and stale == "false"):
            continue
        eol = "\r\n" if lines[0].endswith("\r\n") else "\n"
        stale_line = "stale: %s%s" % (stale, eol)
        head = lines[: end - 1]  # frontmatter without the closing fence
        replaced = False
        for index in range(1, len(head)):
            if head[index].strip().startswith("stale:"):
                head[index] = stale_line
                replaced = True
                break
        if not replaced:
            head.append(stale_line)
        _atomic_write(path, "".join(head + lines[end - 1 :]).encode("utf-8"))
        flipped.append(path.relative_to(wiki_dir).as_posix())
    return flipped


def export(output=None, config_path=None):
    """Build hub pages and write them. Returns (wiki_dir, stats dict)."""
    roots = resolve_roots(config_path)
    target = resolve_wiki_dir(output, roots)
    from ..graph.builder import ensure_index

    ensure_index(roots["vault_dir"], roots["state_dir"], roots["workspace_dir"])
    payload = build_bundle(roots["vault_dir"], roots["state_dir"])
    pages = build_pages(payload, vault_name=roots["vault_dir"].name, wiki_name=target.name)
    written, deleted = write_pages(target, pages)
    flipped = mark_brief_staleness(target, _snapshot_id(payload))
    return target, {
        "written": written,
        "deleted": deleted,
        "stale_flips": flipped,
        "non_sibling": target.parent != roots["vault_dir"].parent,
    }


def run(argv):
    parser = argparse.ArgumentParser(
        prog="viewer obsidian", description=__doc__.splitlines()[0]
    )
    parser.add_argument(
        "output", nargs="?", help="wiki directory (default: <vault parent>/%s)" % DEFAULT_DIRNAME
    )
    parser.add_argument("--config", help="path to .palace.toml")
    args = parser.parse_args(argv)
    try:
        target, stats = export(args.output, args.config)
    except (ConfigError, ValueError, FileNotFoundError) as err:
        print("wiki export: %s" % err)
        return 1
    if stats["non_sibling"]:
        print(
            "warning: %s is not a sibling of the Vault — path-qualified "
            "wikilinks only resolve when wiki and vault share one "
            "Obsidian root" % target
        )
    print(
        "wiki export: wrote %d pages, deleted %d orphans -> %s"
        % (stats["written"], stats["deleted"], target)
    )
    for relpath in stats["stale_flips"]:
        print("wiki export: stale flag updated on %s" % relpath)
    return 0


if __name__ == "__main__":
    sys.exit(run(sys.argv[1:]))
