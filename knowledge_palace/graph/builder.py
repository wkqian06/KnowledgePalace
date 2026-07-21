"""Vault → rebuildable Graph Index snapshot in Derived State.

Storage decision: one canonical JSON snapshot under
``<state_dir>/graph-index/`` loaded into in-memory dicts by the port.
Idempotence by construction: the payload is serialized with sorted keys, so
an unchanged Vault rebuilds to byte-identical payload bytes and an identical
``payload_fingerprint`` (``built_at`` in the snapshot is informational and
excluded from that fingerprint).
ponytail: JSON + dicts, not SQL — at 85→5k works a database buys nothing;
upgrade path is stdlib sqlite3 behind the same port if rebuild latency or
memory measurably hurts.

Writes land ONLY under ``<state_dir>/graph-index/``; the Vault is read-only
here, always.
"""

import argparse
import copy
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from ..tools import SCHEMA_VERSION
from .identity import AXES, load_vault_identity

INDEX_RELPATH = Path("graph-index") / "index.json"

HIERARCHY = {
    "id": "domain-concept-work",
    "label": "Domain / Concept / Work",
    "levels": [
        {"level": 0, "label": "Domains", "node_kinds": ["domain"]},
        {"level": 1, "label": "Concepts", "node_kinds": ["concept"]},
        {"level": 2, "label": "Works and gaps", "node_kinds": ["work", "gap"]},
    ],
}
# ponytail: one hierarchy, defined here — a registry file appears when a
# second hierarchy actually exists (semantic projections).


def canonical_bytes(obj):
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode(
        "utf-8"
    )


def vault_fingerprint(vault):
    """sha256 over sorted relpath:sha256 lines of every Vault *.md file."""
    vault = Path(vault)
    entries = []
    for path in sorted(vault.rglob("*.md")):
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        entries.append(path.relative_to(vault).as_posix() + ":" + digest)
    return hashlib.sha256("\n".join(entries).encode("utf-8")).hexdigest()


def payload_fingerprint(payload):
    return hashlib.sha256(canonical_bytes(payload)).hexdigest()


def _node(node_id, kind, label, path, anchor=None, attrs=None):
    view = {
        "id": node_id,
        "kind": kind,
        "label": label,
        "canonical_ref": {"root": "vault", "path": path, "anchor": anchor},
    }
    if attrs is not None:
        view["attrs"] = attrs
    return view


