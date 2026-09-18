"""Bounded research context and progress command."""

import argparse
import json
import sys
import re
from pathlib import Path

from .research_helpers import research_context, render_progress
from ..graph.builder import ensure_index
from ..tools.config_resolver import resolve_roots
from ..semantic.update_helpers import load_updates, resolve_update
from ..workspace.research_helpers import project_context

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    # ---- Request ----
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("view", choices=("progress", "ask", "updates", "resolve"))
    parser.add_argument("topic", nargs="?", default="")
    parser.add_argument("--config")
    parser.add_argument("--alternative", action="append", default=[])
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--project")
    parser.add_argument("--entry")
    parser.add_argument("--decision", choices=("retain", "revise", "withdraw"))
    parser.add_argument("--note", default="")
    args = parser.parse_args()
    # ---- Retrieval and view ----
    roots = resolve_roots(args.config)
    if args.view == "resolve" and not (args.topic and args.entry and args.decision and args.note.strip()):
        parser.error("resolve requires a node ID, --entry, --decision and --note")
    if args.view not in ("updates", "resolve") and not args.topic:
        parser.error("a research topic is required")
    document = ensure_index(roots["vault_dir"], roots["state_dir"], roots["workspace_dir"])
    if args.view == "resolve":
        context = resolve_update(roots["state_dir"], args.topic, args.entry, args.decision, args.note)
    elif args.view == "updates":
        context = load_updates(roots["state_dir"])
    else:
        policy = (Path(__file__).resolve().parents[2] / "PALACE.md").read_text(encoding="utf-8")
        hubs = re.search(r"## Hub stopwords[^\n]*\n+`([^`]+)`", policy).group(1)
        stopwords = [term.strip() for term in hubs.split(",")]
        context = research_context(document["payload"], args.topic, args.alternative, stopwords)
        relevant = set(context["works"]) | set(context["gaps"]) | set(context["current_syntheses"])
        if args.project:
            relevant.add("project:" + args.project)
        context["pending_updates"] = [row for row in load_updates(roots["state_dir"])["entries"]
            if row.get("status", "pending" if row["affected"] else "unchanged") == "pending"
            and (row["node_id"] in relevant or relevant.intersection(row["dependencies"]))]
        if args.project:
            context["project"] = project_context(roots["workspace_dir"], args.project, roots["vault_dir"])
    context["snapshot"] = document["snapshot"]
    print(json.dumps(context, ensure_ascii=False, indent=2) if args.json or args.view != "progress"
          else render_progress(context))
