# KnowledgePalace Commands — surface and flows

Platform-neutral command reference. Rules of engagement (storage resolution,
roles, write invariants, schema, weights, governance) live in `PROTOCOL.md`
and bind every flow below.

## Commands

| Command | Flow | Output |
|---|---|---|
| `/palace ingest [<paths\|dois>...]` | Ingest (single/batch) | paper cards + gap backflow + INDEX rows |
| `/palace status` | Status | live-computed counts + consistency report (no writes) |
| `/palace brief onboard [<domain>]` | Brief | concept-tree domain map, high-frequency core vocabulary, 5–8-paper reading path covering distinct subtrees |
| `/palace brief map <concept>` | Brief | chronological method-generation timeline, established conclusions ([C] + weight), disputes side-by-side, gap state under the concept |
| `/palace brief gaps [<domain>]` | Brief | open/disputed gaps ranked qualitatively by relation count and the weights present (no numeric formula — PALACE.md rule 4): who tried, why unresolved, remaining uncertainty, open subquestions |
| `/palace brief ideas [<domain>]` | Brief | ranked research-opportunity cards: open gap × transfer candidate × weight → hypothesis, grounds ([C]/[S]/[H]), assumptions, risks, minimal validation experiment, possible paper contribution |
| `/palace brief transfers [<domain>]` | Brief | current transfer radar (cards by status) |
| `/palace brief bridges [<domain-a> <domain-b>]` | Brief | domain-pair connection report (pure computed view, no new storage); no args → full cross-domain connection matrix |
| `/palace discover [<target>]` | Discover | candidate transfer cards for user selection |
| `/palace style ingest\|status\|crystallize` | Style | bank cards / library status / journal- or lang- profiles |
| `/palace domain add <name>` | Domain add | seeded concept subtree + Vault registry row |
| `/palace domain list` | Domain | domains table from Vault `domains.md` |
| `/palace govern` | Govern | trigger scan → proposals + impact lists → confirmed edits |
| `/palace audit [<card>...]` | Audit | auditor findings over the vault or the given cards |
| `/palace init <topic> [n]` | Init | topic-searched candidate list (~n, default 50) → one circled selection → batch ingest |
| `/palace refresh <impact\|citations\|metadata> [<scope>]` | Refresh | explicit provider fetch → Derived State snapshots + proposal reports; the ONLY network entry |
| `/palace ask <question>` | Ask | vault-grounded answer ([C]/[S]/[H] per sentence) or "not in vault" + expansion advice; no writes by default |
| `/palace idea refine <text\|file>` | Idea refine | evidence-graded critique + upgraded idea card (novelty-checked vs gaps/transfers/ideas) |
| `/palace draft intro <topic>` | Draft intro | provenance-tagged introduction draft for any topic, coverage-checked |
| `/palace write <project> [<section>]` | Write | project-based section-wise Paper drafting: frozen brief → writer/reviewer loop (≤2 rounds) → confirmed rNNN revision; no-save = chat-only |
| `/palace viewer export [<output-path>]` | Viewer export | one self-contained, offline HTML file for local read-only graph browsing; no LLM in the loop |

## Status (definition)

Compute live, report, write nothing:

- Discovery: runtime entry loaded + the nine shared role contracts present
  (`glob <Framework root>/knowledge_palace/agents/palace-*.md` == 9) + the
  current runtime's adapters present (`tools/doctor.py` verifies both runtimes).
- Counts: papers, gaps, transfers, briefs, style bank cards, style profiles —
  each store = `*.md` files minus its `INDEX.md`; concepts per axis = data rows
  per section of `concepts.md`, domains = data rows of the `domains.md`
  table only (data row = `^\| [a-z]`, excluding header/separator rows).
- Consistency: INDEX row count == card file count (papers, gaps, styles/bank,
  styles/profiles); orphan check — every axis tag in every card frontmatter
  matches a registry Slug cell exactly (`grep -E '^\| <slug> \|' concepts.md`;
  alias or substring matches do NOT count — cards must use canonical slugs).
- Gates: discover gate reached? Governance cadence and seven-day ingest-rate
  fields require non-Git event tracking; until that exists, report those fields
  as `unavailable` rather than inspecting private repository history. Backlog is
  user-reported.
