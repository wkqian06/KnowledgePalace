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
| `/palace brief onboard [<domain>]` | Background, prerequisite concepts and a purposeful reading route | palace-analyst |
| `/palace brief map <concept>` | Concept definition, distinctions and connections | palace-analyst |
| `/palace brief progress <topic>` | Problem evolution, advances, disputes and remaining questions | interaction/research.py; palace-analyst |
| `/palace brief gaps [<domain>]` | Current gaps, conditions and evidence coverage | palace-analyst |
| `/palace brief ideas [<domain>]` | Generate candidate questions from the available evidence | palace-analyst |
| `/palace brief transfers [<domain>]` | View existing transfer candidates | palace-analyst |
| `/palace brief bridges [<domain-a> <domain-b>]` | View shared concepts and cross-domain connections | semantic/corridors.py; palace-analyst |
| `/palace discover [<target>]` | Investigate cross-domain transfer candidates | palace-scout |
| `/palace idea refine <text|file>` | Develop a user idea, contribution and validation direction | palace-analyst; interaction/novelty.py |
| `/palace research <project>` | Maintain project questions, decisions, constraints and observations | workspace/research_helpers.py |
| `/palace write <project|materials> [<section>]` | Draft, develop an outline or substantially revise prose | workflows/writing.md |
| `/palace polish <text|file|project>` | Improve supplied text after understanding the manuscript | workflows/writing.md |
| `/palace feasibility <idea|file|project>` | Assess whether a design can answer the question and be executed | workflows/feasibility.md |
| `/palace draft intro <topic>` | Existing spelling for write, introduction section | workflows/writing.md |
| `/palace updates` | View evidence-dependent judgments awaiting review | interaction/research.py updates |
| `/palace updates resolve <node> <entry>` | Record a completed judgment review | interaction/research.py resolve |
| `/palace status` | Read library counts and operational state | graph/identity.py; configured stores |
| `/palace audit [<card>...]` | Review knowledge assets against source evidence | palace-auditor |
| `/palace govern` | Propose library maintenance and related judgment updates, including domain partition | PROTOCOL.md; graph/identity.py domain_partition_report |
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
`acquisition.transaction.save_paper(vault_dir, card_text)` and prepare the index
once after the batch and related knowledge edits.

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
python -m knowledge_palace.interaction.research ask "SRH" --json
python -m knowledge_palace.interaction.research progress "强对流环境时空特征" --alternative SRH
python -m knowledge_palace.interaction.research ask "取样方案" --project scs-benchmark --json
```

These commands return evidence and context, not automatically verified scientific
answers. The agent reads decisive source context and reasons from the evidence.
Unresolved refs and unread dependencies are not consumed evidence.

`research` reads project_context and updates the project's research.md when the
user asks to retain discussion. Record definitions, judgments, constraints and next
steps. Synthesis rows declare Claim/Gap dependencies; Observations point to registered
user materials. User results remain separate from literature Claims. Manuscript
analysis lives in outline/manuscript-analysis.md and is also returned in project
context. Feasibility decisions use the existing research notes, not another registry.

`updates` returns persistent review items. After reviewing evidence and making any
needed authorized edits, record the decision:

```powershell
python -m knowledge_palace.interaction.research resolve "<node>" --entry "<entry>" --decision retain --note "<reason>"
```

Decisions are retain, revise or withdraw. Recording a decision does not edit the
scientific text. Later evidence changes can reopen it.

## Write, polish and feasibility

Write and polish both read workflows/writing.md and its shared manuscript-analysis.md.
Direct materials need no project or roots configuration. Project mode uses the brief,
registered materials, current sections, analysis and selected style. Generic academic
style is the default; target-specific rules load only when requested.

`draft intro` uses write with section=introduction. It has no separate analyst draft,
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
Audit reads the affected evidence and reports actionable findings without a quota.

Viewer/wiki prepare the current index and read through GraphQueryPort. HTML writes
one requested output; wiki export only updates marked generated hubs. User notes
and original cards remain authoritative. Existing pagination and source boundaries
continue to apply. Exports never trigger Git writes.
