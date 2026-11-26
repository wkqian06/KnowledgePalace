# KnowledgePalace Commands

Use the workflow for the requested task. Commands are agent entrypoints; only
mechanical storage, retrieval and export operations require Python. No command
requires running every role. Shared rules live in PROTOCOL.md and EVIDENCE.md.

| Command | Responsibility | Workflow / implementation |
|---|---|---|
| `/palace init <topic> [n]` | Build or extend a topic collection; selected papers are ingested | workflows/collection.md |
| `/palace expand <target>` | Follow references/related research from papers or an evidence hole; selected papers are ingested | workflows/collection.md; expansion/ |
| `/palace ingest [<paths|dois|paper-slugs>...]` | Read and create/update the corresponding paper cards | workflows/ingest.md |
| `/palace ask <question>` | Explanation, comparison and continuing research discussion | workflows/discussion.md |
| `/palace brief onboard [<domain>]` | Background, prerequisite concepts and a purposeful reading route | workflows/discussion.md |
| `/palace brief map <concept>` | Concept definition, distinctions and connections | workflows/discussion.md |
| `/palace brief progress <topic>` | Problem evolution, advances, disputes and remaining questions | workflows/discussion.md; interaction/research.py progress |
| `/palace brief gaps [<domain>]` | Current gaps, conditions and evidence coverage | workflows/discussion.md |
| `/palace brief ideas [<domain>]` | Generate candidate questions from the available evidence | workflows/discussion.md |
| `/palace brief bridges [<domain-a> <domain-b>]` | View bridge cards by status, shared concepts and cross-domain connections | workflows/discussion.md; interaction/research.py bridges |
| `/palace discover [<target>]` | Investigate cross-domain bridge candidates | workflows/discussion.md |
| `/palace idea refine <text|file>` | Develop a user idea, contribution and validation direction | workflows/discussion.md; interaction/research.py novelty, assess |
| `/palace research <project>` | Maintain project questions, decisions, constraints and observations | workspace/research_helpers.py |
| `/palace write <project|materials> [<section>]` | Draft, develop an outline or substantially revise prose | workflows/writing.md |
| `/palace polish <text|file|project>` | Improve supplied text after understanding the manuscript | workflows/writing.md |
| `/palace feasibility <idea|file|project>` | Assess whether a design can answer the question and be executed | workflows/feasibility.md |
| `/palace draft intro <topic>` | Existing spelling for write, introduction section | workflows/writing.md |
| `/palace updates` | View evidence-dependent judgments awaiting review; each ingest reviews those it opened | interaction/research.py updates |
| `/palace updates resolve <node> <entry>` | Record a completed judgment review | interaction/research.py resolve |
| `/palace status` | Read library counts and operational state | graph/identity.py; configured stores |
| `/palace audit [<card>...]` | Review knowledge assets against source evidence | palace-auditor |
| `/palace govern` | Propose library maintenance and related judgment updates, including domain partition | PROTOCOL.md; interaction/research.py partition |
| `/palace refresh <impact|citations|metadata> [<scope>]` | Refresh bibliographic information | metadata/refresh.py |
| `/palace domain add <name>` | Register a new domain and its initial concepts | domains.md, concepts.md |
| `/palace domain list` | List registered domains | domains.md |
| `/palace style ingest|status|crystallize` | Maintain style examples and profiles | palace-stylist |
| `/palace viewer export [<output-path>]` | Export a read-only HTML view | viewer/cli.py |
| `/palace wiki export [<dir>]` | Export generated Obsidian hubs | viewer/obsidian.py |

## Read and collect

Read workflows/collection.md for init/expand, then workflows/ingest.md for every
selected paper. Read workflows/ingest.md directly for supplied papers or deeper
reading of an existing card. Adopted outside papers in all other workflows follow
the same path. A search hit is temporary until selected; a selected paper receives
a card even if only verified metadata or its abstract is available.

Existing explicit user selection and authorization remain valid. New choices
about ambiguous identity or expanded scope require resolution, not a repeated
approval of the same papers. Save reviewed cards through
`acquisition.transaction.save_paper(vault_dir, card_text, source_dir)` and prepare
the index once after the batch and related knowledge edits. With `source_dir`, new
Claim quotes are checked verbatim against the paper's cached text.

Network access is task-scoped: collection, acquisition and requested external
research may use available providers or web tools. Refresh only owns bibliographic
refresh; it is not the only legitimate network workflow. Govern remains read-only
until approved maintenance and does not silently fetch new literature.

## Ask, brief and research

Ask reads workflows/discussion.md. A missing paper Claim does not prevent a clearly
identified background explanation or tentative hypothesis. Brief views synthesize
selected library evidence; map explains a concept, progress tracks the research
question. Neither requires a numeric score or a fixed paper quota.

For library context, from the Framework directory:

```powershell
python -m knowledge_palace.interaction.research ask "echo cancellation"
python -m knowledge_palace.interaction.research progress "echo cancellation under reverberation" --alternative EC
python -m knowledge_palace.interaction.research ask "sampling design" --project <project-slug>
```