- Framework revision hash + date may be reported only by running Git from the
  Framework root; it is not a Vault revision.

## Flows

### Ingest (single or batch)

1. Fetch full text (delegate to reader/downloader providers) and metadata +
   citation count (academic-search providers: OpenAlex / Crossref / Scopus).
   Stamp `citations_date`; note IF source. Fallback when these capabilities are
   absent in the runtime: query the OpenAlex API directly
   (`api.openalex.org/works/doi:<doi>`) for metadata/citations and ask the user
   for a local full-text path.
2. Dedup gate: derive the tentative slug (`<firstauthor>-<year>-<titleword>`)
   from the metadata NOW, then grep `papers/INDEX.md` for slug/title and grep
   the DOI across card frontmatter (`grep -l "<doi>" papers/*.md`). On hit,
   offer three choices — **skip** / **deepen** (skim→full: add new Claims and
   gap relations, never touch existing quotes) / **correct** (append correction
   entries, marked; never overwrite — evidence is immutable).
3. palace-extractor → paper-card draft (claims with verbatim anchors,
   limitations→gap candidates, transfer notes, suggested weight band).
4. Main agent grep prefilter: registry sections + gap INDEX + peer INDEX rows →
   5–15 candidate cards.
5. palace-linker → slug alignment table, new-concept proposals (≤5/paper), gap
   relation table incl. weighted status-change proposals with rationale.
6. ONE packaged confirmation to the user (per batch of 5–10 in batch mode;
   uncertain papers pulled out for per-paper review).
7. Main agent writes confirmed cards + INDEX rows + registry candidates to the
   configured Vault. No Palace Git operation follows.
8. If the venue is a submission target or the writing is worth learning, offer to
   run `style ingest` on the same paper.

Ingestion into an existing domain triggers, automatically: gap backflow (status
proposals + rationale), concept support evolution (candidate → canonical promotion
proposal at ≥3 papers), governance trigger accumulation.

### Brief (all views, including ideas)

palace-analyst drafts → **palace-auditor audits** (anchors, [C]/[S]/[H] boundary,
source_type). Auditor FAIL → back to analyst for revision (max 2 loops, then
deliver with the unresolved findings appended). Delivery is a write like any
other: one user confirmation, then save to `briefs/<YYYY-MM-DD>-<view>.md`.
Briefs are dated, disposable views — never a source of truth; comparing
same-view briefs across dates shows how the system's understanding evolved.

Sentence provenance tags, mandatory in every brief:
- `[C:slug]` — a paper states it (claim with anchor in the cited card)
- `[S]` — system-level synthesis across cards
- `[H:transfer-slug]` — hypothesis pending validation (any transfer reference is [H:])

### Discover

Gate: ≥15 papers total AND ≥3 cross-domain papers (PALACE.md). palace-scout
searches across shared axes (pattern / function / failure-mode) → ≤5 candidate
transfer cards, each with ≥2 non-stopword bridges, explicit relation type, A–B and
B–C evidence, assumptions/risks, one first validation experiment, and a decision
suggestion. User selects → main agent writes `transfers/transfer-<slug>.md`.
`analogy_only` / `spurious_relation` candidates are reported and dropped, never
written.

### Style

palace-stylist proposes feature cards (7 dimensions) / dual-axis classification
(journal-<venue> × lang-<trait>) / convergence judgment / crystallized profile
draft → confirmation → main agent writes `styles/`. `liked_aspects` and
`user_note` come from the user, never guessed. Profiles follow the
article-review-loop `style_rules` contract: rules grouped D2 / D3 / Fix tone, each
with `Support n/N` and `Maturity (candidate|stable)`; stable at support ≥3 with no
open conflicts; support evolves only via ingest backflow.

### Govern

palace-auditor scans triggers (PALACE.md list) → proposals, each with an impact
analysis (= `grep -l` list of affected files) → confirmation → main agent edits
the configured Vault. Each confirmed decision is appended as a dated Governance
Decision (date, decision, rationale, affected objects, provenance) to the
Vault's append-only `governance/decisions.md`. Migration manifests and
append-only rationales provide private-data recovery evidence; Palace never
uses private Git history.

### Audit

Run palace-auditor over the whole vault or named cards: anchor verbatim checks,
orphan tags, source_type correctness, [C]/[S]/[H] boundary violations. Report only;
fixes go through the normal confirm-then-write path.