def build_payload(vault):
    """Pure derivation: identity scan → nodes/parents/edges/hierarchy."""
    identity = load_vault_identity(vault)
    nodes, parents = {}, {}
    edges = {}
    unresolved = []

    def add_edge(source, kind, target):
        edge_id = "%s|%s|%s" % (source, kind, target)
        edges[edge_id] = {"id": edge_id, "kind": kind, "from": source, "to": target}

    def concept_ref(slug):
        if slug in identity["domains"]:
            return "domain:" + slug
        if slug in identity["registry"]:
            return "concept:" + slug
        return None

    for slug, name in identity["domains"].items():
        nodes["domain:" + slug] = _node("domain:" + slug, "domain", name, "domains.md", slug)
        parents["domain:" + slug] = []

    for slug, row in identity["registry"].items():
        node_id = "concept:" + slug
        nodes[node_id] = _node(
            node_id, "concept", slug, "concepts.md", slug, attrs={"axis": row["axis"]}
        )
        resolved = []
        for parent_slug in row["parents"]:
            parent_id = concept_ref(parent_slug)
            if parent_id:
                resolved.append(parent_id)
            else:
                unresolved.append("concepts.md: %s parent %r" % (slug, parent_slug))
        parents[node_id] = sorted(resolved)

    for slug, work in sorted(identity["works"].items()):
        node_id = "work:" + slug
        nodes[node_id] = _node(node_id, "work", str(work["title"]), work["path"])
        placement = []
        for axis in ("task", "pattern", "domain"):
            for tag in work["axes"].get(axis, []):
                target = concept_ref(tag)
                if target:
                    placement.append(target)
            if placement:
                break
        parents[node_id] = sorted(set(placement))
        for axis in AXES:
            for tag in work["axes"].get(axis, []):
                target = concept_ref(tag)
                if target:
                    add_edge(node_id, "tag:" + axis, target)
                else:
                    unresolved.append("%s: %s tag %r" % (work["path"], axis, tag))
        for gap_slug, relation in work["gaps"]:
            if gap_slug in identity["gaps"]:
                add_edge(node_id, relation, "gap:" + gap_slug)
            else:
                unresolved.append("%s: gap %r" % (work["path"], gap_slug))

    for claim_id, claim in sorted(identity["claims"].items()):
        node_id = "claim:" + claim_id
        work_id = "work:" + claim["work"]
        label = "C%d — %s" % (claim["n"], claim["quote"][:80])
        nodes[node_id] = _node(
            node_id,
            "claim",
            label,
            identity["works"][claim["work"]]["path"],
            "C%d" % claim["n"],
            attrs={"quote": claim["quote"], "anchor": claim["anchor"]},
        )
        parents[node_id] = [work_id]
        add_edge(work_id, "claims", node_id)
        for bound in claim.get("concepts") or []:
            target = concept_ref(bound)
            if target:
                add_edge(node_id, "binds", target)
            else:
                unresolved.append("%s: C%d binds %r" % (claim_id, claim["n"], bound))

    for slug, work in sorted(identity["works"].items()):
        for role, refs in sorted((work.get("profile_roles") or {}).items()):
            for ref in refs:
                claim_node = "claim:%s#%s" % (slug, ref)
                if claim_node in nodes:
                    add_edge("work:" + slug, "role:" + role, claim_node)
                else:
                    unresolved.append("%s: profile role %s -> %s" % (work["path"], role, ref))

    for slug, gap in sorted(identity["gaps"].items()):
        node_id = "gap:" + slug
        nodes[node_id] = _node(
            node_id, "gap", slug, gap["path"], attrs={"status": gap["status"], "type": gap["type"]}
        )
        placement = []
        for tag in gap["concepts"]:
            target = concept_ref(tag)
            if target:
                placement.append(target)
                add_edge(node_id, "concerns", target)
            else:
                unresolved.append("%s: concept %r" % (gap["path"], tag))
        parents[node_id] = sorted(set(placement))
        for other in gap["related"]:
            if other in identity["gaps"]:
                add_edge(node_id, "related", "gap:" + other)
            else:
                unresolved.append("%s: related %r" % (gap["path"], other))

    def any_ref(slug):
        for prefix, table in (
            ("concept:", identity["registry"]),
            ("gap:", identity["gaps"]),
            ("work:", identity["works"]),
            ("domain:", identity["domains"]),
        ):
            if slug in table:
                return prefix + slug
        return None

    for slug, transfer in sorted(identity["transfers"].items()):
        node_id = "transfer:" + slug
        nodes[node_id] = _node(
            node_id, "transfer", slug, transfer["path"], attrs={"status": transfer["status"]}
        )
        parents[node_id] = []
        for field, kind in (("a", "transfer-from"), ("c", "transfer-to")):
            target = any_ref(transfer[field])
            if target:
                add_edge(node_id, kind, target)
            elif transfer[field]:
                unresolved.append("%s: %s %r" % (transfer["path"], field, transfer[field]))
        for bridge in transfer["bridges"]:
            target = concept_ref(bridge)
            if target:
                add_edge(node_id, "bridge", target)
            else:
                unresolved.append("%s: bridge %r" % (transfer["path"], bridge))
        for gap_slug in transfer["gaps"]:
            if gap_slug in identity["gaps"]:
                add_edge(node_id, "addresses", "gap:" + gap_slug)
            else:
                unresolved.append("%s: gap %r" % (transfer["path"], gap_slug))
        for paper in transfer["papers"]:
            if paper in identity["works"]:
                add_edge(node_id, "evidence-paper", "work:" + paper)
            else:
                unresolved.append("%s: paper %r" % (transfer["path"], paper))

    for slug, brief in sorted(identity["briefs"].items()):
        node_id = "brief:" + slug
        nodes[node_id] = _node(
            node_id,
            "brief",
            slug,
            brief["path"],
            attrs={"role": "view", "evidence_capable": False},
        )
        parents[node_id] = []
        # Briefs are views: they emit zero edges (GRAPH_QUERY_PORT.md).

    payload = {
        "hierarchies": [copy.deepcopy(HIERARCHY)],
        "nodes": nodes,
        "parents": parents,
        "edges": [edges[key] for key in sorted(edges)],
        "identity_report": {
            "works": len(identity["works"]),
            "claims": len(identity["claims"]),
            "gaps": len(identity["gaps"]),
            "transfers": len(identity["transfers"]),
            "briefs": len(identity["briefs"]),
            "confirmations": identity["confirmations"],
            "parse_errors": identity["parse_errors"],
            "unresolved_refs": sorted(unresolved),
        },
    }
    return payload