`ask` prints a bounded reading plan within `--budget` bytes (default 24000): every
candidate, a few quoted Claims per work, query matches first. `--full` prints the
complete context. The same module serves the other read-only analysis views:

```powershell
python -m knowledge_palace.interaction.research novelty "<idea text>"
python -m knowledge_palace.interaction.research assess --file <assessment.json>
python -m knowledge_palace.interaction.research partition
python -m knowledge_palace.interaction.research source "<DOI, arXiv id or title>"
```

`novelty` gives idea refine its corridors, closest works and related Claims;
`assess` lists the errors in an IdeaAssessment; `partition` is govern's domain
partition input; `source` resolves an author-supplied reference against the
library.

These commands return evidence and context, not automatically verified scientific
answers. The agent reads decisive source context and reasons from the evidence.
Unresolved refs and unread dependencies are not consumed evidence.

`brief bridges` reads the typed corridors between two domains (bridge cards and
shared-axis concepts); without arguments, run it for each registered domain pair
in `domains.md`:

```powershell
python -m knowledge_palace.interaction.research bridges <domain-a> --domain-b <domain-b>
python -m knowledge_palace.interaction.research bridges <domain-a> --domain-b <domain-b> --offset <next_offset>
```

Corridors come strongest first (bridge cards, then concepts by the smaller endpoint
count); `corridors` holds the detailed page, `more` lists the rest briefly, and
`by_axis` counts all of them. While `next_offset` is not null, call again with
`--offset <next_offset>` (or narrow with `--axis`) before ranking or recommending
corridors, and say which pages were read. `--full` prints every corridor in detail.

`research` reads project_context and updates the project's research.md when the
user asks to retain discussion. Record definitions, judgments, constraints and next
steps. Synthesis rows declare Claim/Gap dependencies; Observations point to registered
user materials. User results remain separate from literature Claims. Manuscript
analysis lives in outline/manuscript-analysis.md and is also returned in project
context. Feasibility decisions use the existing research notes, not another registry.

`updates` lists the judgments awaiting review, one row per judgment. Review them
node by node: `updates "<node ID or ID prefix such as gap:>"` gives those entries
with their dependencies and the nodes and edges that changed, and `updates --full`
prints the whole queue with its event and review history. When the view's note
says rows were left out, narrow the prefix until every row has been seen. After
reviewing evidence and making any needed authorized edits, record the decision:

```powershell
python -m knowledge_palace.interaction.research resolve "<node>" --entry "<entry>" --decision retain --note "<reason>"
```

Decisions are retain, revise or withdraw. Recording a decision does not edit the
scientific text. Later evidence changes can reopen it.

Updates and govern divide maintenance by scope. Each ingest reviews, through
`updates`, the entries its batch opened (workflows/ingest.md). Govern decides what
needs the whole library: concept promotions, orphan and deprecated tags, recurring
unregistered terms, domain partition, gap rows that paper cards declare and gap
cards lack, and Gap status moves, which follow the counting rules and a
palace-auditor review: each move goes to the auditor with the gap card, the cited
paper cards and their cached source texts before it is proposed. Govern also
takes the queue entries no ingest reviewed. Project entries are the user's research decisions under both routes.

## Write, polish and feasibility

Write and polish both read workflows/writing.md and its shared manuscript-analysis.md.
The author gives the framing, motivation and design, however briefly; the text is
then written in one pass from the analysis's argument graph (light nodes and
labelled links: one node per paragraph, and a chain from opening to landing inside
each) under the numbered writing rules in writing.md, which the review reports
against. The graph precedes the text in what is delivered, and the author revises
by changing its nodes and links.
Direct materials need no project or roots configuration. Project mode uses the brief,
registered materials, current sections, analysis and selected style. Generic academic
style is the default; target-specific rules load only when requested.

`draft intro` uses write with section=introduction. It has no separate draft route,
audit loop or save policy. Polish defaults to the requested passage and preserves
scientific meaning; substantive changes are explicitly within write scope.

Feasibility reads workflows/feasibility.md. It evaluates the supplied plan and real
constraints. Idea refine develops the idea; feasibility judges the design; research
retains the decision. Neither field completeness nor software test results establish
scientific feasibility.

Saved project sections use workspace.revision.save_revision and remain append-only.
Direct tasks return prose or save at the selected destination without overwriting the
source by default. Analysis notes stay separate. Missing user results remain marked
as missing; source evidence and actual user findings are never interchangeable.

## Maintenance and exports

Status reads the configured stores and reports current counts, missing sources or
index state without changing authoritative content. Govern handles concrete issues
such as duplicate concepts, stale metadata, uncurated cards or pending syntheses.
Audit goes to palace-auditor with the cards, their cached source texts (the
card's `local:` under the Source Cache), `PALACE.md`, EVIDENCE.md, `concepts.md` and
the Vault root; it reads the affected evidence and reports actionable findings
without a quota. Fixes go through the normal confirm-then-write path. Without a
separate context the same checks run in the main session and are reported as a
same-session check.

Viewer/wiki prepare the current index and read through GraphQueryPort. HTML writes
one requested output; wiki export only updates marked generated hubs. User notes
and original cards remain authoritative. Existing pagination and source boundaries
continue to apply. Exports never trigger Git writes.
