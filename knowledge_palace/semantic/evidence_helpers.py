"""Optional, source-linked argument tables on Markdown cards."""

import re

TABLES = {
    "Argument": ("Role", "Claim", "Paraphrase", "Attribution", "Scope"),
    "Conditions": ("Dimension", "Value", "Evidence"),
    "Evidence relations": (
        "Claim", "Relation", "Target", "Attribution", "Comparison", "Scope", "Rationale"
    ),
    "Synthesis": ("ID", "Statement", "Claims", "Gaps", "Rationale"),
    "Observations": ("ID", "Source", "Judgment", "Outcome", "Interpretation"),
}
RELATIONS = (
    "identifies", "supports", "partially_addresses", "disputes", "reframes",
    "same_question", "overlaps", "broader_than", "narrower_than", "different_question",
)
ATTRIBUTIONS = ("author", "system")
COMPARISONS = ("direct_response", "retrospective")


def read_tables(body, origin):
    """Read the documented pipe-table subset; report malformed new sections."""
    tables = {name: [] for name in TABLES}
    section = None
    errors = []
    for number, line in enumerate(body.splitlines(), 1):
        if line.startswith("## "):
            section = line[3:].strip()
        if section not in TABLES or not line.startswith("|"):
            continue
        cells = [cell.strip().replace("\\|", "|") for cell in re.split(r"(?<!\\)\|", line)[1:-1]]
        columns = TABLES[section]
        if cells == list(columns) or all(re.fullmatch(r":?-+:?", c) for c in cells):
            continue
        if len(cells) != len(columns):
            errors.append("%s: %s table row %d needs %d cells" % (origin, section, number, len(columns)))
            continue
        row = dict(zip((c.lower() for c in columns), cells))
        if any(not c for c in cells):
            errors.append("%s: empty %s cell at row %d" % (origin, section, number))
            continue
        if section == "Argument" and row["role"] not in ("problem", "advance", "remaining"):
            errors.append("%s: unknown argument role %s" % (origin, row["role"]))
            continue
        if section in ("Argument", "Evidence relations") and row["attribution"] not in ATTRIBUTIONS:
            errors.append("%s: attribution must be author or system" % origin)
            continue
        if section == "Evidence relations":
            if row["relation"] not in RELATIONS or row["comparison"] not in COMPARISONS:
                errors.append("%s: invalid evidence relation or comparison" % origin)
                continue
            if row["comparison"] == "retrospective" and row["attribution"] != "system":
                errors.append("%s: retrospective relations require system attribution" % origin)
                continue
        if section == "Observations" and row["outcome"] not in ("supports", "questions", "inconclusive"):
            errors.append("%s: observation outcome must be supports, questions or inconclusive" % origin)
            continue
        tables[section].append(row)
    return tables, errors


def claim_ref(slug, reference):
    """Resolve a local C-number or an already qualified Claim reference."""
    return "claim:%s#%s" % (slug, reference) if re.fullmatch(r"C\d+", reference) else reference


def dependencies(entry):
    """Explicit dependencies of one synthesis entry; '-' means none."""
    return sorted({ref.strip() for key in ("claims", "gaps")
                   for ref in entry[key].split(",") if ref.strip() != "-"})


def changed_evidence_nodes(before, after):
    """Changed records, including Claims whose recorded study context changed."""
    changed = {key for key in before["nodes"].keys() | after["nodes"].keys()
               if before["nodes"].get(key) != after["nodes"].get(key)}
    context_works = set()
    for key in changed:
        old, new = before["nodes"].get(key, {}), after["nodes"].get(key, {})
        if new.get("kind", old.get("kind")) == "work" and any(
                old.get("attrs", {}).get(field) != new.get("attrs", {}).get(field)
                for field in ("conditions", "argument")):
            context_works.add(key)
    for payload in (before, after):
        changed.update(nid for nid, node in payload["nodes"].items()
                       if node["kind"] == "claim" and context_works.intersection(payload["parents"].get(nid, [])))
    changed.update("work:" + key[6:].split("#")[0] for key in list(changed) if key.startswith("claim:"))
    return changed


def evidence_changes(before, after):
    """Locate affected synthesis entries without treating views as evidence.

    Suggestions request scientific review. They never change a stored verdict.
    Gap relations added by a new work affect existing Gap-dependent syntheses.
    """
    changes = []
    old_edges = {edge["id"]: edge for edge in before["edges"]}
    new_edges = {edge["id"]: edge for edge in after["edges"]}
    changed_edges = [new_edges.get(key, old_edges.get(key))
                     for key in sorted(old_edges.keys() | new_edges.keys())
                     if old_edges.get(key) != new_edges.get(key)]
    changed_nodes = changed_evidence_nodes(before, after)
    for node_id, node in sorted(after["nodes"].items()):
        entries = list(node.get("attrs", {}).get("synthesis", []))
        if node["kind"] == "transfer" and node["attrs"].get("dependencies"):
            entries.append({"id": "hypothesis", "claims": ", ".join(node["attrs"]["dependencies"]), "gaps": "-"})
        for entry in entries:
            refs = dependencies(entry)
            if node["kind"] == "gap":
                refs = sorted(set(refs) | {node_id})
            touched = [edge for edge in changed_edges
                       if edge["kind"] != "depends_on"
                       and (edge["from"] in refs or edge["to"] in refs
                            or (edge["from"].startswith("claim:")
                                and "work:" + edge["from"][6:].split("#")[0] in refs))]
            changed = sorted(set(refs) & changed_nodes)
            suggestions = []
            for edge in touched:
                if edge["id"] not in new_edges:
                    suggestions.append("review judgment after evidence relation removal")
                elif edge["kind"] == "disputes":
                    suggestions.append("review whether to question the judgment")
                elif edge["kind"] in ("reframes", "narrower_than", "different_question"):
                    suggestions.append("review scope and whether to narrow the judgment")
                elif edge["kind"] in ("supports", "partially_addresses"):
                    suggestions.append("review whether evidence strengthens the judgment within its conditions")
            changes.append({
                "node_id": node_id, "entry": entry["id"], "dependencies": refs,
                "changed_nodes": changed, "changed_edges": [edge["id"] for edge in touched],
                "affected": bool(changed or touched),
                "suggestions": sorted(set(suggestions)) if suggestions else
                    (["review changed evidence and applicability"] if changed or touched else
                     ["retain judgment; no dependency change detected"]),
            })
    affected_gaps = {row["node_id"] for row in changes
                     if row["affected"] and row["node_id"].startswith("gap:")}
    while True:
        newly_affected = [row for row in changes if not row["affected"]
                          and affected_gaps.intersection(row["dependencies"])]
        if not newly_affected:
            break
        for row in newly_affected:
            row["affected"] = True
            row["suggestions"] = ["review dependent Gap judgment after evidence changes"]
            row["affected_gaps"] = sorted(affected_gaps.intersection(row["dependencies"]))
            if row["node_id"].startswith("gap:"):
                affected_gaps.add(row["node_id"])
    return changes
