> Current task routes: [Commands](knowledge_palace/protocol/COMMANDS.md). Selected literature is ingested; reading updates its card. `write` and `polish` share manuscript analysis; `feasibility` assesses a design. Direct manuscript tasks need no new project.

# KnowledgePalace Tutorial

English | [中文](TUTORIAL.zh-CN.md)

Hands-on walkthroughs from an empty setup to writing a paper section. Each
tutorial shows what you type, what Palace does, what you confirm, and where
files land. Concepts and rules are in [GUIDE.md](GUIDE.md); this file is
purely practical.

Conventions used below:

- `$` — a shell command you run yourself.
- `>` — something you type to the agent (Claude Code or Codex) in the
  Framework root. `/palace …` commands and natural-language equivalents
  both work.
  In Codex write `$palace …` instead of `/palace …`.
- **Confirm** — Palace never writes to your data without showing you a
  packaged confirmation first. Answering "no" always leaves everything
  byte-identical.

---

## Tutorial 0 — Setup (5 minutes)

Requirements: Python ≥ 3.9 (nothing to pip-install) and Claude Code or Codex.

```bash
$ git clone <this-repo> KnowledgePalace
$ cd KnowledgePalace

# The four private roots must exist, be distinct, and live OUTSIDE the repo.
$ mkdir -p ../KnowledgePalace-vault ../KnowledgePalace-state \
           ../KnowledgePalace-sources ../KnowledgePalace-workspace

$ cp .palace.example.toml .palace.toml
```

`.palace.toml` is git-ignored and local to you. Its paths resolve relative
to the file itself, so the defaults match the `mkdir` above:

```toml
vault_dir = "../KnowledgePalace-vault"
state_dir = "../KnowledgePalace-state"
source_dir = "../KnowledgePalace-sources"
workspace_dir = "../KnowledgePalace-workspace"
```

Verify the config (read-only, zero writes, zero network):

```bash
$ python3 -m knowledge_palace.tools.config_resolver
```

You want all four roots printed as absolute paths; a config error names the
offending line or the missing/duplicated directory.

Optional but recommended: make the private roots (except sources) one Git
repository of your own — that is entirely your business; Palace never runs
Git there.

---

## Tutorial 1 — Bootstrap a corpus with `init`

The fastest way to a useful vault: pick a topic, let Palace search, circle
once, batch-ingest.

```
> /palace init diffusion-model-interpretability 30
```

What happens:

1. **Domain check.** If the topic's domain is not registered yet, Palace
   first runs the domain-add flow: it asks you for (or retrieves) 1–2
   review papers, proposes a seed concept subtree (reusing the shared
   pattern/function/failure-mode/metric axes first), and you confirm one
   package → `domains.md` row + concept rows are written.
2. **Corpus scouting.** Palace searches by topic through the available
   providers or browsing tools and mines the reviews' references. Citation
   and venue data are shown as context, never as a quality score; queries,
   dates and selection reasons are recorded.
3. **One candidate table** (~30 rows: title / year / venue / citations /
   why it was found). You circle your selection **once** — this is the only
   selection pass; Palace never asks you to reselect the same papers.
4. **Ingest every selected paper** (see Tutorial 2). Papers already in the
   vault are reused, never duplicated.

Afterwards:

```
> /palace status
```

expect paper counts, gap counts, concept counts per axis, and a clean
consistency block (INDEX rows == card files, zero orphan tags).

---

## Tutorial 2 — Ingest one paper and read the result

```
> /palace ingest 10.48550/arXiv.2301.00001
```

or with a local PDF (papers Palace cannot download get asked for a local
path anyway):

```
> /palace ingest ~/Downloads/smith-2023.pdf
```

The flow you will see:

1. **Identity** — DOI, arXiv id and title are matched against the vault. A
   hit reuses the existing card and deepens it; existing quotes and anchors
   are never touched. A preprint/published pair is verified before merging.
2. **Material** — the best available source (local file, Zotero, open access,
   or a browsing/PDF tool) goes into the Source Cache. The card records
   `source_coverage` (what you hold) and `read_depth` (what was read); a PDF
   on disk is not a reading.
3. **Reading** — to your question and the requested depth: the author's
   question, method, principal findings and boundaries; load-bearing Claims
   related to the analysis or figure that supports them.