### Domain add

User names the domain and supplies (or delegates retrieval of) 1–2 review /
representative papers → extractor + linker propose the seed concept subtree —
REUSE shared axes first (map new tasks/methods onto existing pattern / function /
failure-mode / metric rows), add new abstract concepts only when genuinely missing
→ packaged confirmation → registry row in `domains.md` + concept rows written →
normal ingest for that domain. New domains automatically join discover's
cross-domain search space; brief views accept the optional domain argument.

### Init (bootstrap a topic corpus)

Turnkey initialization: topic → searched candidates → one circled selection →
batch ingest.

1. If the topic's domain is not in Vault `domains.md`, run Domain add first (1–2 reviews
   seed the concept subtree).
2. Corpus scouting (main agent): topic/title search via the Ingest metadata
   chain (OpenAlex first, Crossref / Semantic Scholar fallbacks),
   citation-sorted, plus reference mining from the topic's reviews → ~n
   candidates (default 50).
3. Mix policy (defaults, user-tunable): classics (>10 yr) ≥ 20%; reviews 2–4;
   every method generation ≥ 3 papers; frontier (≤ 3 yr) ≥ 25%.
4. ONE candidate table (title / year / venue / citations / track) → the user
   circles the selection once.
5. Batch ingest per the Ingest flow (5–10 per batch, one merged confirmation
   per batch; acceptance checks per batch: zero orphans, dedup, weight
   derivations persisted).

### Refresh (explicit metadata / citations / impact updates)

The only flow that may touch the network, and only when the user invokes it —
no automatic or scheduled refresh exists. `govern` reports stale data; it
never fetches.

1. Run the deterministic tool: `python3 -m knowledge_palace.metadata.refresh
   --kind <impact|citations|metadata> [--scope all|<slug>|domain:<slug>]
   [--live] [--jcr-snapshot <path>]`. Without `--live` the run is cache-only
   (Bibliographic Cache under `state_dir`); `--live` requires the Goal-level
   network authorization.
2. Snapshots land in `<state_dir>/impact/snapshots.json` (Derived State:
   dated observations, deletable, rebuildable). Multi-category bands are
   stored side by side with their Evaluation Context — never collapsed to a
   maximum; unknown stays unknown.
3. Card updates (e.g. `citations` + `citations_date`) come out as PROPOSAL
   reports; the orchestrator packages them into one confirmation and writes
   only after the user approves. Weight-band changes additionally require
   their own migration gate. Evidence quotes are never touched.
4. `--dryrun-weights` compares every card's persisted legacy `weight:`
   derivation against its contextual bands — a read-only report, zero Vault
   writes.

### Acquisition (unified material fetch → Source Snapshot transaction)

`acquire(MaterialRequest) → MaterialReceipt` with three independent axes:
`acquisition_status` / `identity_status` / `text_status`. Channel order:
user-supplied local file → Zotero (read-only) → Open Access → licensed API
(not in V1) → institutional (disabled experimental stub). Implementation:
`knowledge_palace/acquisition/` (receipt / providers / transaction).

1. Providers stage bytes under `<state_dir>/acquisition/` (Derived State,
   deletable); receipts are compact — raw logs and provider dumps never
   reach the orchestrator context.
2. Hard rules: identity `verified` only mechanically (expected-sha match,
   DOI in text head, or recorded user confirmation); `mismatch` quarantines;
   nothing is Claim-eligible unless identity is verified AND text is ready;
   partial failure never yields a half-written receipt.
3. Zotero is a formal but optional read-only entry: Local API first, Web
   API fallback; metadata/attachments only — never notes, annotations, or
   the live SQLite; stable keys only.
4. Promotion into the Source Cache happens ONLY inside the packaged user
   confirmation (real roots additionally behind the Goal-level source-write
   gate): immutable temp+rename copy to `fulltext/<slug>.<ext>` — identical
   hash is an idempotent no-op, a differing hash is a typed refusal.
   Rejecting the confirmation changes nothing: Vault and Source Cache stay
   byte-identical.
5. Full-text bytes never land under the Vault; cards store only the
   `source_dir`-relative `local:` pointer plus the recorded sha256.
