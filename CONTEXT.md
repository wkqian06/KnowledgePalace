# KnowledgePalace

KnowledgePalace is an evidence-driven research knowledge system that separates
confirmed knowledge, literature discovery, and rebuildable query state.

## System Boundaries

**Framework**:
The public protocols, schemas, agents, and executable capabilities that operate
on private KnowledgePalace data. It is the only boundary Palace may manage with
Git.
_Avoid_: Knowledge base, vault

**Personal Vault**:
A user's independently stored collection of confirmed research knowledge and
research decisions. Any version control is optional and exclusively user-managed.
_Avoid_: Framework repository, cache

**Vault Graph**:
The authoritative, multi-level knowledge graph expressed by the human-readable
artifacts in a Personal Vault, including both nodes and confirmed relationships.
_Avoid_: Graph Index, cache

**Derived State**:
Rebuildable operational data that accelerates or resumes work without becoming
authoritative research knowledge.
_Avoid_: Vault Graph, evidence

**Source Cache**:
An independently stored collection of immutable full-text snapshots used by
Vault evidence pointers.
_Avoid_: Personal Vault, Derived State

**Research Workspace**:
An independently stored collection of user-confirmed project materials,
revisions, reviews, bibliographies, and exports.
_Avoid_: Personal Vault, Source Cache

**Graph Index**:
A rebuildable query projection of the Vault Graph.
_Avoid_: Knowledge graph, source of truth

**Bibliographic Cache**:
Dated observations retrieved from external scholarly providers, including work
identities and citation neighborhoods.
_Avoid_: Confirmed knowledge, evidence claim

**ImpactSnapshot**:
A dated, per-Work record of raw impact observations — field-normalized
citation percentile, categories, optional licensed JCR quartiles, venue
metrics — stored side by side in Derived State without any global band.
_Avoid_: Global score, absolute threshold

**Evaluation Context**:
The explicit category and evaluation year under which one contextual band is
computed and recorded; the same Work may band differently in different
contexts.
_Avoid_: Global ranking, best category

**Run Checkpoint**:
Temporary state that allows an interrupted operation to resume without changing
the meaning or authority of the Personal Vault.
_Avoid_: Decision record

## Research Knowledge

**Work**:
One intellectual research contribution, independent of where or in which version
it was published.
_Avoid_: File, provider record, paper version

**Manifestation**:
A specific published or distributed version of a Work, such as an arXiv revision
or journal version of record.
_Avoid_: Work

**Claim**:
An immutable, evidence-anchored statement extracted from a specific Manifestation
of a Work.
_Avoid_: Summary, synthesis

**StudyProfile**:
An optional methodology view over one Work's Claims — role references from
exactly one set (empirical, review, or theoretical), each resolving to an
anchored Claim; never a second store of facts.
_Avoid_: Second fact store, mandatory field

**Candidate Work**:
A metadata-verified Work under consideration that has not yet completed formal
ingestion into the Personal Vault.
_Avoid_: Paper card, Claim

**Bibliographic Edge**:
A directed observation that one Work references another Work; reverse-citation
views are computed from the same edge.
_Avoid_: Citation count, evidence relation

**Potential Link**:
An explainable but unconfirmed connection suggested by the graph for later
evidence review.
_Avoid_: Transfer, established relation

## Views, Query, and Governance

**Brief**:
A dated, disposable synthesis view saved in the Personal Vault. Its object role
is `view`: it can locate the sources it cites but can never generate an
evidence edge or serve as an evidence source for a Claim.
_Avoid_: Evidence, source of truth

**GraphQueryPort**:
The internal, UI-neutral, read-only query contract over the rebuildable Graph
Index. Every response carries a schema version and an index snapshot; a stale
index rejects queries.
_Avoid_: HTTP API, Viewer

**CanonicalRef**:
A logical reference of root, path, and anchor that opens an authoritative card
or section without exposing any absolute filesystem path.
_Avoid_: Absolute path, URL

**Hierarchy**:
A registry-defined, ordered set of named levels in which graph nodes are
placed. Multiple hierarchies coexist and a node may be placed differently in
each; registry-driven extensibility, not a fixed four-level taxonomy.
_Avoid_: Fixed taxonomy, folder tree

**Viewer State**:
Layout, filters, navigation history, community assignments, and dismissed
visual suggestions. It belongs only to Derived State or browser-local storage;
deleting all of it causes no knowledge loss.
_Avoid_: Vault knowledge, decision record

**Governance Decision**:
A dated, append-only private record in the Vault governance log capturing one
confirmed registry or policy decision with its rationale, affected objects, and
provenance.
_Avoid_: Public policy, computed count

## Interaction

**InteractionSession**:
The resumable Derived-State record of one Ask/Idea exchange — question,
mode, candidates, coverage, proposal decisions, history; deletable without
knowledge loss.
_Avoid_: Vault record, decision authority

**CoverageReport**:
The verdict structure gating what an answer may claim: sufficient, partial
(covered part answered, holes named), or insufficient (no fabricated
answer; an ExpansionProposal instead), with id-shaped evidence.
_Avoid_: Domain gate, confidence score

