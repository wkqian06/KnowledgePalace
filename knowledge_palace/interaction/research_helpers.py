"""Bounded evidence retrieval and source-linked research progress views."""

import re
from collections import Counter
from itertools import zip_longest

from .prefilter import CANDIDATE_CAP, candidate_matches, match_rank
from ..semantic.evidence_helpers import dependencies, RELATIONS
from ..semantic.corridors import _domain_resolver, SHARED_AXES


def research_context(payload, topic, alternatives=(), bridge_stopwords=()):
    """Select current understanding and its evidence across all requested queries."""
    nodes = payload["nodes"]
    pools, attempts, match_reasons = [], [], {}
    for query in list(dict.fromkeys([topic] + list(alternatives)[:2])):
        matches = candidate_matches(payload, query)
        for nid, why in matches.items():
            match_reasons.setdefault(nid, set()).update(why)
        pools.append(sorted(matches, key=lambda nid: match_rank(nid, matches[nid])))
        attempts.append({"query": query, "hits": len(matches)})
    # A synthesis is current for this question when its evidence is among the leading
    # matches; on a real library the whole match pool covers most of the Vault.
    leading = set().union(*(set(pool[:CANDIDATE_CAP]) for pool in pools))
    latest = {}
    for nid, node in nodes.items():
        attrs = node.get("attrs", {})
        if node["kind"] != "brief" or not attrs.get("synthesis"):
            continue
        scope = (attrs.get("topic") or nid, attrs.get("view", ""))
        previous = latest.get(scope)
        if previous is None or (attrs.get("date", ""), nid) > (
                nodes[previous]["attrs"].get("date", ""), previous):
            latest[scope] = nid
    briefs = []
    for nid in latest.values():
        node = nodes[nid]
        refs = {ref for entry in node["attrs"]["synthesis"] for ref in dependencies(entry)}
        owners = {"work:" + ref[6:].split("#")[0] for ref in refs if ref.startswith("claim:")}
        if (refs | owners) & leading:
            briefs.append(nid)
    briefs.sort(key=lambda nid: (nodes[nid]["attrs"].get("date", ""), nid), reverse=True)
    selected = briefs[:3]
    reasons = {nid: {"current-synthesis"} for nid in selected}
    # Each reformulation contributes before a broad first query fills the budget.
    for pool in pools:
        if pool:
            nid = pool[0]
            reasons.setdefault(nid, set()).add("query-match")
            if nid not in selected:
                selected.append(nid)
    evidence_lists = []
    for nid in list(selected):
        for entry in nodes[nid].get("attrs", {}).get("synthesis", []):
            evidence_lists.append(list(dict.fromkeys(
                "work:" + ref[6:].split("#")[0] for ref in dependencies(entry)
                if ref.startswith("claim:") and ref in nodes)))
        if nodes[nid]["kind"] == "gap":
            evidence_lists.append(list(dict.fromkeys(
                "work:" + edge["from"][6:].split("#")[0] if edge["from"].startswith("claim:") else edge["from"]
                for edge in payload["edges"] if edge["to"] == nid and edge["kind"] in RELATIONS
                and nodes[edge["from"]]["kind"] in ("claim", "work"))))
    # Interleave judgment dependencies so one long entry cannot consume the set.
    for group in zip_longest(*evidence_lists):
        for nid in group:
            if nid is None:
                continue
            reasons.setdefault(nid, set()).add("synthesis-dependency")
            if nid not in selected and len(selected) < 15:
                selected.append(nid)
    for group in zip_longest(*pools):
        for nid in group:
            if nid is None:
                continue
            reasons.setdefault(nid, set()).add("query-match")
            if nid not in selected and len(selected) < 15:
                selected.append(nid)
    ids = set(selected)
    claims = {nid: node for nid, node in nodes.items()
              if node["kind"] == "claim" and any(p in ids for p in payload["parents"].get(nid, []))}
    relations = [edge for edge in payload["edges"]
                 if edge["from"] in claims and edge.get("attrs", {}).get("claim_ref")]
    gap_ids = {edge["to"] for edge in relations if edge["to"].startswith("gap:")}
    gap_ids.update(nid for nid in ids if nid.startswith("gap:"))
    current = {nid: nodes[nid] for nid in selected if nodes[nid]["kind"] == "brief"}
    refs = {ref for nid in selected for entry in nodes[nid].get("attrs", {}).get("synthesis", [])
            for ref in dependencies(entry)}
    gap_ids.update(ref for ref in refs if ref.startswith("gap:") and ref in nodes)
    refs.update(edge["to"] for edge in relations if edge["to"].startswith("claim:"))
    return {
        "topic": topic, "attempts": attempts,
        "candidates": [{"node_id": nid, "canonical_ref": dict(nodes[nid]["canonical_ref"]),
                        "why": sorted(reasons[nid] | match_reasons.get(nid, set()))} for nid in selected],
        "works": {nid: nodes[nid] for nid in selected if nodes[nid]["kind"] == "work"},
        "claims": claims, "relations": relations, "current_syntheses": current,
        "gaps": {nid: nodes[nid] for nid in sorted(gap_ids & ids)},
        "related_gaps": [{"node_id": nid, "canonical_ref": nodes[nid]["canonical_ref"]}
                         for nid in sorted(gap_ids - ids)],
        "unread_dependencies": sorted(ref for ref in refs if ref not in claims and ref not in ids),
        "cross_domain": cross_domain_candidates(payload, ids, bridge_stopwords),
        "coverage": "candidate-set-only" if ids else "no-candidates",
    }