6. `doctor` reports Source Cache health (missing pointers =
   `source_unavailable`, report-only — existing Claims keep working) and
   always reports the institutional provider as experimental.

### Expand (bounded A→B→C literature expansion)

`/palace expand <work-slug|doi|arxiv-id> [--scope <domain-or-topic>]
[--review auto|manual] [--depth 1|2] [--max-new N]` — defaults: review=auto,
depth=2, max-new=50. Implementation: `knowledge_palace/expansion/`
(candidates / run / engine / record).

1. `max-new` counts unique, non-Vault, identity-verified Candidate Works
   discovered this Run — not ingested texts. Reaching it stops querying;
   frontier exhaustion below the cap ends the Run early; continuing needs a
   new budget or a new Run. Stop reasons are recorded.
2. Frontier eligibility: only ingested Works, explicit user roots, and
   Vault Hits expand further; metadata-only Candidates never join the
   frontier; a boundary-depth C is recorded, never expanded in the same Run.
3. One Candidate per Work identity (doi > openalex > arxiv > title hash),
   however many paths found it — each path is a Discovery Occurrence.
   Vault Hits verify/record the edge and are never re-ingested.
4. Selection Decisions are Scope-bound (`selected|deferred|rejected` +
   reason; auto mode keeps ≤2 exploratory picks per batch and flows through
   the palace-expansion-reviewer task package; manual mode presents the
   same candidate package). A rejection never becomes a global blacklist.
5. Candidate pool, occurrences, and run checkpoints live under
   `<state_dir>/expansion/` (Derived State; interrupted runs resume without
   duplicates). The compact run record (template `expansion-run.md`) is
   written to the Vault only through the packaged confirmation; rejecting
   the final batch leaves Vault and Source Cache byte-identical.
6. Selected candidates proceed to acquisition (MaterialReceipts) and the
   normal Ingest confirmation; expansion itself never writes cards.

### Ask (coverage-driven grounded Q&A)

No-write computed view unless the user asks to save. Coverage — not Domain
— gates answering; modes: `vault` (default) | `hybrid` |
`external`, where hybrid/external are explicit user opt-ins recorded in the
session. Machinery: `knowledge_palace/interaction/` (session / coverage /
proposal / prefilter).

1. Decompose the question into subquestions; open an InteractionSession
   (Derived State, `state/interaction/<id>/`, resumable and deletable).
2. Deterministic prefilter (`interaction/prefilter.py` over the Graph
   Index payload, PALACE.md hub stopwords injected): ≤15 id-only candidate
   descriptors; cross-domain questions reach foreign material through
   typed corridors. The whole Vault never enters a prompt.
3. palace-analyst drills the candidates through the GraphQueryPort and
   returns a CoverageReport (`interaction/coverage.py` schema): verdict
   `sufficient` | `partial` | `insufficient` with per-subquestion
   covered/hole status and id-shaped evidence.
4. sufficient → answer, every sentence tagged [C]/[S]/[H], weights
   side-by-side. partial → answer ONLY the covered part; holes are listed
   explicitly, never papered over. insufficient → no Vault-grounded answer
   is fabricated; an ExpansionProposal (holes → seeds/queries, depth ≤2,
   budget ≤50) is presented instead.
5. ONE user confirmation on the proposal: accepted → it materializes as a
   bounded ExpansionRun (that flow's gates govern live traffic and any Vault
   write); rejected → nothing changes, the covered part stands. Either way
   the decision is recorded in the session.
6. After an expansion completes, the SAME session resumes: recompute the
   prefilter + coverage over the updated index — no whole-corpus re-read.
7. hybrid/external (opt-in only): temporary external sources are listed
   under External Sources, marked session-local, and can never auto-enter
   the Vault (schema-enforced `vault_eligible: false`).
8. Optional save: auditor pass → confirmation → `briefs/<date>-ask-<slug>.md`.

### Idea refine (critique and upgrade a user idea)

`brief ideas` creates ideas from gap × transfer; this flow refines one the
user brings. No-write computed view unless the user asks to save. Novelty
is profile-relative and vault-relative by default. Machinery:
`knowledge_palace/interaction/` (novelty / project_source, on the shared
session).

1. The user supplies the idea (inline text or a file path); the
   orchestrator opens (or resumes) an InteractionSession and confirms the
   Novelty Profile — which dimensions (theory, mechanism, method, data,
   evaluation, empirical-finding, system-integration,
   application-transfer, scale-generalization) novelty is even claimed on.