**ExpansionProposal**:
A bounded, user-confirmable bridge from coverage holes to an
Expansion Run (seeds/queries, depth ≤2, budget ≤50); rejection changes
nothing.
_Avoid_: Automatic search, executed run

**NoveltyProfile**:
The per-project selection of dimensions (theory, mechanism, method, data,
evaluation, empirical finding, system integration, application transfer,
scale generalization) on which novelty is even claimed.
_Avoid_: Uniform "is the method new", global novelty score

**IdeaAssessment**:
The bounded idea-refine verdict: supporting/opposing/unknown evidence side
by side, closest prior work, falsifiers and a minimal experiment required;
novelty vault-relative by default, external statements only within a
recorded search scope + date.
_Avoid_: Absolute novelty claim, unbounded literature review

**ProjectSource**:
An author-supplied reference resolved against Vault identity first: hit →
the existing Work is reused; miss → a verified session-local source that
never auto-enters the Vault.
_Avoid_: Auto-ingest, duplicate Work identity

**ResearchProject**:
One Workspace project (`projects/<slug>/`): document kind, audience,
venue, language, length, citation style, style profile, status; the
current revision is computed from files, never stored.
_Avoid_: Vault record, Git repository

**ProjectMaterial**:
User-supplied writing input (drafts, data, figures, solicitations,
reviewer comments) — usable for writing, never Vault Claim evidence.
_Avoid_: Evidence claim, ingested source

**Revision**:
One confirmed full-text save, `rNNN.md`, append-only; prior revisions are
immutable and exports never overwrite them.
_Avoid_: Working draft, overwrite

**ProjectBrief**:
The frozen, fingerprinted writing contract: genre parameters, section
plan, and the evidence package every writer package must stay within.
_Avoid_: Retrieval scope, mutable outline

**RequirementsMatrix**:
Anchored requirement rows from a solicitation with named
section-coverage tracking; the no-solicitation fallback is born
compliance-unverifiable.
_Avoid_: Silent compliance claim, summarized coverage

**ExportPlan**:
A replayable, deterministic pandoc invocation plan (CSL resolution,
relative paths, exact arguments); outputs never overwrite anything and
Markdown stays the canonical source.
_Avoid_: Editing source, live network fetch

## Literature Expansion

**Expansion Run**:
A bounded literature-discovery operation rooted in one or more ingested Works and
evaluated relative to one explicit Scope.
_Avoid_: Ingestion, unbounded loop

**Scope**:
The domain, topic, paper, gap, or concept relative to which Candidate Works and
selection decisions are judged.
_Avoid_: Global relevance

**Expansion Frontier**:
The deduplicated set of Works that remain eligible for traversal within an
Expansion Run.
_Avoid_: Ingest queue

**Vault Hit**:
A discovered Work that already exists in the Personal Vault and therefore does
not require another ingestion.
_Avoid_: Candidate Work

**Selection Decision**:
A scope-specific choice to select, defer, or reject a Candidate Work, together
with its rationale and decision provenance.
_Avoid_: Global paper status

**Domain View**:
A query-scoped projection of the global Vault Graph for one domain, including its
local concepts and relevant shared bridges without duplicating global nodes.
_Avoid_: Separate domain graph

## Acquisition

**MaterialReceipt**:
The uniform three-axis record of one acquisition attempt — acquisition,
identity, and text status — with compact attempts and a next action; no axis
can compensate for another.
_Avoid_: Provider log dump, Claim

**Source Snapshot**:
An immutable full-text file promoted into the Source Cache only through the
confirmed transaction; identical re-promotion is a no-op and a differing
hash is refused.
_Avoid_: Staged download, editable copy

## Shared Core and Runtimes

**Shared Core**:
The platform-neutral `knowledge_palace/` layer — protocol, role contracts,
templates, and deterministic tools — consumed identically by every runtime.
_Avoid_: Runtime adapter, private data

**Runtime Adapter**:
A thin per-runtime entry (Claude Code or Codex) that routes to the Shared Core
and never duplicates protocol bodies.
_Avoid_: Protocol authority, second protocol copy

**Role Contract**:
The platform-neutral definition of one read-only subagent role in the Shared
Core, bound unchanged by every runtime's adapter.
_Avoid_: Runtime adapter, prompt experiment

**Task Package**:
The deterministic, runtime-independent dispatch payload the Shared Core builds
for one role over the orchestrator's handed inputs.
_Avoid_: Chat transcript, cached authority

**Palace Doctor**:
The read-only diagnostic tool reporting root resolvability and both runtimes'
contract completeness; it never writes and never uses the network.
_Avoid_: Fixer, migration tool

**Git Target Guard**:
The advisory pre-flight check that refuses any Palace Git invocation whose CWD
or target leaves the Public Framework, and any unauthorized push.
_Avoid_: Sandbox, private-root inspector

**Palace Viewer Export**:
A deterministic, one-file static HTML build over the frozen GraphQueryPort —
opened offline via file://, zero outbound network calls, zero new
dependency. Not a live server.
_Avoid_: HTTP service, editable graph, search backend
