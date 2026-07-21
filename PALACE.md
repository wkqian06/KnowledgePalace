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

## Weight bands (impact factor × citations; seed values, user-adjustable)

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
  (always displayed with the count). No automatic refresh in V1, except the
  provisional re-derivation below.
- Papers < 2 years old at derivation carry a provisional annotation —
  `weight: <band> (provisional — citations immature, ingested YYYY-MM)` —
  and are re-fetched/re-derived at every `/palace govern` run; the marker is
  dropped once the paper turns 2 years old.
- Peer-review floor: a peer-reviewed paper < 3 years old with immature
  citations takes a MEDIUM floor (transition-eligible under rule 1).
  Preprints still band by citations only.
- Confirmation-gate uplift: at ingest confirmation the user may uplift a band
  on qualitative signals (author pedigree via the co-authorship network, code
  release, operational deployment); the reason MUST be persisted inside the
  `weight:` derivation annotation.

### Qualitative weight rules (linker/analyst must cite these in verdicts)

1. A gap status transition (open → partially-addressed, → closed, …) requires
   ≥ 1 supporting relation of high or medium weight. Preprint/low-only evidence
   can NEVER close or reverse a gap — it may only be recorded as "an unresolved
   challenge exists".
2. "Established" in a brief: ≥ 2 independent sources with consistent claims,
   including ≥ 1 high-weight. Consistent low-weight evidence is at most
   "emerging consensus". Independence is mechanical, via the co-authorship
   network: two papers whose `authors:` sets intersect (≥ 1 shared name, ONE
   hop) count as one source; transitive closure is FORBIDDEN (small-world
   collapse would make this rule unsatisfiable). The co-authorship edge list
   (`pair: ×count, first–last year`) is computed live from `authors:` +
   `year:` fields, never stored. Qualitative reading: count = 1 edges from
   large-consortium papers are incidental, not lab proximity; corroboration
   from disconnected network components may be annotated as stronger.
3. `brief ideas` ranking considers gap-relation weights and transfer-evidence
   weights but never drowns minority evidence: high-weight conclusions and
   low-weight counterexamples are shown side by side, each labeled with weight.
4. No numeric weighting formula — on a corpus of this size it is false precision.

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
  refreshed with the citation refresh at `/palace govern`.
- Stars/forks are attention proxies, not usage; real usage (PyPI downloads,
  dependents) is labeled as such. Official vs third-party repos are
  distinguished; monorepo star counts carry a caveat.
- Retroactive backfill: existing cards at the next full govern pass; classics
  default `none-stated` at zero cost.
- Reproduction-event convention: an independent reproduction = a `supports`
  relation whose evidence cell explicitly says "independent reproduction";
  under mechanical rule 2 (author-disjoint) the analyst may upgrade "two
  consistent teams" wording to "independently reproduced".
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
| concept promotion | candidate → canonical at ≥ 3 confirmed supporting papers that genuinely USE the concept, drawn from ≥ 2 independent author clusters (rule-2: author sets disjoint). Baseline-only comparison does not count (see Concept conventions); single-cluster support keeps the row candidate with a note. |
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

- A candidate concept reaches ≥ 3 genuine-use supporters from ≥ 2 independent
  author clusters → promotion proposal (baseline-only tags excluded).
- A provisional-weight paper exists (grep `provisional` in papers/) → re-fetch citations, re-derive its band; drop the marker at age 2 yr.
- A non-canonical raw term recurs in ≥ 3 cards' Summary/notes text without a registry row (grep the term) → alias or new-concept proposal.
- `concepts.md` grows unwieldy from multi-domain growth → propose per-axis file split (schema unchanged).
- Orphan tags (card tags absent from the registry) found → repair proposal.
- Deprecated slug still referenced by any card → migration proposal (`grep -l` impact list attached).
