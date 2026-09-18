# PALACE.md — Public Policy

Static Framework policy for concept axes, hub stopwords, weight bands, and
operational thresholds. Private registries live in the configured Personal Vault:
`domains.md` for domains and `concepts.md` for concepts.

## Domain registry schema

| Slug | Name | Status | Seeded | Notes |
|---|---|---|---|---|

New domains enter via `/palace domain add <name>`: seeded from 1–2 review or
representative papers, concept subtree proposed (reusing shared axes first),
confirmed by the user, then written to the configured Vault. Palace performs no
Git operation in the Vault.

## Concept axes (7)

| Axis | Scope | Sharing |
|---|---|---|
| domain | Physical/subject concepts of a domain | per-domain subtree |
| task | Problems a domain works on | per-domain subtree |
| pattern | Abstract problem/solution structures | shared across domains |
| function | Capability a method provides | shared across domains |
| method | Concrete techniques, algorithms, systems | shared where applicable |
| metric | Evaluation measures | shared (generic) + domain-specific |
| failure-mode | Recurring ways approaches fail | shared across domains |

Cross-domain relations live ONLY in shared axes (pattern/function/failure-mode),
transfer cards, or a gap card's `related:` field. NEVER as `Parents` edges between
domain subtrees — between top-level domains there are only bridges, no hierarchy.

## Hub stopwords (banned as transfer bridges)

`deep-learning, machine-learning, neural-network, ai, artificial-intelligence,
model, data, dataset, prediction, algorithm, learning, training, optimization,
performance, accuracy, evaluation, benchmark, framework, architecture`

palace-scout must not count any of these as a bridge concept; a candidate transfer
whose only bridges are stopwords is `spurious_relation` (report and drop).

## Bibliographic context bands (display and field attention)

| Band | IF channel | Citations channel (age-tiered, at derivation time) |
|---|---|---|
| high | IF ≥ 10 | ≥ 25 (< 1 yr) · ≥ 50 (1–5 yr) · ≥ 100 (> 5 yr) |
| medium | IF 3–10 | ≥ 10 (< 1 yr) · ≥ 20 (1–3 yr) · 20–99 (> 3 yr) |
| low | everything else | everything else |

- Band = the HIGHER of the IF band and the citations band.
- Preprints have no IF: band by citations only.
- Books have no IF: band by citations and domain-classic status (a classic
  textbook counts as high).
- Missing data: band by whatever is available and annotate on the card, e.g.
  `weight: low (IF unavailable)`.
- IF source: JCR IF is not open data. Use Scopus CiteScore or OpenAlex 2-yr
  citedness as the substitute and note the source next to the value.
- Citations are fetched at ingest time and stamped with `citations_date`
  (always displayed with the count). Later refreshes are explicit.
- Papers < 2 years old at derivation carry a provisional annotation —
  `weight: <band> (provisional — citations immature, ingested YYYY-MM)` —
  and are reported for explicit `/palace refresh`; the marker is
  dropped once the paper turns 2 years old.
- A band reads field attention, never scientific standing. It says how often a
  work has been cited and where it appeared, which tracks how active or
  fashionable its area is; it says nothing about how much of a question that
  work answered. Age and publication adjustments are context of the same kind.
- No band, citation count, venue metric or publication type may decide a Gap
  status change, make evidence "transition-eligible", freeze a work out of a
  judgment, or alter a recorded relation. A relation records what the work did
  with the question, so a preprint that substantively answers one is recorded
  `partially_addresses` at whatever band it carries. Status follows the
  substance of the answer and what it leaves open; see EVIDENCE.md.
- Confirmation-gate uplift: at ingest confirmation the user may uplift a band
  on qualitative signals (author pedigree via the co-authorship network, code
  release, operational deployment); the reason MUST be persisted inside the
  `weight:` derivation annotation.

### Evidence judgment (extractor/linker/analyst/auditor)

1. Gap status changes cite concrete Claims, study design, evidence directness,
   applicable conditions and the subquestions advanced or left open. Citation
   counts, venue metrics, attention bands and publication type never decide a
   scientific conclusion or prevent counterevidence from changing it.
2. Evidence independence concerns shared data, samples, methods, assumptions and
   analyses. Explain these dependencies; author overlap is background information,
   never a substitute. Strong consensus language needs converging direct evidence
   across relevant conditions and a reasoned assessment of those dependencies.
3. Show counterevidence beside supporting evidence. Align populations, measurement
   definitions, sampling and evaluation before calling results contradictory.
   Research opportunities state importance, existing evidence, the inference step,
   alternatives and a validation design that can distinguish them. Low Vault
   coverage is not a field-wide research gap.
4. Use reasoned judgments, without numeric evidence scores or rankings derived
   from bibliographic context. Preserve dated citation/venue metadata for display.

## Reproducibility fields

Paper cards carry four OPTIONAL frontmatter fields:

```yaml
code: <URL | none-stated>            # code/model-weights availability; link liveness checked at ingest
data: <public | licensed | closed | none-stated>   # training/eval data availability, as stated by authors (anchored)
compute: "<training/inference cost, near-verbatim>" # e.g. "~1.3 s/sample on V100 (inference)"; none-stated if absent
code_usage: "<repo, stars/downloads, kind, YYYY-MM>" # dated snapshot, display-only; NEVER enters weight derivation
```

- Values come from author statements with anchors (same evidence discipline as
  Claims); absent → `none-stated`, never guessed. `code_usage` is the one
  exception: it is orchestrator-fetched (GitHub/PyPI), always dated, and
  refreshed only by explicit `/palace refresh`.
- Stars/forks are attention proxies, not usage; real usage (PyPI downloads,
  dependents) is labeled as such. Official vs third-party repos are
  distinguished; monorepo star counts carry a caveat.
- Retroactive backfill: existing cards at the next full govern pass; classics
  default `none-stated` at zero cost.
- Reproduction-event convention: a `supports` relation names the repeated result,
  data and method dependencies, and scope. Call it independently reproduced only
  when the underlying study design supports that description.
- Explicitly not adopted:
  reproducibility scores/grades (false precision), a new concept axis (paper
  attributes are not knowledge concepts), system-run reproduction experiments
  (out of scope).

## Evidence conventions

- **Quote-artifact normalization**: PDF-extraction ligatures (ﬁ→fi) and math
  symbols rendered as `$` etc. are normalized to their original meaning (≥, ±)
  inside verbatim quotes; ¶ indices are best-effort from two-column extraction.
  This normalization does not violate evidence immutability; substantive
  wording is never altered.
- **Supports-by-omission**: a paper that HAS a capability (e.g. a probabilistic
  variant) but does not evaluate it may carry a `supports` relation on the
  corresponding evaluation/standard gap, with the omission stated in the
  evidence cell.
- **Alias strictness**: aliases map input TERMS to a slug (systems, acronyms,
  notation variants of the same referent). System names are NOT aliased to
  generic pattern slugs; recurring named systems receive their own method slug.

## Thresholds

| Parameter | Value |
|---|---|
| discover gate | ≥ 15 papers total AND ≥ 3 cross-domain papers (a cross-domain paper = its `domain:` array contains ≥ 1 registered slug outside the home domain's subtree; domains must be registered via `domain add` BEFORE such papers are ingested) |
| concept promotion | candidate → canonical at ≥ 3 confirmed supporting papers that genuinely USE the concept, with evidence from distinct data or analyses, assessed under evidence rule 2. Baseline-only comparison does not count (see Concept conventions); dependent support keeps the row candidate with a note. |
| new concept proposals | ≤ 5 per paper (linker) |
| linker prefilter budget | 5–15 candidate cards per paper; INDEX-first, never full-vault reads |
| batch ingest size | 5–10 papers per batch, one merged confirmation |
| govern cadence | every ~20 ingested papers, or when a trigger fires |
| style profile stability | rule is `stable` at support ≥ 3 sources and no open conflicts |
| V2 trigger | backlog > 20 unprocessed papers, or ≥ 10 papers/week making per-paper confirmation the bottleneck |

## Concept conventions

- **Baseline tags.** A method/system slug may be tagged in a card's
  frontmatter even when the paper only compares against it as a baseline —
  this preserves discoverability for baseline searches. But
  baseline-only tags do NOT count toward promoting that slug to canonical;
  promotion counts genuine-use supporters only.
- **System-slug precedent.** A named system earns a registry slug once it
  is referenced as a method or baseline by ≥ 2 independent papers; a system
  appearing in only one paper is described in that card's prose, not minted.
- **Metric parent tagging.** Tag the most specific applicable metric slug;
  add its parent slug only when the paper separately uses the parent's broader
  form; do not tag both a child metric and its parent unless both are distinctly
  used.

## Governance triggers (checked by `/palace govern`, computed live by grep)

- A candidate concept reaches ≥ 3 genuine-use supporters from distinct data or analyses → promotion proposal (baseline-only tags excluded).
- A provisional-weight paper exists → propose explicit citation refresh; governance never fetches metadata.
- A non-canonical raw term recurs in ≥ 3 cards' Summary/notes text without a registry row (grep the term) → alias or new-concept proposal.
- `concepts.md` grows unwieldy from multi-domain growth → propose per-axis file split (schema unchanged).
- Orphan tags (card tags absent from the registry) found → repair proposal.
- Deprecated slug still referenced by any card → migration proposal (`grep -l` impact list attached).
- A registered domain's cards split into task-tag groups that rarely co-occur on one card, or a domain-axis root concept exists without a `domains.md` row → domain-partition proposal (candidate domains, the cards whose root tag would change, computed by `graph.identity.domain_partition_report`). Criterion: papers written by one community that cite each other and share gap cards form a domain; a toolbox that several communities each use belongs on the shared method/pattern axes, never as a domain.