def cross_domain_candidates(payload, selected, stopwords=()):
    """Suggest at most three foreign sources through the selected works' functions."""
    nodes = payload["nodes"]
    domains_of = _domain_resolver(payload)
    origins = set().union(*(domains_of(nid) for nid in selected))
    attached = {}
    for edge in payload["edges"]:
        concept = nodes.get(edge["to"], {})
        if (edge["kind"] not in ("tag:pattern", "tag:function", "tag:failure-mode", "concerns")
                or concept.get("attrs", {}).get("axis") not in SHARED_AXES
                or edge["to"].split(":", 1)[-1] in stopwords):
            continue
        attached.setdefault(edge["to"], set()).add(edge["from"])
    result = []
    for via, endpoints in sorted(attached.items()):
        local = endpoints & selected
        if not local:
            continue
        for nid in sorted(endpoints - selected):
            if (nodes[nid]["kind"] != "work" or not domains_of(nid) - origins
                    or any(row["node_id"] == nid for row in result)):
                continue
            result.append({"node_id": nid, "via": via, "from": sorted(local),
                           "canonical_ref": nodes[nid]["canonical_ref"],
                           "status": "candidate; compare assumptions before transfer"})
            if len(result) == 3:
                return result
    return result


def bounded_context(context, claims_per_work=3):
    """Reduce a research context to a reading plan that fits a small context window.

    Every candidate keeps its card path. Each work quotes at most
    ``claims_per_work`` Claims verbatim: Claims the query matched come first, then
    Claims with recorded relations, then the Claims its argument cites. Relations
    become triples; a synthesis keeps its statements and Claim references, and a
    brief keeps only the entries that depend on a selected card. A retracted Claim
    is not evidence and is neither quoted nor counted. The cards hold everything
    left out.
    """
    judgment = ("id", "statement", "claims")
    claims = context["claims"]
    related = {edge["from"] for edge in context["relations"]}
    works, quoted = {}, set()
    for row in context["candidates"]:
        work = context["works"].get(row["node_id"])
        if work is None:
            continue
        prefix = "claim:%s#" % row["node_id"][5:]
        own = sorted((cid for cid in claims
                      if cid.startswith(prefix) and not claims[cid]["attrs"].get("retracted")),
                     key=lambda cid: int(cid[len(prefix) + 1:]))
        # A Claim match reads "claim:<claim id> (term:<term>)", and the id carries its own "claim:".
        hits = Counter(reason[6:].split(" ")[0] for reason in row["why"]
                       if reason.startswith("claim:" + prefix))
        cited = [prefix + entry["claim"] for entry in work["attrs"].get("argument", [])]
        order = dict.fromkeys(sorted((cid for cid in own if cid in hits), key=lambda cid: -hits[cid])
                              + [cid for cid in own if cid in related] + cited + own)
        chosen = [cid for cid in order if cid in own][:claims_per_work]
        quoted.update(chosen)
        works[row["node_id"]] = {
            "title": work["label"], "year": work["attrs"].get("year"),
            "read_depth": work["attrs"].get("read_depth"), "claims_total": len(own),
            "claims": [{"id": cid[len(prefix):], "quote": claims[cid]["attrs"]["quote"],
                        "anchor": claims[cid]["attrs"]["anchor"]} for cid in chosen],
        }
    gaps = {}
    for nid, node in context["gaps"].items():
        statement = re.search(r"## Statement\s+(.*?)(?=\n## |\Z)", node["attrs"]["text"], re.S)
        gaps[nid] = {"path": node["canonical_ref"]["path"], "status": node["attrs"]["status"],
                     "type": node["attrs"]["type"],
                     "statement": statement.group(1).strip() if statement else "",
                     "synthesis": [{key: entry[key] for key in judgment}
                                   for entry in node["attrs"].get("synthesis", [])]}
    selected = set(works) | set(gaps)
    syntheses = {}
    for nid, node in context["current_syntheses"].items():
        entries = [{key: entry[key] for key in judgment} for entry in node["attrs"]["synthesis"]
                   if any(ref in selected or "work:" + ref[6:].split("#")[0] in selected
                          for ref in dependencies(entry))]
        if entries:
            syntheses[nid] = {"path": node["canonical_ref"]["path"],
                              "date": node["attrs"].get("date", ""), "synthesis": entries}
    return {
        "topic": context["topic"], "attempts": context["attempts"], "coverage": context["coverage"],
        "candidates": [{
            "node_id": row["node_id"], "path": row["canonical_ref"]["path"],
            "why": sorted(dict.fromkeys(reason.split(" (")[0] for reason in row["why"]
                                        if not reason.startswith("claim:")),
                          key=lambda reason: (not reason.startswith("term:"), reason))[:4],
        } for row in context["candidates"]],
        "works": works, "gaps": gaps, "current_syntheses": syntheses,
        "relations": [{"from": edge["from"], "kind": edge["kind"], "to": edge["to"]}
                      for edge in context["relations"] if edge["from"] in quoted],
        "related_gaps": [{"node_id": row["node_id"], "path": row["canonical_ref"]["path"]}
                         for row in context["related_gaps"]],
        "unread_dependencies": context["unread_dependencies"],
        "cross_domain": [{"node_id": row["node_id"], "path": row["canonical_ref"]["path"],
                          "via": row["via"], "from": row["from"], "status": row["status"]}
                         for row in context["cross_domain"]],
    }