2. Author-supplied references resolve FIRST (`project_source.resolve`
   over graph identity): Vault Hit → the existing Work is reused, never a
   duplicate identity; miss → a verified session-local Project Source
   (`project_local: true`, `auto_ingest: false`, schema-enforced) usable
   in the assessment; formal ingestion later is a separate user-initiated
   ingest flow.
3. Coarse-to-fine bounded pipeline (`novelty.novelty_pipeline` over the
   Graph Index payload, deterministic, id-only, honest per-stage
   truncation counts): ≤10 novelty corridors → ≤15 closest works →
   ≤30 related claims. The whole Vault never enters a prompt.
4. palace-analyst returns an IdeaAssessment (`novelty.py` schema):
   supporting vs opposing vs unknown evidence side by side (weights
   shown), closest prior work (name duplicates among gap cards, transfer
   cards, prior ideas briefs), alternative hypotheses, falsifiers/kill
   criteria and a minimal validation experiment (both required); novelty
   verdicts only on profile dimensions, vault-relative; graph-synthesis
   "possible novelty" listed separately, never presented as literature
   fact.
5. External novelty check — offered, never run by default. On explicit
   user confirmation an ExternalNoveltyRequest is recorded (one hop,
   ≤20 candidates, scope + date); resulting statements are framed as
   "not found within the recorded search scope and date" — the validator
   requires every statement to carry the recorded scope and date, and
   rejects ALL external statements without the recorded opt-in; absolute
   global novelty is never the contract.
6. palace-scout, only when a cross-domain angle is plausible: transfer
   candidates that strengthen the idea.
7. palace-auditor: anchors + [C]/[S]/[H] boundary → confirmation →
   `briefs/<date>-idea-<slug>.md`.

### Draft intro (provenance-tagged introduction for any topic)

Input is a free-text topic (a research angle, a method × problem pairing, a
gap direction — a domain name is just a special case), plus optional focus
(gap/idea slug) and optional style profile (`styles/profiles/journal-<venue>`).

1. Topic scope verdict: reuse Ask steps 1–2. Fully OUT → do not draft; reply
   "not in the vault" + expansion advice. Partial → draft only the covered
   aspects and list uncovered aspects as coverage holes in the draft header.
2. Assembly is topic-sliced (never whole-domain): relevant concept subtrees,
   relevant gap cards (motivation), claims with anchors (citation pool), and
   ideas / refined-idea cards (contribution) when present.
3. palace-analyst drafts: field context → progress narrative by method
   generations → the specific gap (why unresolved, weighted evidence) → the
   contribution. EVERY sentence tagged [C:slug]/[S]/[H:slug]; citations listed
   as slugs + anchors; a supplied style profile's rules (D2/D3/Fix tone) bind
   phrasing.
4. palace-auditor: verbatim anchors, tag boundary, style-rule conformance when
   a profile was applied. FAIL → revise (max 2 loops, then deliver with
   findings appended).
5. Confirmation → `briefs/<date>-intro-<topic-slug>.md`. The draft is a
   provenance-tagged skeleton: the user rewrites prose freely; the tags say
   which sentences rest on which evidence.

### Write (project-based section-wise Paper workflow)

Staged, never one-shot full text. Machinery:
`knowledge_palace/workspace/` (project / material / brief / writing /
revision). The Workspace is a private root: Palace NEVER runs Git there,
and only user-confirmed content enters it — auto drafts and interim
reviews live only in Derived State (`state/workspace-drafts/`).

1. Project create/open: a confirmed Workspace write materializes
   `projects/<slug>/` (eight subdirectories + flat `project.yaml`;
   relative paths only, resolved against `workspace_dir`, CWD never
   consulted). The current revision is computed live from the revision
   files, never stored.
2. Inputs registered: ProjectMaterials (user drafts, data, figures,
   solicitations, reviewer comments — usable for writing, schema-barred
   from ever becoming Vault Claim evidence) and Project Sources
   (Vault-first resolution).
3. Project Brief frozen: problem, contribution, audience/venue/language/
   length/citation-style/style-profile, the section plan with
   dependencies, and the evidence package — id-shaped refs with verbatim
   quotes AND anchors. `freeze` fingerprints the brief (sha256 of
   canonical JSON); every writer package pins that fingerprint.
