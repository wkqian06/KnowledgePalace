# Answer and discuss

`ask` handles explanation, comparison and multi-turn scientific discussion.
Start with the user's question, definitions, prior choices and supplied materials.
Use `research` to recover project decisions when a project is named. Brief views
summarize a chosen body of knowledge; they are not additional chat modes.

Choose what the question actually needs: background explanation, paper evidence,
cross-paper comparison, a tentative explanation or a research decision. Do not
require a Gap or bridge card before discussing a hypothesis. Internally distinguish
source-backed statements, background explanation, system inference/hypothesis and
user observations. Use normal readable prose and source links in the answer.

For library questions, run
`python -m knowledge_palace.interaction.research ask "<topic>"` with the topic as
English key terms (add `--project <slug>` for project context and up to two
`--alternative` reformulations). It returns a bounded reading plan: the candidate
cards with their paths, a few verbatim Claims per work chosen for the query, gap
statements with their current syntheses, Claim-to-gap relations, and the pending
updates that touch them. Each work quotes only some of its `claims_total` Claims:
before relying on a work beyond those quotes, read its card at `<vault>/<path>`
(`## Claims`); `--full` prints the complete context. Important unread dependencies need
a further bounded reading set. Coverage records describe only the literature-backed
portion; they do not prohibit background explanation or require an expansion proposal
for every unknown. Explain the limits of unverified or disputed claims.

When evidence is needed and the request authorizes collection, call init/expand
and [ingest](ingest.md) for adopted papers, then continue the same question.
Unselected search hits are not evidence. New library Claims replace temporary
source references in the completed answer.

Compare definitions, study conditions, measured outcomes and alternative
explanations before calling results contradictory. Give a useful next question
when the evidence cannot discriminate. Do not require every inference to combine
two papers or every hypothesis to point to a bridge card.

The result's `bridges.candidates` lists at most three papers from other domains
that share a pattern, function or failure mode with the reading set; each row
carries the Claim on each side that binds the shared concept. Read both Claims.
When the shared mechanism bears on the question, raise the connection in one or
two sentences as a hypothesis, say what would have to hold in the user's setting
for it to carry over, and link both papers. When it does not bear on the
question, leave it out; an empty list is a normal result. `bridges.cards` lists
saved bridge cards that touch the reading set; read a card before relying on its
hypothesis. Offer to save a new bridge card only when a connection holds up in the
discussion and the user wants to keep it; `discover` develops it further.

On a request to retain the discussion, update the existing project research notes
with the question, working definitions, accepted/tentative decisions, alternatives,
constraints and next action. Declare literature dependencies on judgments where
available. Preserve user observations as user materials. A chat without a save
request does not create an authoritative project or decision.

## Brief views, discovery and idea refinement

A brief synthesizes selected library evidence; map explains a concept and progress
tracks a research question. Neither requires a numeric score or a fixed paper
quota. Read `knowledge_palace/protocol/EVIDENCE.md` for syntheses, relations and the
gaps/ideas coverage rule (importance, Vault coverage and dated external search
scope/results stated separately).

A brief is a view: it adds no new knowledge, Gap or bridge card, only what the
cards support, and states missing coverage as missing without inferring a gap in
the field. Gather its context with `research ask` (`progress` and `bridges` have
views of their own, COMMANDS.md) and work from the cards and INDEX rows the
result names; when they are not enough, read a further bounded set rather than
the whole Vault. Compare study design, directness, conditions and data or method
dependence, show counterevidence beside support, and treat venue metrics,
citation counts and publication type as background. A paper under two years old
is cited with the note "(recent, citations immature)". Write every decisive
statement so that it can be checked against its source. The draft for
`briefs/<date>-<view>.md` opens with a header naming the view, date, domain scope
and card counts consumed.

- `onboard`: a domain map from the concept tree, the high-frequency core
  vocabulary and a 5–8 paper reading path across distinct subtrees, each pick
  justified. For a project, use its research notes' background, prerequisites
  and completed reading; each next reading answers a recorded open question. Ask
  for missing background instead of inferring proficiency.
