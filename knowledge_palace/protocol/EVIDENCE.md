# Argument, conditions and current synthesis

Markdown cards remain authoritative. Optional tables extend existing cards;
absence means not yet curated. Existing Work and Claim IDs and quotes remain
unchanged. Append a new Claim and a correction note when this work's evidence was
read wrongly. When the wording or its source is in doubt, verify against the
cached source before anything else: repair the quote in place when the recorded
wording drifted from the source, correct the anchor if the quote sits elsewhere
in this work, and retract the Claim if the quote is not this work's at all. Only
a misreading appends a note; a transcription repair does not. A retracted Claim
keeps its text but stops being evidence, so no table row below may cite it.

## Paper tables

`## Argument` uses `Role | Claim | Paraphrase | Attribution | Scope`.
Role is `problem`, `advance` or `remaining`; Claim is a local `C<n>`.
Quote and original location live in that Claim, normalized wording in Paraphrase.
Attribution is `author` or `system`. Do not fill missing author statements by
inference. A system interpretation never becomes an author's historical claim.

`## Conditions` uses `Dimension | Value | Evidence` (one local C-number per row).
Use dimensions relevant to the study: population, setting, sampling, scale, data,
design, comparator, outcome, assumptions and data/method dependence. Values and
dimension names are domain knowledge; code contains no discipline-specific list.
Extract an anchored Claim for a condition that lacks an existing evidence ref.

`## Evidence relations` uses
`Claim | Relation | Target | Attribution | Comparison | Scope | Rationale`.
The source is a local C-number and Target is `gap:<slug>` or
`claim:<paper-slug>#C<n>`. Relations are `identifies`, `supports`,
`partially_addresses`, `disputes`, `reframes`, `same_question`, `overlaps`,
`broader_than`, `narrower_than`, `different_question`. Direction is source to
target (e.g. `broader_than` means the source question contains the target).
Comparison is `direct_response` only when an anchored author passage explicitly
responds to the cited work/question; otherwise use `retrospective` and `system`.
Scope states relevant conditions and subquestions; Rationale explains the link.
Use one row per source/relation/target, joining relevant scopes in that row.
Keep the legacy paper `gaps:` summary for existing consumers.

Tables have one physical line per row. Escape a literal pipe as `\|`.
Omit uncurated rows; empty cells are errors. Parsed new relations must resolve
before authoritative writes. Legacy sections remain readable.

## Gap and brief synthesis

`## Synthesis` uses `ID | Statement | Claims | Gaps | Rationale`.
IDs distinguish judgments within a card. Claims and Gaps contain comma-separated
qualified references (`claim:paper#C1`, `gap:gap-slug`); `-` means none.
These are current system judgments, never original evidence. Each judgment names
the subquestion advanced and the conditions still uncovered; status rationale is
append-only. The underlying historical author assertions stay unchanged.

### Generalization height and gap closure

These two rules bind every synthesis, gap status, brief, answer and draft.