4. **The card draft** — verbatim Claims with anchors, Argument and Conditions
   rows, an optional `## Analysis evidence` table, dated `## Reading notes`,
   concept tags and gap relations aligned against the registry.
5. **Save** through `save_paper`: it refuses a duplicate identity, keeps every
   old Claim, checks depth against coverage and updates the INDEX row. After
   the batch the index is rebuilt once and affected judgments are listed
   (`/palace updates`).

Now look at what was written:

```bash
$ ls ../KnowledgePalace-vault/papers/
$ cat ../KnowledgePalace-vault/papers/smith-2023-emergent.md
```

Anatomy of a paper card, the parts worth knowing:

```markdown
---
title: ...
authors: [Smith, J., ...]
year: 2023
citations: 42
citations_date: 2026-07-17
weight: medium (IF 4.2 in 3–10)        # bibliographic context, not a score
read_depth: full                       # full | skim | abstract | metadata
source_coverage: full-text             # full-text | excerpt | abstract | metadata
domain: [diffusion-models]             # always includes the domain root
method: [classifier-free-guidance]
gaps:
  - gap-guidance-fidelity: supports
local: fulltext/smith-2023-emergent.pdf   # source_dir-relative pointer
---
## Summary
(may be in Chinese)

## Claims
- C1 [classifier-free-guidance]: "exact verbatim sentence from the paper"
  — §4.2 [¶3] / p.6
```

Every claim: a verbatim quote, an anchor, and at least one concept binding.
If a fact has no anchor, it is not in the vault. An abstract-only paper gets a
card whose Claims are abstract quotes and whose Limitations say so; a
metadata-only record gets a card with no Claims at all.

---

## Tutorial 3 — Ask questions

```
> /palace ask does classifier-free guidance hurt sample diversity?
```

Palace decides what the question needs — a background explanation, paper
evidence, a cross-paper comparison, a tentative explanation — and answers in
plain prose with source links:

- Sentences a paper supports cite the card (`[C:smith-2023-emergent]`; go read
  the anchor). Minority evidence sits next to majority evidence.
- Synthesis and hypotheses are labeled as such and name what they rest on; a
  hypothesis does not need a Transfer card, and a concept explanation does not
  need a Claim.
