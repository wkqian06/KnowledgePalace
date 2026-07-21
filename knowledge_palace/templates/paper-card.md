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
source: "<DOI or URL>"                   # locator only — full text is NEVER stored in the vault
local: "<optional source_dir-relative path>"
added: <YYYY-MM-DD>
read_depth: <full|skim>                  # classics default to full
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
<!-- Quotes are immutable once written. Corrections append a new entry marked
     "Correction of C<n> (<date>): ..." — never edit the original.
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

## Limitations & gaps

- <limitation as stated or as system-inferred; if it seeds/relates to a gap card,
  name it: gap-<slug> (<relation>)>

## Transfer notes

<!-- Only if the paper is cross-domain or carries a transferable function.
     Otherwise delete this section. -->
- <function/pattern that could transfer, toward which domain/task, and why>
