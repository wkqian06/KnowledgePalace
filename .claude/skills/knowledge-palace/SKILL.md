---
name: knowledge-palace
description: Evidence-driven research knowledge OS over a markdown vault. Use for any /palace command or equivalent request — ingest papers, track gaps, discover cross-domain transfers, generate briefs (onboard/map/gaps/ideas/transfers/bridges), build the internal style library, add domains, run governance and audits.
---

# knowledge-palace — Claude Code runtime entry (thin adapter)

The protocol lives in the platform-neutral shared core `knowledge_palace/`;
this file only routes. Do not add or duplicate protocol content here. Every
path below is a Framework-root-relative label — resolve it against the
Framework root, never the CWD.

Read, in order, before acting on any `/palace` command:

1. `knowledge_palace/protocol/PROTOCOL.md` — storage resolution, roles and
   dispatch, write invariants, card schema, multi-domain rules, weight rules,
   governance invariants.
2. `knowledge_palace/protocol/COMMANDS.md` — the command surface and the
   per-command flow for the command at hand.

Supporting shared assets:

- Card templates: `knowledge_palace/templates/`.
- Role contracts: `knowledge_palace/agents/palace-<role>.md` (nine roles).
- Internal query contract:
  `knowledge_palace/protocol/GRAPH_QUERY_PORT.md`.

Claude Code dispatch:

- Subagent adapters are `.claude/agents/palace-<role>.md`, tools restricted to
  Read/Grep/Glob; each points to its shared contract and adds nothing of
  substance.
- Resolve the four roots deterministically:
  `python3 -m knowledge_palace.tools.config_resolver` (from the Framework
  root). Diagnose setup with `python3 -m knowledge_palace.tools.doctor`.
- Build every subagent dispatch as a task package:
  `python3 -m knowledge_palace.tools.task_package --fixture <input> --role
  <role>`, then hand the package plus resolved absolute input paths to the
  subagent.
- Before any Palace Git command, pre-flight it:
  `python3 -m knowledge_palace.tools.git_guard -- <git args>` (refuses
  non-Framework CWD/targets and unauthorized push).
- `/palace refresh` dispatches `python3 -m knowledge_palace.metadata.refresh`
  (the only network entry; cache-only without `--live` — see
  `knowledge_palace/protocol/COMMANDS.md` § Refresh).
- `/palace expand` uses `knowledge_palace/expansion/` (bounded A→B→C,
  Scope-bound decisions, checkpoints in Derived State — see COMMANDS.md
  § Expand).
- Material acquisition uses `knowledge_palace/acquisition/` (three-axis
  receipts, staged in Derived State; Source Snapshot promotion only inside
  the packaged confirmation — see COMMANDS.md § Acquisition).
