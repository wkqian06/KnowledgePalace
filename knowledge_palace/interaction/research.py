"""Bounded research context and progress command, plus the read-only analysis
views behind brief bridges, idea refine, govern and author-supplied references."""

import argparse
import json
import sys
import re
from pathlib import Path

from .novelty import novelty_pipeline, validate_assessment
from .project_source import resolve
from .research_helpers import bounded_context, research_context, render_progress
from ..graph.builder import ensure_index
from ..graph.identity import domain_partition_report, extract_external_ids, load_vault_identity
from ..tools.config_resolver import resolve_roots
from ..semantic.corridors import corridor_view
from ..semantic.update_helpers import load_updates, resolve_update, review_queue
from ..workspace.research_helpers import project_context


def reference_from_text(text):
    """A user-supplied reference as a resolvable record. The card-source rules
    (DOI, arXiv URL or arXiv:id) apply first, then a bare new- or old-style
    arXiv id; anything else is a title."""
    value = text.strip()
    ids = extract_external_ids(value)
    bare = re.fullmatch(r"(?i)(?:arxiv:\s?)?(\d{4}\.\d{4,5}|[a-z-]+(?:\.[a-z]{2})?/\d{7})(?:v\d+)?", value)
    if not ids and bare:
        ids = {"arxiv": bare.group(1)}
    return {"ids": ids} if ids else {"title": value}


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    # ---- Request ----
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("view", choices=("progress", "ask", "updates", "resolve", "bridges", "novelty",
                                         "assess", "partition", "source"))
    parser.add_argument("topic", nargs="?", default="")
    parser.add_argument("--config")
    parser.add_argument("--alternative", action="append", default=[])
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--project")
    parser.add_argument("--entry")
    parser.add_argument("--decision", choices=("retain", "revise", "withdraw"))
    parser.add_argument("--note", default="")
    parser.add_argument("--domain-b", help="bridges: the second domain slug")
    parser.add_argument("--file", help="assess: IdeaAssessment JSON file")
    parser.add_argument("--budget", type=int, default=24000,
                        help="ask, updates, bridges: bytes the bounded view may take (default 24000, about 6k tokens)")
    parser.add_argument("--offset", type=int, default=0, help="bridges: first corridor of the detailed page (next_offset of the previous page)")
    parser.add_argument("--axis", choices=("pattern", "function", "failure-mode", "bridge"), help="bridges: keep one corridor type")
    parser.add_argument("--full", action="store_true",
                        help="ask, updates, bridges: the complete record, indented, instead of the bounded view")
    args = parser.parse_args()
    # ---- Retrieval and view ----
    roots = resolve_roots(args.config)
    if args.view == "resolve" and not (args.topic and args.entry and args.decision and args.note.strip()):
        parser.error("resolve requires a node ID, --entry, --decision and --note")
    if args.view == "bridges" and not (args.topic and args.domain_b):
        parser.error("bridges requires two domain slugs: <domain-a> --domain-b <domain-b>")
    if args.view == "assess" and not args.file:
        parser.error("assess requires --file <assessment.json>")
    if args.view not in ("updates", "resolve", "assess", "partition") and not args.topic:
        parser.error("a research topic is required")
    document = ensure_index(roots["vault_dir"], roots["state_dir"], roots["workspace_dir"])
    policy = (Path(__file__).resolve().parents[2] / "PALACE.md").read_text(encoding="utf-8")
    hubs = re.search(r"## Hub stopwords[^\n]*\n+`([^`]+)`", policy).group(1)
    stopwords = [term.strip() for term in hubs.split(",")]
    awaiting = lambda row: row.get("status", "pending" if row["affected"] else "unchanged") == "pending"
    if args.view == "resolve":
        context = resolve_update(roots["state_dir"], args.topic, args.entry, args.decision, args.note)
    elif args.view == "updates":
        # The queue keeps every event and review; the view lists what is pending: one row per judgment,
        # or, for a node ID or ID prefix as the topic, its entries with what changed.
        queue = load_updates(roots["state_dir"])
        context = queue if args.full else review_queue(queue, args.topic, args.budget)
    elif args.view == "bridges":
        context = corridor_view(document["payload"], args.topic, args.domain_b, budget=args.budget,
                                offset=args.offset, axis=args.axis, full=args.full)
    elif args.view == "novelty":
        context = novelty_pipeline(document["payload"], args.topic, stopwords)
    elif args.view == "assess":
        assessment = json.loads(Path(args.file).read_text(encoding="utf-8"))
        context = {"errors": validate_assessment(assessment, document["payload"])}
    elif args.view == "partition":
        context = domain_partition_report(load_vault_identity(roots["vault_dir"]), stopwords=stopwords)
        context["root_pairs"] = [{"roots": list(pair), "cards": count}
                                 for pair, count in context["root_pairs"].most_common()]
    elif args.view == "source":
        context = resolve(reference_from_text(args.topic), load_vault_identity(roots["vault_dir"]))
    else:
        context = research_context(document["payload"], args.topic, args.alternative, stopwords)
        relevant = set(context["works"]) | set(context["gaps"]) | set(context["current_syntheses"])
        if args.project:
            relevant.add("project:" + args.project)
        pending = [row for row in load_updates(roots["state_dir"])["entries"]
            if awaiting(row) and (row["node_id"] in relevant or relevant.intersection(row["dependencies"]))]
        project = project_context(roots["workspace_dir"], args.project, roots["vault_dir"]) if args.project else None
        if args.view == "ask" and not args.full:
            # The complete context runs to hundreds of KB on a real library; ask prints a reading
            # plan with as many quoted Claims per work as the byte budget holds.
            frame = {"vault": str(roots["vault_dir"]),
                     "note": "Paths are relative to vault. Each work quotes a few of its claims_total "
                             "Claims; read the card for the rest.",
                     "pending_updates": [{key: row[key] for key in ("node_id", "entry", "suggestions")}
                                         for row in pending]}
            if project:
                # Decisions and observations travel with the plan; the long texts stay in their files.
                folder = Path(roots["workspace_dir"]) / "projects" / args.project
                frame["project"] = {"project": project["project"], "judgments": project["judgments"],
                                    "observation_feedback": project["observation_feedback"],
                                    "research_notes": str(folder / "research.md"),
                                    "manuscript_analysis": str(folder / "outline/manuscript-analysis.md"),
                                    "style_profiles": [row["path"] for row in project["style_profiles"]]}
            complete = context
            for claims_per_work in (4, 3, 2, 1):
                context = {**bounded_context(complete, claims_per_work), **frame}
                if len(json.dumps(context, ensure_ascii=False, separators=(",", ":")).encode("utf-8")) <= args.budget:
                    break
            else:
                context["note"] += " This plan exceeds the byte budget even at one Claim per work."
        else:
            context["pending_updates"] = pending
            if project:
                context["project"] = project
    context["snapshot"] = document["snapshot"]
    # ---- Output ----
    if args.view == "progress" and not args.json:
        print(render_progress(context))
    elif args.full and args.view in ("ask", "updates"):
        print(json.dumps(context, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(context, ensure_ascii=False, separators=(",", ":")))