- `map <concept>`: a chronological timeline of method generations, established
  conclusions with Claim references and weights, disputes side by side, and the
  status of the Gaps under the concept.
- `progress <topic>`: question evolution, claimed advances, disputes, remaining
  subquestions and coverage, keeping author/system attribution, conditions and
  Claim locators. Start from `current_syntheses` and inspect `pending_updates`.
  Unread dependencies and `related_gaps` are locators, not consumed evidence;
  read a further bounded set when they are decisive. Record each current
  judgment's Claim and Gap dependencies in the Synthesis table, and revise a
  judgment when new evidence changes its scope.
- `gaps`: open and disputed Gaps ordered by importance and evidence coverage; per
  Gap, who tried, why it is still unresolved, the remaining uncertainty and the
  open subquestions.
- `ideas`: opportunity cards, each with its importance, evidence, explicit
  inference steps, alternatives, hypothesis, tagged grounds, assumptions, risks,
  a minimal discriminating validation experiment with a one-line feasibility note
  derived from the cards' code, data and compute fields, and a possible paper
  contribution. Code-usage snapshots are display context, never a ranking input.
  When project decisions and observations are supplied, keep user observations
  apart from literature Claims and say how each changes a decision and its cited
  Gap, with its material source and interpretation.
- `bridges`: bridge cards by status with one-line hypotheses, the shared-concept
  corridors and bridge-card edges between the pair, and cross-domain `related:`
  Gap links, all from `research bridges`; without arguments, the domain-pair
  connection matrix.

An important brief can go to palace-auditor for an independent check, with the
draft and the absolute paths of the cards it cites, their cached source texts,
`PALACE.md`, `knowledge_palace/protocol/EVIDENCE.md`, `concepts.md` and the Vault
root. A brief is saved as `briefs/<date>-<view>.md` only after the packaged
confirmation; prepare the index afterwards.

`discover` looks for indirect connections: a capability in another domain
(`from`) linked to a home-domain Gap or task (`to`) through shared concepts
(`via`) on the pattern, function and failure-mode axes. A real bridge maps
relational structure, not surface keywords. It runs only past the discover gate
in PALACE.md. Start from the target Gap or task, or sweep the open Gaps, and read
the shared-axis sections of `concepts.md` and a prefiltered set of cards:
home-domain papers and Gaps, and cross-domain papers with Bridge notes. Each
candidate needs at least two distinct canonical shared-axis `via` concepts, none
of them a PALACE.md hub stopword, and an anchored quote from an in-vault paper
card (or its Bridge notes; older cards call them Transfer notes) on each side: no
evidence, no candidate. Its relation is one of the types in
`knowledge_palace/templates/bridge-card.md`; `analogy_only` and
`spurious_relation` findings are reported with their reason and dropped. Return
at most five candidates, ranked, each with one concrete first validation
experiment (data, method, metric, success criterion) and drafted from the
bridge-card template with status `candidate` or `monitor`. A candidate becomes a
bridge card only when the user selects it. Report missing foreign-domain
coverage and `via` concepts that need more papers.

`idea refine` starts from `research novelty "<idea text>"`, which gives the
bounded corridors, the closest works and their related Claims. Set supporting and
opposing Claims side by side with their weights and draft an IdeaAssessment as
specified in `knowledge_palace/interaction/novelty.py`: evidence references are
ids (or `project-source:` for author-supplied references); novelty verdicts cover
only the dimensions the user's Novelty Profile selects and are relative to the
Vault by default; possible novelty from graph synthesis is listed separately,
never as literature fact; falsifiers and a minimal validation experiment are
always given; duplicates among existing Gap cards, bridge cards and earlier idea
briefs are named. Check the JSON with `research assess --file <assessment.json>`
and fix every reported error before presenting it. The user confirms the Novelty
Profile; external novelty wording needs the user's recorded opt-in scope and date.
