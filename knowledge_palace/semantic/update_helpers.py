"""Persistent review state for evidence-dependent judgments and project plans."""

import copy
import json
from datetime import datetime, timezone
from pathlib import Path
from .evidence_helpers import read_tables, dependencies, changed_evidence_nodes

UPDATE_PATH = Path("graph-index/synthesis-updates.json")


def merge_updates(previous, changes, snapshot):
    """Keep unresolved evidence changes until an explicit review resolves them."""
    entries = {(row["node_id"], row["entry"]): copy.deepcopy(row)
               for row in previous.get("entries", [])}
    for row in entries.values():
        if "events" not in row and row["affected"]:
            event = {"snapshot": previous.get("snapshot", {}), "change": copy.deepcopy(row)}
            row["events"] = [event]
        row.setdefault("status", "pending" if row["affected"] else "unchanged")
        row.setdefault("events", [])
        row.setdefault("reviews", [])
    for change in changes:
        key = (change["node_id"], change["entry"])
        old = entries.get(key)
        if not change["affected"] and old is not None:
            continue
        row = copy.deepcopy(change)
        row["events"] = old["events"] if old is not None else []
        row["reviews"] = old["reviews"] if old is not None else []
        row["status"] = "pending" if change["affected"] else "unchanged"
        if change["affected"]:
            row["events"].append({"snapshot": snapshot, "change": copy.deepcopy(change)})
            reviewed = row["reviews"][-1]["events_reviewed"] if row["reviews"] else 0
            row["suggestions"] = sorted({s for event in row["events"][reviewed:] for s in event["change"]["suggestions"]})
        entries[key] = row
    return {"snapshot": snapshot, "entries": [entries[key] for key in sorted(entries)]}


def load_updates(state):
    path = Path(state) / UPDATE_PATH
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {"entries": []}


def resolve_update(state, node_id, entry, decision, note):
    """Record the operator's completed review; later evidence reopens the item."""
    if decision not in ("retain", "revise", "withdraw") or not note.strip():
        raise ValueError("review requires retain/revise/withdraw and a nonempty rationale")
    document = load_updates(state)
    row = next((r for r in document["entries"] if r["node_id"] == node_id and r["entry"] == entry), None)
    if row is None or row.get("status", "pending" if row["affected"] else "unchanged") != "pending":
        raise ValueError("no pending review for %s / %s" % (node_id, entry))
    row.setdefault("reviews", []).append({"decision": decision, "note": note,
        "date": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "events_reviewed": len(row.get("events", []))})
    row["status"] = "resolved"
    (Path(state) / UPDATE_PATH).write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return row


def project_impacts(workspace, before, after, changes):
    """Locate frozen project arguments and declared section dependencies to review."""
    touched = changed_evidence_nodes(before, after)
    old_edges = {edge["id"]: edge for edge in before["edges"]}
    new_edges = {edge["id"]: edge for edge in after["edges"]}
    for key in old_edges.keys() | new_edges.keys():
        if old_edges.get(key) != new_edges.get(key):
            edge = new_edges.get(key, old_edges.get(key))
            touched.update((edge["from"], edge["to"]))
    touched.update("work:" + nid[6:].split("#")[0] for nid in list(touched) if nid.startswith("claim:"))
    touched.update(row["node_id"] for row in changes if row["affected"])
    result = []
    for manifest in sorted((Path(workspace) / "projects").glob("*/project.yaml")):
        project = manifest.parent.name
        notes_path = manifest.parent / "research.md"
        if notes_path.is_file():
            tables, errors = read_tables(notes_path.read_text(encoding="utf-8"), str(notes_path))
            if errors:
                raise ValueError("; ".join(errors))
            for entry in tables["Synthesis"]:
                refs = set(dependencies(entry))
                if refs & touched:
                    result.append({"node_id": "project:" + project, "entry": "decision:" + entry["id"],
                                   "dependencies": sorted(refs), "changed_nodes": sorted(refs & touched),
                                   "changed_edges": [], "affected": True,
                                   "suggestions": ["review the research decision and its experiment or learning plan"],
                                   "canonical_ref": {"root": "workspace", "path": notes_path.relative_to(workspace).as_posix()}})
        path = manifest.parent / "outline/brief.json"
        if not path.is_file():
            continue
        brief = json.loads(path.read_text(encoding="utf-8"))
        refs = {row["ref"] for row in brief.get("evidence", [])}
        affected = refs & touched
        if not affected:
            continue
        result.append({"node_id": "project:" + project, "entry": "argument",
                       "dependencies": sorted(refs), "changed_nodes": sorted(affected),
                       "changed_edges": [], "affected": True,
                       "suggestions": ["review project problem, contribution and evidence brief"],
                       "canonical_ref": {"root": "workspace", "path": path.relative_to(workspace).as_posix()}})
        for section in brief.get("sections", []):
            section_refs = set(section.get("evidence", []))
            if section_refs & affected:
                result.append({"node_id": "project:" + project, "entry": "section:" + section["name"],
                               "dependencies": sorted(section_refs), "changed_nodes": sorted(section_refs & affected),
                               "changed_edges": [], "affected": True,
                               "suggestions": ["review the section's declared evidence and reasoning"]})
    return result