The evidence held sets how high a statement may generalize, and the statement
names that evidence at the point it generalizes. One paper supports only its own
conclusion, stated with its conditions (which model, region, scale). Several
mutually independent sources may support "a class of models" or "a general
mechanism", each source named. Only the Vault's current holdings, named, support
"where this field/library now stands". Never turn one paper into a class-level
conclusion. Never let a noun phrase stand in for a conclusion ("the
storm-resolving comparison"): state what was done and found, so that a reader
can reconstruct it.

Literature touching a question does not close it. Judge by how much the sources
substantively answer and what they leave, never by whether or how many papers
exist. A question stays open through unresolved disagreement, an unverified
mechanism or an untested condition. A purely technical increment (finer grid,
more data, faster scheme) is not a remaining question and is no reason to keep a
Gap open or to propose further work.

Silence does not keep a question open either. A Gap whose newest evidence is old
and that carries no addressing relation records that nothing here looked again,
not that the field left the question unanswered; say which of the two it is. Such
a Gap does read as field attention — a quiet area is either an opening others
missed or one they left for a reason worth finding — and that reading belongs
beside the coverage fact in the Gap's synthesis, never as a scientific verdict.
Bibliographic bands carry the same kind of information under the same limit; see
PALACE.md.

The graph stores these rows on Gap/Brief/Transfer attributes. `depends_on` edges point to
Claims and Gaps. Briefs remain `role=view`, `evidence_capable=false`; they cannot
emit evidence-bearing edges. Rebuilding the index compares prior evidence and
new relations, writing `graph-index/synthesis-updates.json` in Derived State.
Suggestions name affected entries, dependencies and reasons to strengthen,
narrow, question or retain a judgment; they require evidence review, never
automatic promotion into facts. A removed relation also triggers review.
Each Gap synthesis also tracks new evidence targeting its owning Gap; affected
Gap judgments propagate review suggestions to dependent syntheses. Transfers
also track their declared papers and gaps. With the configured workspace,
maintenance locates affected current project briefs, sections with declared
`evidence` refs and decisions in `projects/<slug>/research.md`.

The update file is persistent workflow state. Entries have `pending`, `resolved`
or `unchanged` status, evidence-change events and dated review decisions.
Unrelated builds preserve pending entries; new relevant evidence reopens a
resolved entry. Preserve this file when clearing rebuildable index snapshots.
Use `research updates` to inspect the queue and `research resolve <node-id>
--entry <id> --decision retain|revise|withdraw --note "<rationale>"` after the
scientific review and any approved card edits are complete. Resolving a queue
entry records that action; it does not edit a scientific judgment.

## Retrieval and use

Before ask, brief, linker retrieval or viewer/wiki export, call
`graph.builder.ensure_index(vault, state, workspace)`. This maintains only Derived State.
The read-only GraphQueryPort serves the maintained snapshot. `ensure_index`
rebuilds changed Vault content or index formats before constructing it.
After approved ingestion/revision call `write_index(vault, state, workspace)`, read its
synthesis update report, and include proposed judgment changes in the ingest
result. Do not silently rewrite approved synthesis from a change detector.

`python -m knowledge_palace.interaction.research progress "<topic>"` implements
the evidence view for `/palace brief progress <topic>`. `ask`, `gaps` and `ideas`
produce the same structured research context for the analyst. `--alternative`
allows at most two explicit query reformulations; all supplied reformulations
are searched even when the first match pool is full. The combined reading set
is capped at 15 cards, including current briefs. Selection uses the latest
synthesis per topic/view, a representative from each query, interleaved Claim
dependencies and remaining query matches. A matched Gap also supplies source
papers. `--json` exposes candidate locators, full anchored Claims, argument
roles, conditions and evidence relations. Read candidate cards via the port;
for decisive or ambiguous evidence, read the card's `local` Source Cache file
around its cited section/page before judging. Registry Aliases handle Chinese,
acronyms and named concepts. Match-pool counts precede reading selection and
are not coverage verdicts. Unread dependencies are explicit. A retrieval
failure is a coverage result.

Only selected cards supply full content. Other related Gaps are locators in
`related_gaps`; their content is not added outside the reading budget. Conditions
and Argument changes count as applicability changes for the owning work's Claims,
including when the paper has no explicit Evidence relation edge.

Current synthesis remains a view: retrieve its underlying Claims before using
its conclusion. `cross_domain` lists up to three additional source locators
through selected works' shared functions, patterns or failure modes, including
when the initial question names only one domain. These are reading proposals,
outside the consumed evidence set; apply PALACE hub exclusions and compare
assumptions before asserting a transfer. Prior proposals are not evidence.

`--project <slug>` adds the existing project brief, research notes, materials,
observation feedback and explicitly selected style profiles. Use the project
research template for background, prerequisites, completed reading, next steps,
research decisions and experimental observations. Observations cite declared
project materials and a local decision; outcomes are supports/questions/
inconclusive. They prompt review of that decision and its dependencies without
becoming literature Claims. Style references are semicolon-separated absolute
profile paths or Vault `styles/profiles` names; external profiles are read in
place. Supply the selected journal/language pair, preserving user preferences.

Progress shows problem evolution, advances, disputes, remaining questions and
coverage. For gaps/ideas, separately state importance, Vault coverage and dated
external search scope/results. An opportunity must name the evidence chain,
inference step, competing explanations and a discriminating validation design.
No new scientific gap follows solely from few hits or a study's own omission.