4. Per-section loop: a validated writer package (evidence and materials
   ⊆ the frozen brief — beyond-brief references are validation errors)
   goes to palace-writer; palace-reviewer reviews; palace-writer revises
   automatically at most TWICE; then palace-auditor (anchors, boundaries,
   fabrication). Unresolved findings are delivered to the user, never
   looped away. A Results-kind section without user-supplied materials
   must be placeholder-only (structure + analysis plan + marked
   placeholders) — results are never fabricated.
5. ONE packaged confirmation per save: accepted → the next
   `sections/<section>/rNNN.md` revision (append-only; prior revisions
   are immutable; the assembled full document is the reserved section
   name `assembled`). No-save → chat-only delivery, the Workspace stays
   byte-identical.
6. User-facing prose uses normal scholarly citation (APA default; CSL
   switching via the export step) — internal [C]/[S]/[H] tags never appear in user
   output.

#### Proposal variant

For `kind: proposal` projects the Write flow adds three deterministic
layers (`workspace/requirements.py`, `workspace/proposal.py`):

- **Requirements Matrix first**: the solicitation/funder text becomes
  anchored requirement rows (a modal-marker line extractor prefilters;
  the LLM refines; the schema judges — every row carries id + text +
  source anchor). Coverage is tracked section → requirement ids and
  every uncovered requirement is NAMED in the delivery, never
  summarized. Without a solicitation the generic research-proposal
  profile applies and is BORN `compliance_verifiable: false` with a
  degradation note — the flag is schema-enforced and appears in the
  delivery.
- **Aims/approach alignment**: every specific aim must map to at least
  one approach element; orphan aims and unmapped approach elements are
  named review findings.
- **User facts**: budget figures, institutional facts, and preliminary
  results validate ONLY when the package carries registered
  ProjectMaterial ids — user facts never come from the model
  (preliminary-results sections additionally sit under the
  Results guard).

#### Export step

Markdown stays the canonical source; exports are replayable plans
(`workspace/export.py`): CSL resolution (explicit override > project
manifest `citation_style` > APA), project-relative source/output paths,
and the exact pandoc argument list built as data. Outputs land under
`exports/` with deterministic collision-free naming; nothing is ever
overwritten and the source revision is untouched by construction. ONE
confirmation shows the plan; the run executes exactly the plan the user
saw (pandoc is an external tool — if it is absent the orchestrator
reports that instead of improvising). Exports are never an editing
source and never re-enter revisions.

### Viewer export (local, offline, read-only graph browsing)

No LLM in this flow — a deterministic build step, the same class as
`doctor` or `refresh`. Machinery: `knowledge_palace/viewer/` (export /
html_template / cli). Excludes Proposal/Requirements-Matrix rendering,
CSL/DOCX/LaTeX (that is `write`'s export step) — this exports the Vault
*graph*, not a project document.

1. Resolve the four roots; the export walks ONLY the frozen
   GraphQueryPort's five operations (`list_hierarchies`, `list_levels`,
   `query_level`, `query_context`, `get_content`) — never a raw Vault
   scan, never Source Cache. A stale index aborts the export with no
   output file written.
2. Confirm the output path with the user (default
   `./palace-viewer.html`); the orchestrator flags if it would
   overwrite an existing file. The path must be outside all four
   private roots — this write is the user's explicit choice, never an
   implicit Vault/Source/Workspace write.
3. ONE confirmation, then the export runs and writes exactly one
   self-contained HTML file via temp+rename (a failed export never
   leaves a partial file; prior good exports are never corrupted).
4. The emitted page is entirely offline: one embedded JSON payload,
   hand-rolled CSS/JS, zero external requests, zero new dependency. It
   renders the domain → concept → work/gap hierarchy as a browsable
   tree plus a per-node detail pane (parents/children/edges/content);
   `children`/`edges` are single-page by the frozen port contract
   itself (no further pagination offered) — the page shows
   `returned`/`total` honestly rather than implying completeness.
5. Nodes with no parent and no edges (e.g. Briefs — a documented
   non-evidence view role) are not graph-reachable and do not appear;
   this is inherited from the frozen contract, not a Viewer defect.