def write_index(vault, state):
    """Build and persist the snapshot. Writes only under state/graph-index/."""
    vault, state = Path(vault), Path(state)
    fingerprint = vault_fingerprint(vault)
    payload = build_payload(vault)
    document = {
        "schema_version": SCHEMA_VERSION,
        "snapshot": {
            "snapshot_id": "snap-" + fingerprint[:12],
            "vault_fingerprint": fingerprint,
            "built_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        },
        "payload_fingerprint": payload_fingerprint(payload),
        "payload": payload,
    }
    target = state / INDEX_RELPATH
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(document, sort_keys=True, ensure_ascii=False, indent=1) + "\n",
        encoding="utf-8",
    )
    return target, document


def load_index(state):
    target = Path(state) / INDEX_RELPATH
    if not target.is_file():
        return None
    return json.loads(target.read_text(encoding="utf-8"))


def check(vault, state):
    """(status, detail) where status ∈ absent | stale | fresh."""
    document = load_index(state)
    if document is None:
        return "absent", "no index at %s — rebuildable" % (Path(state) / INDEX_RELPATH)
    current = vault_fingerprint(vault)
    served = document["snapshot"]["vault_fingerprint"]
    if current != served:
        return "stale", "index %s != vault %s — rebuild" % (served[:12], current[:12])
    rebuilt = payload_fingerprint(build_payload(vault))
    if rebuilt != document["payload_fingerprint"]:
        return "stale", "payload fingerprint drift (%s != %s)" % (
            rebuilt[:12],
            document["payload_fingerprint"][:12],
        )
    return "fresh", "snapshot %s, payload %s, idempotent rebuild verified" % (
        document["snapshot"]["snapshot_id"],
        document["payload_fingerprint"][:12],
    )


def _roots(args):
    if args.vault and args.state:
        return Path(args.vault), Path(args.state)
    from ..tools.config_resolver import resolve_roots

    roots = resolve_roots(args.config)
    return (
        Path(args.vault) if args.vault else roots["vault_dir"],
        Path(args.state) if args.state else roots["state_dir"],
    )


def run(argv):
    parser = argparse.ArgumentParser(prog="graph.builder", description=__doc__.splitlines()[0])
    parser.add_argument("--vault", help="vault root (default: .palace.toml)")
    parser.add_argument("--state", help="state root (default: .palace.toml)")
    parser.add_argument("--config", help="path to .palace.toml")
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--rebuild", action="store_true")
    action.add_argument("--fingerprint", action="store_true")
    action.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    try:
        vault, state = _roots(args)
        if args.fingerprint:
            print(vault_fingerprint(vault))
            return 0
        if args.check:
            status, detail = check(vault, state)
            print("%s — %s" % (status, detail))
            return 0 if status == "fresh" else 1
        target, document = write_index(vault, state)
        report = document["payload"]["identity_report"]
        print("wrote %s" % target)
        print(
            "works=%d claims=%d gaps=%d transfers=%d briefs=%d "
            "confirmations=%d parse_errors=%d unresolved=%d"
            % (
                report["works"],
                report["claims"],
                report["gaps"],
                report["transfers"],
                report["briefs"],
                len(report["confirmations"]),
                len(report["parse_errors"]),
                len(report["unresolved_refs"]),
            )
        )
        return 0
    except (OSError, ValueError) as err:
        print("builder error: %s" % err, file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(run(sys.argv[1:]))
