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

Verify everything (read-only, zero writes, zero network):

```bash
$ python3 -m knowledge_palace.tools.doctor
```

You want every root reported resolvable and distinct, and both runtimes'
contracts complete. An "index: absent (rebuildable)" line is normal before
your first ingest.

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
2. **Corpus scouting.** Palace searches by topic via OpenAlex (Crossref /
   Semantic Scholar fallbacks), mines the reviews' references, and applies
   the default mix policy: ≥20% classics, 2–4 reviews, every method
   generation ≥3 papers, ≥25% recent frontier.
3. **One candidate table** (~30 rows: title / year / venue / citations /
   track). You circle your selection **once** — this is the only selection
   pass.
4. **Batch ingest**, 5–10 papers per batch, one merged confirmation per
   batch (see Tutorial 2 for what each confirmation contains).

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

1. **Metadata + citations** fetched and stamped with `citations_date`.
2. **Dedup gate** — the tentative slug (`<firstauthor>-<year>-<titleword>`)
   and DOI are grepped against the vault. On a hit you choose: **skip**,
   **deepen** (add new claims to the existing card; existing quotes are
   never touched), or **correct** (append marked corrections).
3. **palace-extractor** drafts the card: verbatim claims with anchors,
   limitation-derived gap candidates, transfer notes, a suggested weight
   band.
4. **palace-linker** aligns it against 5–15 prefiltered candidates: concept
   slug alignments, ≤5 new-concept proposals, a weighted gap-relation table.
5. **One packaged confirmation** shows you all of it — card, INDEX row,
   registry candidates, gap status proposals. Approve, and the orchestrator
   writes to the Vault.

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
weight: medium (IF 4.2 in 3–10)        # derivation persisted inline
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

Every claim: a verbatim quote, an anchor, and (since KP-07) at least one
concept binding. If a fact has no anchor, it is not in the vault.

---

## Tutorial 3 — Ask questions

```
> /palace ask does classifier-free guidance hurt sample diversity?
```

Three possible outcomes, decided by **coverage**, not by vibes:

- **Sufficient** — a full answer in which *every sentence* carries a tag:
  `[C:smith-2023-emergent]` (a paper states it — go read the anchor),
  `[S]` (synthesis across cards), `[H:transfer-x]` (hypothesis). Weights
  are shown side by side; minority evidence is never drowned.
- **Partial** — only the covered subquestions are answered; the holes are
  listed explicitly ("no vault evidence on diversity metrics beyond FID").
- **Insufficient** — no answer is fabricated. Instead you get a bounded
  **ExpansionProposal**: seed papers/queries derived from the holes, depth
  ≤2, budget ≤50 candidates.

If you accept the proposal, it runs as a normal bounded expansion
(Tutorial 4); when it completes, the **same session resumes** and coverage
is recomputed — ask your question again and the holes should have closed.

Answers are chat-only by default. Say "save it" and it goes through the
auditor + one confirmation into `briefs/<date>-ask-<slug>.md`.

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
```

Every brief is drafted by palace-analyst, then **audited** by
palace-auditor (anchors verifiable, `[C]/[S]/[H]` boundaries respected) —
up to two revision loops before delivery. You confirm the save to
`briefs/<YYYY-MM-DD>-<view>.md`. Briefs are dated, disposable views: re-run
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
   reused; unknown ones become verified session-local sources (never
   auto-ingested).
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
audience, venue, language, length, citation style, style profile) and eight
subdirectories.

Then, in order:

1. **Register inputs.** Your drafts, figures, data, and reviewer comments
   become ProjectMaterials; your reference list resolves Vault-first into
   Project Sources. Materials feed writing but can never become Vault
   evidence.
2. **Freeze the brief.** Problem, contribution, section plan, and the
   evidence package (id-shaped refs with verbatim quotes AND anchors) are
   frozen and fingerprinted. Every subsequent writer package pins that
   fingerprint — the writer cannot silently expand its evidence scope.
3. **Draft a section:**

   ```
   > /palace write guidance-anneal-paper introduction
   ```

   palace-writer drafts within the frozen brief → palace-reviewer reviews →
   at most two automatic revision rounds → palace-auditor checks anchors
   and fabrication. Unresolved findings are shown to you, never looped
   away. A Results-kind section without your registered data comes back
   placeholder-only — results are never invented.
4. **Confirm the save** → `sections/introduction/r001.md`. Revisions are
   append-only; the next save is `r002.md`, and `assembled` is the reserved
   section name for the stitched full document. Declining the save keeps
   the delivery chat-only and the Workspace byte-identical.
5. **Export.** The export step shows you a replayable pandoc plan (CSL:
   explicit override > `project.yaml` > APA; exact argument list) — the run
   executes exactly the plan you saw, into `exports/`, overwriting nothing.
   No pandoc installed → Palace says so instead of improvising.

For grant proposals (`kind: proposal`), the solicitation text first becomes
an anchored **Requirements Matrix**; every uncovered requirement is named
in each delivery, and budget/institutional/preliminary-result statements
validate only against your registered materials.

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
concepts ready for promotion (≥3 genuine-use supporters from ≥2
independent author clusters), provisional weights due for re-derivation,
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
| `doctor` reports an unresolvable root | the four paths in `.palace.toml` resolve relative to that file — check them from the Framework root, not your shell CWD |
| `stale_index` refusals / viewer export aborts | the Vault changed since the last snapshot: `python3 -m knowledge_palace.graph.builder --rebuild` |
| Ingest says the paper already exists | that's the dedup gate — choose skip, deepen (add claims), or correct (append marked corrections); it never overwrites |
| Ask refuses to answer | coverage is insufficient — that's the design; accept the expansion proposal or narrow the question |
| Export step reports pandoc missing | install pandoc yourself; Palace deliberately never installs software or improvises a converter |
| A count looks wrong in `status` | counts are computed live from files — inspect the vault directly; INDEX↔file mismatches are listed in the consistency block |
| Want your vault in Git | do it yourself in the private roots; Palace will neither help nor interfere — that boundary is by design |
