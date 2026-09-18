---
name: palace
description: Collect and read scientific papers into a persistent knowledge library, discuss research with evidence, draft or polish manuscripts, and assess experimental feasibility. Use for /palace commands or the corresponding research-library tasks.
---
# KnowledgePalace

The shared command index is `knowledge_palace/protocol/COMMANDS.md` under the
Framework root. Choose the requested command there and read only its workflow.
Shared rules: `knowledge_palace/protocol/PROTOCOL.md`. For library evidence read
`knowledge_palace/protocol/EVIDENCE.md`; graph consumers use
`knowledge_palace/protocol/GRAPH_QUERY_PORT.md`.

- init/expand: `knowledge_palace/workflows/collection.md`; selected papers use ingest.
- ingest or paper reading: `knowledge_palace/workflows/ingest.md`.
- ask: `knowledge_palace/workflows/discussion.md`.
- write/polish/draft intro: `knowledge_palace/workflows/writing.md`, then its shared manuscript analysis.
- feasibility: `knowledge_palace/workflows/feasibility.md`.
- research/updates and remaining commands: COMMANDS.md.

Resolve library roots through `knowledge_palace.tools.config_resolver` only when
needed. Direct text/material tasks do not require .palace.toml or a project.
Use existing authorized scope; collection includes selected-paper ingestion and
reading updates the knowledge card. Polishing requires manuscript analysis.

The main agent owns writes and can run a workflow directly. Optional read-only
specialists use `knowledge_palace/agents/palace-<role>.md`; runtime adapters point
to those files. Give delegates resolved paths and bounded inputs. No fixed role
sequence is required. Do not execute Git writes.
