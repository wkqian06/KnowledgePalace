---
slug: transfer-<slug>
relation: <similar_problem_pattern|transferable_method_function|shared_failure_mode|shared_validation_logic|prerequisite_or_enabler>
# analogy_only and spurious_relation verdicts are reported and dropped — never written as cards.
a: <home-domain concept slug>            # the local task/gap side
c: <foreign-domain concept slug>         # the external source side
bridges: [<canonical slugs>]             # ≥2, none from the PALACE.md hub stopword list
status: <candidate|monitor|pursuing|dropped>
gaps: [gap-<slug>, ...]                  # gaps this transfer could address
papers: [<paper-slugs>]                  # evidence carriers on both sides
---

# transfer-<slug>

## Hypothesis

<One sentence: what transfers from C to A and what it would achieve.>

## Bridge evidence

- A–B: "<verbatim or C-ref from a home-domain paper>" — <paper-slug>, §<sec> / p.<page>
- B–C: "<verbatim or C-ref from the foreign-domain paper>" — <paper-slug>, §<sec> / p.<page>

## Assumptions & risks

- <what must hold for the transfer to work; what breaks it>

## First validation step

<ONE concrete minimal experiment: data, method, metric, success criterion.>

## Decision log

<!-- Append-only: status changes with date and reason. -->
- <YYYY-MM-DD> <status>: <reason>
