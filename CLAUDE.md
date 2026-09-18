# KnowledgePalace — Agent Contract

Evidence-backed paper collection, reading, discussion, writing and experiment
planning. AGENTS.md and CLAUDE.md are identical runtime contracts. Shared task
instructions live in knowledge_palace/workflows/; the current command table is
knowledge_palace/protocol/COMMANDS.md. Load the requested workflow only.

## Command routing

- init / expand → workflows/collection.md → selected papers use ingest.
- ingest (including deeper reading of existing papers) → workflows/ingest.md.
- ask → workflows/discussion.md; brief views → palace-analyst and EVIDENCE.md.
- write / polish / draft intro → workflows/writing.md and manuscript-analysis.md.
- feasibility → workflows/feasibility.md.
- research / updates → project research context and evidence review records.
- discover develops cross-domain transfers; idea refine develops the user's idea.
- status, audit, govern, refresh, domain, style, viewer and wiki retain their
  specific responsibilities in COMMANDS.md.

Natural-language requests use the same routes. There are no separate collect,
read or discuss commands. draft intro is write's introduction route. Direct
writing/polishing/feasibility tasks do not require a new project.

## Storage and evidence

Read protocol/PROTOCOL.md for shared storage and write rules. Resolve .palace.toml
only when library/project access is needed: vault_dir, state_dir, source_dir,
workspace_dir are relative to the configuration file, not CWD. Python helper:
knowledge_palace.tools.config_resolver. Full papers stay in Source Cache; cards
contain anchored evidence. Graph Index is derived and rebuildable.

Read protocol/EVIDENCE.md when handling Claims, conditions, relations and current
syntheses. Keep original Claim IDs, quotes and anchors. Corrections append. Store
user results as project materials, not published Claims. Citation/venue metrics
are context; scientific judgments follow evidence, design and conditions.

Every selected/adopted outside paper is ingested. Abstract/metadata-only cards state
their limits and never invent full-text findings. A completed reading updates its
paper card. Save via acquisition.transaction.save_paper and prepare the index after
the batch. Historical project-source references remain readable.

## Execution and authorization

The main agent chooses and composes workflows, audits important evidence and
performs authorized writes. Existing explicit task authorization persists; do not
ask the user to reselect papers or reapprove the same scope. Resolve only material
ambiguities. Unrequested saved discussions and project creation need user intent.

The nine role contracts under knowledge_palace/agents/ are optional specialists,
not a mandatory sequence. A straightforward task may be completed by the main
agent. Delegates receive resolved inputs and a bounded reading scope, return drafts,
and NEVER write, edit, or create files. The two runtimes use thin adapters pointing
at these contracts. No native-agent dependency is required for the main workflow.

Collection, acquisition and user-requested external research can use network tools
within their task scope. Refresh owns metadata refresh only. Govern does not fetch
or edit automatically. Never install a service or external skill merely to run an
internal workflow.

## Mechanical core

Reuse existing metadata, acquisition, identity, retrieval, graph, revision and export
code. Keep checks at actual parsing/write boundaries: identity, evidence references,
source preservation, correct destinations and recoverable state. Avoid new validator
scripts, internal repeated sanity checks, scores or state machines for prose tasks.

GraphQueryPort remains a five-operation read-only interface; see
knowledge_palace/protocol/GRAPH_QUERY_PORT.md. Index preparation is separate from
query evaluation. Scientific truth is evaluated from sources, not schema success.

## Git

All Git writes are user-only. Do not stage, commit, push, change branches, configure
Git or create worktrees. No Git commands target private roots. Framework inspection
may use read-only Git commands. Complete workspace edits and leave Git to the user.
