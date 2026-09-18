---
slug: <firstauthor>-<year>-<titleword>   # grep papers/INDEX.md for duplicates BEFORE assigning
title: "<full title>"
authors: [<Last, F.>, ...]
year: <YYYY>
venue: "<journal/conference>"
journal_if: <value> (<source, e.g. OpenAlex 2yr citedness / Scopus CiteScore>)   # or "n/a (preprint)" / "n/a (book)"
citations: <count>
citations_date: <YYYY-MM>                # freshness stamp, always displayed with the count
weight: <high|medium|low> (<derivation>) # derivation is MANDATORY and persisted here, e.g. "high (citations 240 ≥ 100)", "medium (IF 4.8 in 3–10)", "low (IF unavailable; citations 7)"
publication_status: <peer-reviewed|preprint|book|other> # bibliographic context; weight is display-only
source: "<DOI or URL>"                   # locator only — full text is NEVER stored in the vault
local: "<optional source_dir-relative path>"
added: <YYYY-MM-DD>
read_depth: <full|skim|abstract|metadata> # actual reading, not mere file availability
source_coverage: <full-text|excerpt|abstract|metadata>
domain: [<canonical slugs>]              # ALWAYS include the registered domain-root slug so domain-filtered greps work
task: [<canonical slugs>]
pattern: [<canonical slugs>]
function: [<canonical slugs>]
method: [<canonical slugs>]
metric: [<canonical slugs>]
failure-mode: [<canonical slugs>]
gaps: ["gap-<slug>:<relation>", ...]     # relation ∈ identifies|supports|partially_addresses|disputes|reframes
style_card: <optional slug in styles/bank/>
---

# <Title>

## Summary

<2–6 sentences; may be Chinese.>

## Claims

- C1 [<concept-slug>, <concept-slug>]: "<verbatim quote from the paper>" — §<section> [¶<para>] / p.<page>
- C2 [<concept-slug>]: "<verbatim quote>" — §<section> / p.<page>
<!-- The author's wording is authoritative. Search the cached source FIRST,
     then pick the one action that fits:
     Scientific error (quote IS this paper's and accurate, reading was wrong):
       append "- Correction of C<n> (<date>): ..." and a new Claim if needed.
       Never edit the quote.
     Transcription error (wording drifted from the source — dropped citation,
     clause, qualifier or index): repair the quote in place to match the
       source exactly. No Correction entry; report the repair instead.
       Keep a source typo verbatim and mark it "[sic]".
     Wrong position (quote sits elsewhere in this paper): fix only the anchor.
     Wrong source (quote not in this paper at all): append
       "- Retraction of C<n> (<date>): ..." naming the true source.
     A retracted Claim stays on the card but is no longer evidence: it binds no
     concept and no Argument/Conditions/Evidence relations row may cite it.
     Every NEW claim binds ≥1 canonical concept slug in the
     bracket group (validated by semantic/binding.py before confirmation);
     historical claims without brackets stay valid until their migration
     packets. -->

## Study profile

<!-- OPTIONAL methodology view: roles are claim references ONLY (no free
     text), from exactly ONE role set —
     empirical: subjects, method, comparator, outcomes, limitations
     review: corpus, selection, synthesis
     theoretical: assumptions, mechanism, predictions, validation
     Delete this section when no set applies. -->
- <role>: C1, C3

## Argument

| Role | Claim | Paraphrase | Attribution | Scope |
|---|---|---|---|---|
| problem | C1 | <normalized author question> | author | <question scope> |
| advance | C2 | <claimed contribution> | author | <tested conditions> |
<!-- Add remaining only when explicitly stated and anchored; omit absent roles. -->

## Conditions

<!-- Reading checklist for dimensions worth a row when the paper states them
     (each Value must trace to a cited Claim; "Not reported" is not a row):
     data: dataset name/version, variables, spatial/temporal resolution and
       period, sample size (cases/events/grid points/years), QC and case-selection
       criteria, how key quantities are defined (what counts as an event, a hit);
     method: model/method name and version, configuration (grid spacing, physics,
       IC/BC, ensemble size; or model specification, treatment/outcome,
       covariates, identification strategy), experimental design (controls,
       baselines, splits/cross-validation), evaluation metrics with non-standard
       definitions, uncertainty quantification (bootstrap, CI, significance). -->
| Dimension | Value | Evidence |
|---|---|---|
| <relevant study dimension> | <condition stated in the cited Claim> | C2 |

## Evidence relations

| Claim | Relation | Target | Attribution | Comparison | Scope | Rationale |
|---|---|---|---|---|---|---|
| C2 | partially_addresses | gap:<slug> | system | retrospective | <subquestion and conditions> | <why this Claim advances this question> |
<!-- Full relation vocabulary and attribution rules: protocol/EVIDENCE.md. -->

## Analysis evidence

<!-- Optional compact reading record relating load-bearing Claims to the analysis,
     comparison or figure that supports them. Prose for readers; not a parsed
     schema and not an independent source of evidence. -->
| Claim | Analysis / figure | What it supports | Boundary |
|---|---|---|---|
| C2 | <table/figure/experiment and its location> | <what that analysis shows for this Claim> | <sample, conditions, uncertainty> |

## Limitations & gaps

- <limitation as stated or as system-inferred; if it seeds/relates to a gap card,
  name it: gap-<slug> (<relation>)>
<!-- Also record null findings and results that did not support the authors'
     hypothesis, and conditions under which the authors say results may not hold. -->

## Transfer notes

<!-- Only if the paper is cross-domain or carries a transferable function.
     Otherwise delete this section. -->
- <function/pattern that could transfer, toward which domain/task, and why>

## Reading notes

<!-- Dated entries: the question the paper was read for, what the reading added,
     interpretation, and unresolved reading work. Notes are system/user working
     material, never Claims. -->
- <YYYY-MM-DD>: <question read for; what was added; what remains unread>
<!-- Worth noting here when present: cited references worth following up (with
     reason; feeds expand), parts that could not be read reliably (unreadable
     figures, missing supplementary material, ambiguous notation), and unstated
     assumptions the method depends on — as reader interpretation, not Claims. -->