def render_progress(context):
    """Render recorded arguments and relationships, with no inferred consensus."""
    lines = ["# Research progress: " + context["topic"], "", "## Evidence coverage", "",
             "Coverage: %s; %d candidate cards. This view describes recorded evidence." %
             (context["coverage"], len(context["candidates"])), ""]
    for attempt in context["attempts"]:
        lines.append("- Query `%s`: %d index matches before selection." % (attempt["query"], attempt["hits"]))
    lines.extend(["", "## Current understanding", ""])
    for nid, node in context["current_syntheses"].items():
        lines.append("- [%s](../%s)" % (nid, node["canonical_ref"]["path"]))
        for entry in node["attrs"]["synthesis"]:
            lines.append("  [S] %s Dependencies: %s. %s" % (
                entry["statement"], ", ".join(dependencies(entry)), entry["rationale"]))
    if context["unread_dependencies"]:
        lines.append("Dependencies outside this reading set: " + ", ".join(context["unread_dependencies"]))
    for role, title in (("problem", "Problem evolution"), ("advance", "Recorded advances"),
                        ("remaining", "Remaining author questions")):
        lines.extend(["", "## " + title, ""])
        count = 0
        for work_id, work in sorted(context["works"].items(), key=lambda pair: (str(pair[1]["attrs"].get("year", "")), pair[0])):
            for row in work["attrs"].get("argument", []):
                if row["role"] != role:
                    continue
                claim_id = "claim:%s#%s" % (work_id[5:], row["claim"])
                claim = context["claims"].get(claim_id)
                if claim is None:
                    continue
                count += 1
                lines.extend([
                    "- [%s; %s] %s (%s). Scope: %s. [%s](../%s#%s) — %s" %
                    (row["attribution"], work["attrs"].get("year", ""), row["paraphrase"], work_id,
                     row["scope"], row["claim"], claim["canonical_ref"]["path"], row["claim"], claim["attrs"]["anchor"]),
                    "  Quote: " + claim["attrs"]["quote"],
                ])
        if not count:
            lines.append("No statements recorded for this role in the retrieved candidates.")
    lines.extend(["", "## Relations and disputes", ""])
    for edge in context["relations"]:
        attrs = edge["attrs"]
        lines.append("- `%s` %s `%s` [%s; %s]. %s Scope: %s. %s" % (
            edge["from"], edge["kind"], edge["to"], attrs["attribution"], attrs["comparison"],
            attrs["rationale"], attrs["scope"], attrs["anchor"]))
    if not context["relations"]:
        lines.append("No Claim-level relations recorded for the candidates; legacy cards remain available.")
    lines.extend(["", "## Current Gap synthesis", ""])
    for gap_id, gap in context["gaps"].items():
        lines.append("- `%s`: %s" % (gap_id, gap["attrs"]["status"]))
        for entry in gap["attrs"].get("synthesis", []):
            lines.append("  [S] %s Dependencies: %s; %s. %s" % (
                entry["statement"], entry["claims"], entry["gaps"], entry["rationale"]))
    lines.extend(["", "## Study conditions", ""])
    for work_id, work in context["works"].items():
        for row in work["attrs"].get("conditions", []):
            lines.append("- `%s#%s` %s: %s" % (work_id, row["evidence"], row["dimension"], row["value"]))
    lines.extend(["", "## Cross-domain reading candidates", ""])
    for item in context["cross_domain"]:
        lines.append("- `%s` via `%s` from %s: %s" % (
            item["node_id"], item["via"], ", ".join(item["from"]), item["status"]))
    lines.extend(["", "## Pending judgment reviews", ""])
    for row in context.get("pending_updates", []):
        lines.append("- `%s` / %s: %s" % (row["node_id"], row["entry"], "; ".join(row["suggestions"])))
    if "project" in context:
        project = context["project"]
        lines.extend(["", "## Project learning and decisions", "", project["research_notes"]])
        for observation in project["observation_feedback"]:
            lines.append("- [H] Review %s after %s: %s (%s). Source: %s." % (
                observation["judgment"], observation["id"], observation["interpretation"],
                observation["outcome"], observation["source"]))
    return "\n".join(lines) + "\n"


