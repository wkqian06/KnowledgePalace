# KnowledgePalace shared protocol

## Task routing

COMMANDS.md is the single command index. Workflows under ../workflows/ define
collection, ingest, discussion, manuscript analysis, writing/polishing and
feasibility. Read only the requested workflow and its necessary shared steps.
Roles are optional specialists; the main agent may execute the same workflow.

## Storage resolution

When accessing the library/project, resolve .palace.toml against its own directory:
vault_dir, state_dir, source_dir and workspace_dir are distinct roots outside the
Framework. Direct-material tasks do not need these roots or a new project.

- Vault: papers, concepts, gaps, transfers, current syntheses and style records.
- Source Cache: full texts and their source versions; cards carry relative locators.
- Workspace: user materials, project context, manuscript analysis and saved sections.
- Derived State: reconstructible indexes, discovery/session records and task drafts.
  Preserve synthesis-updates.json when rebuilding: it also holds review decisions.

Private Git topology is user-managed. No Git command targets a private root. All
Git writes, including Framework writes, are performed by the user only.

## Reading and evidence

A selected/adopted outside paper is ingested; completed reading updates its card.
Use ../workflows/ingest.md and the paper-card template. Reuse existing Work identity
and Claim numbers. Record actual read_depth (full, skim, abstract, metadata) and
source_coverage (full-text, excerpt, abstract, metadata). Older cards may omit
source_coverage; absence means not recorded, never inferred full coverage.

Metadata-only cards contain no scientific Claims. Abstract-only Claims quote the
abstract and retain that source boundary. Possessing full text is not full reading.
Every new Claim has an exact quote, a real source locator and canonical concepts.
Claim IDs are immutable and the author's wording is authoritative. Three errors,
three different actions. A scientific error — the quote is this work's and
accurate, but its reading, scope or boundary was wrong — appends a Correction
and, where needed, a new Claim; the quote itself stays. A transcription error —
the recorded wording does not match the source, through a dropped citation,
clause, qualifier or index — is repaired in place toward the source, with no
Correction: a quote that never matched the paper was never the evidence, and
restoring it is what immutability protects. A provenance error — the quote is
not in this work at all — is retracted in place with
`- Retraction of C<n> (<date>): <note>`, never edited or deleted.

Every repair is checked against the cached source first. That check also decides
the smaller case: a quote found elsewhere in this work corrects only its anchor.
Repairs move toward the source and never away, so save_paper accepts a changed
quote only when the new wording is verbatim in that work's cached text and
refuses it when no cached text exists. A retracted Claim leaves the work's claims
edge, binds no concept and cannot be cited by Argument, Conditions or Evidence
relations rows. No missing method, result or limitation is filled from an unseen
section.

Read EVIDENCE.md for Argument, Conditions, evidence relations and synthesis tables.
These are optional structured views; omission means uncurated. Interpretations,
hypotheses and user observations are distinct from original literature assertions.
Current synthesis records can change without rewriting historical author statements.

Scientific confidence follows design, direct evidence, conditions and dependence
between datasets/analyses. Citation counts, venue and publication type are context.
No automated score or successful schema validation establishes a scientific claim.

## Authorized writes

The main agent performs writes; delegated readers return drafts and NEVER write,
edit, or create files. Explicit ingest or selection within an authorized collection
includes card/source preservation. Carry prior authorization forward. Ask only for
unresolved identity, changed scope or genuinely missing user intent.

save_paper is the common paper-card write boundary: identity reuse, old Claims,
new references and INDEX update. Rebuild derived context once after the batch and
related Gap edits. Source promotion retains immutable originals. Saved project
sections use append-only revisions; polish never overwrites its source by default.

User manuscripts, experiment data and analysis notes are project materials. They
can support the user's writing and research decisions but never become published
paper Claims. Important discussion is saved when requested. Short direct tasks
may remain in conversation without project creation.

## Discussion and writing

Ask may explain background and discuss hypotheses beyond the current card set,
while separating them from retrieved evidence. Coverage records apply to the
literature-backed portion only. New adopted literature goes through ingest before
final library citation; unresolved acquisition is reported as an incomplete step.
Temporary external records remain discovery state, not another permanent library.

Write and polish share manuscript-analysis.md. Use source document/version,
argument, section roles, intent, terms and unresolved evidence to guide the draft.
Reuse an applicable analysis; update it after relevant changes. Project analysis
lives at outline/manuscript-analysis.md. Direct work uses supplied context.

Use normal citations in prose, backed by selected evidence; internal provenance
labels need not appear in every user-facing sentence. No user results means no
invented Results text. Focused revision follows actual findings, with at most two
automatic revisions for a section; no Python state machine is required.

## Concepts, relations and review

Keep the seven existing concept axes and canonical slugs. Domain-specific meaning
lives in records, not Python enums. Inter-domain connections are shared concepts,
justified Gap analogies or directed transfers, not cross-domain Parents links.

Status reads current facts. Audit reviews source fidelity and inference. Govern
proposes meaningful maintenance; it neither fetches nor writes automatically.
Refresh updates bibliographic metadata; collection/acquisition and authorized
external research may also use network tools within their task scope.

## Mechanical guarantees

Use checks where failure changes storage or execution: correct paths and identity,
resolvable references, original evidence preservation, complete query/pagination,
recoverable project state. Keep them at the actual boundary, not repeated between
internal helpers. Review scientific content through source comparison and reasoning.

GraphQueryPort remains the read-only five-operation contract in GRAPH_QUERY_PORT.md.
Index preparation may rebuild Derived State. Viewer exports one requested HTML;
wiki export updates marked generated hubs and preserves unmarked user content.
Existing logical-reference, paging and source-text boundaries continue to apply.