- What the library does not cover is stated ("no vault evidence on diversity
  metrics beyond FID") rather than fabricated — and does not block a clearly
  labeled explanation.

When more literature would change the answer, Palace offers to collect it. Say
yes and it runs `init`/`expand` (Tutorial 4), ingests the papers you select, and
**continues the same question** with the new Claims.

Answers are chat-only by default. Say "keep this" and the working definitions,
decisions, alternatives and next step go into the project's `research.md`
(Tutorial 7c); say "save it" for a dated brief in `briefs/`.

---

## Tutorial 4 — Grow the corpus with bounded expansion

From any ingested paper:

```
> /palace expand smith-2023-emergent --scope diffusion-models --depth 2 --max-new 30
```

- The engine traverses citations A→B→C, at most depth 2, stopping at 30
  unique verified non-vault candidates (or earlier if the frontier runs
  dry). Works already in your vault are recognized as Vault Hits — their
  edges are recorded, they are never re-ingested.
- Each candidate gets a scope-bound decision — `selected / deferred /
  rejected` + reason — from palace-expansion-reviewer (add
  `--review manual` to decide yourself). Rejections are scoped, never a
  global blacklist: the same paper can be selected for another scope later.
- Interrupted runs resume from checkpoints under `state/expansion/`
  without duplicates.
- You confirm the compact run record; selected candidates then flow into
  the normal ingest confirmation of Tutorial 2. Expansion itself never
  writes cards.

---

## Tutorial 5 — Briefs and cross-domain discovery

Once you have ~10+ papers:

```
> /palace brief onboard                 # domain map + 5–8 paper reading path
> /palace brief gaps                    # ranked open problems, who tried, why unresolved
> /palace brief map classifier-free-guidance   # one concept's method timeline + disputes
> /palace brief ideas                   # gap × transfer opportunity cards
> /palace brief progress guidance-schedule   # question evolution, advances, remaining evidence
```

Every brief is drafted from the bounded research context (`progress <topic>`
adds question evolution and remaining subquestions). Ask for an audit pass when
you want an independent check of anchors and source boundaries. You confirm the
save to `briefs/<YYYY-MM-DD>-<view>.md`. Briefs are dated, disposable views: re-run
`brief gaps` in a month and diff the two files to watch your field's
picture evolve.

Cross-domain discovery unlocks at ≥15 papers total and ≥3 cross-domain
papers (register the second domain via `/palace domain add` *before*
ingesting its papers):

```
> /palace discover gap-guidance-fidelity
```

palace-scout returns ≤5 candidate transfer cards, each with ≥2
**non-stopword** bridges (generic terms like "deep-learning" never count),
a typed relation, evidence on both sides, and one concrete first validation
experiment. You select which ones become `transfers/transfer-<slug>.md`.

---

## Tutorial 6 — Refine your own idea

```
> /palace idea refine "Adapting guidance-schedule annealing from
  text-to-image diffusion to protein structure generation could reduce
  mode collapse without retraining."
```

(or `/palace idea refine ideas/my-idea.md` for a file.)

1. Palace confirms your **Novelty Profile** — which dimensions you claim
   novelty on (mechanism? method? application transfer? …). Verdicts are
   only ever issued on those dimensions.
2. If you supply references, they resolve Vault-first: known Works are
   reused; unknown ones become temporary project sources. Adopt one and it
   is ingested through the normal path (Tutorial 2), then cited by its card.
3. A deterministic coarse-to-fine pipeline narrows context: ≤10 corridors →
   ≤15 closest works → ≤30 related claims.
4. You get an **IdeaAssessment**: supporting vs opposing vs unknown
   evidence side by side with weights, the closest prior work by name,
   alternative hypotheses, and — always — falsifiers and a minimal
   validation experiment.
5. Novelty is **vault-relative** by default. An external novelty check is
   offered but only runs on your explicit opt-in, and its findings are
   framed as "not found within the recorded search scope and date" — never
   as absolute novelty.

Save lands in `briefs/<date>-idea-<slug>.md` after audit + confirmation.

---

## Tutorial 7 — Write a paper section

```
> /palace write guidance-anneal-paper
```

First run creates the Workspace project (one confirmation):
`workspace/projects/guidance-anneal-paper/` with `project.yaml` (kind,
audience, venue, language, length, citation style, style profile) and its
subdirectories. Direct text needs none of this — `/palace write` and
`/palace polish` also accept a pasted passage or a file.

Then, in order:

1. **Register inputs.** Your drafts, figures, data, and reviewer comments
   become ProjectMaterials; your reference list resolves Vault-first into
   Project Sources, and any paper you adopt from outside is ingested.
   Materials feed writing but can never become Vault evidence.
2. **Manuscript analysis.** Before touching prose Palace records, in
   `outline/manuscript-analysis.md`: the research question, central claim and
   evidence, the whole-paper argument and section roles, target reader, your
   writing intent, canonical terms and unresolved inputs. It is reused on
   later tasks while it still matches the manuscript, and updated after a
   substantive change — never redone just because you asked for another
   polish.
3. **Draft a section:**

   ```
   > /palace write guidance-anneal-paper introduction
   ```

   The argument and paragraph roles come first; the draft is built from the
   selected evidence and your materials; one focused review follows, with at
   most two automatic revisions. Unresolved findings are shown to you, never
   looped away. A Results-kind section without your registered data comes
   back placeholder-only — results are never invented. `draft intro <topic>`
   is the same route for an introduction.
4. **Confirm the save** → `sections/introduction/r001.md`. Revisions are
   append-only; the next save is `r002.md`, and `assembled` is the reserved
   section name for the stitched full document. Declining the save keeps
   the delivery chat-only and the Workspace byte-identical.
5. **Polish a passage:**

   ```
   > /palace polish guidance-anneal-paper introduction "The gap has a second component ..."
   ```

   Palace reads the analysis and the surrounding text, decides whether the
   problem is wording, paragraph logic or the scientific claim, revises only
   that passage, and checks numbers, units, terms, citations, claim strength
   and boundary conditions against the original. Everything else in the
   section stays byte-identical; the result is `r002.md`. A scientific
   problem is reported, not polished into apparent certainty; a substantial
   restructuring is handed to `write`.

Grant proposals (`kind: proposal`) follow the same route: register the
solicitation as a material and its requirements become part of the analysis;
budget, institutional and preliminary-result statements come only from your
registered materials.

---

## Tutorial 7b — Judge a design's feasibility

```
> /palace feasibility "Compare SRH computed from forecast-available HRRR
  profiles against SRH from observed storm motions, using our event packages."
```

(or a file, or a project whose research notes hold the plan.)

Palace reads the proposal, your registered materials and the relevant Claims,
then reasons about the decisive issues: what explanations the design
distinguishes; whether variables, sampling scale and independent units match;
whether the controls can separate the alternatives; and whether the data,
access, computation, storage, skills and time actually exist. You get one of
可执行 / 满足明确条件后可执行 / 需调整方案 / 目前无法判断, the decisive
conditions, the smallest useful pilot with its possible outcomes, and what
would change the decision. Resources are estimated only from what you supplied
— a method being available in a paper says nothing about your data. Say "keep
this" and the judgment lands in the project's `research.md`; the experiment
itself is never run for you.

---

## Tutorial 7c — Research notes and evidence reviews

```
> /palace research guidance-anneal-paper
```

shows the project's `research.md`: learning goals, working definitions,
Synthesis rows that declare which Claims and Gaps they depend on, decisions,
constraints and Observations that point to your registered materials. Any
discussion, feasibility judgment or reading you ask to keep is appended here,
so "continue where we left off on the sampling design" recovers the actual
choices and their grounds.

After new papers are ingested the index is rebuilt and every judgment whose
declared evidence changed becomes a pending review:

```
> /palace updates
> /palace updates resolve gap:guidance-fidelity S1
```

Review the evidence, edit the synthesis if needed, and record `retain`,
`revise` or `withdraw` with a reason. Recording a decision never edits
scientific text by itself; later evidence changes reopen the item.

---

## Tutorial 8 — Browse your graph offline

```
> /palace viewer export
```

Confirm the output path (default `./palace-viewer.html`; it must be outside
the four private roots, and Palace flags any overwrite). The build is
deterministic — no LLM — and walks the frozen GraphQueryPort only. Open the
file in any browser, fully offline: the domain → concept → work/gap
hierarchy as a browsable tree with a per-node detail pane. Truncation is
reported honestly (`returned`/`total`); the page makes zero network calls.

For an Obsidian vault, `/palace wiki export [<dir>]` regenerates only the
marked hub pages; your own notes and the original cards stay untouched.

If the export aborts with a stale index, rebuild first:

```bash
$ python3 -m knowledge_palace.graph.builder --rebuild
```

---

## Tutorial 9 — Maintenance cadence

Roughly every ~20 ingested papers (or when Palace mentions a trigger):

```
> /palace govern
```

You get proposals, each with a grep-computed impact list: candidate
concepts ready for promotion (≥3 genuine-use supporters with evidence from
distinct data or analyses), provisional
bibliographic bands due for explicit refresh,
recurring unregistered terms, orphan tags, deprecated-slug migrations.
Confirmed edits are applied and logged as dated Governance Decisions in the
Vault's append-only `governance/decisions.md`. `govern` never touches the
network — refreshing citations is a separate, explicit step:

```
> /palace refresh citations all        # cache-only preview
> /palace refresh citations all --live # real fetches, on your say-so
```

Occasionally, or before trusting a big brief:

```
> /palace audit                        # whole vault
> /palace audit smith-2023-emergent    # or specific cards
```

The auditor adversarially re-verifies anchors verbatim, hunts orphan tags,
and checks provenance boundaries. It only reports; any fix goes through the
normal confirm-then-write path.

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `config_resolver` reports an unresolvable root | the four paths in `.palace.toml` resolve relative to that file — check them from the Framework root, not your shell CWD |
| Ingest says the paper already exists | that's the dedup gate — choose skip, deepen (add claims), or correct (append marked corrections); it never overwrites |
| Ask says the library has no evidence on part of the question | that part is answered as labeled background or hypothesis; let Palace collect literature, or narrow the question |
| `save_paper` refuses a card | read the listed reasons: a duplicate identity (reuse the named slug), a changed old quote (append a correction instead), or a reading depth that outruns the material |
| A count looks wrong in `status` | counts are computed live from files — inspect the vault directly; INDEX↔file mismatches are listed in the consistency block |
| Want your vault in Git | do it yourself in the private roots; Palace will neither help nor interfere — that boundary is by design |
