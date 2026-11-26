---
slug: bridge-<slug>
relation: <similar_problem_pattern|transferable_method_function|shared_failure_mode|shared_validation_logic|prerequisite_or_enabler>
# analogy_only and spurious_relation verdicts are reported and dropped — never written as cards.
from: <foreign-side concept, paper or gap slug>  # the capability or finding in the other domain
to: <home-side gap or task slug>                 # the local problem it could serve
via: [<canonical slugs>]                         # ≥2 shared-axis concepts, none from the PALACE.md hub stopword list
status: <candidate|monitor|pursuing|dropped>
gaps: [gap-<slug>, ...]                          # gaps this bridge could address
papers: [<paper-slugs>]                          # evidence carriers on both sides
---

# bridge-<slug>

## Hypothesis

<One sentence: what carries over from the `from` side to the `to` side and what it would achieve.>

## Bridge evidence

- Home side (to–via): "<verbatim or C-ref from a home-domain paper>" — <paper-slug>, §<sec> / p.<page>
- Foreign side (from–via): "<verbatim or C-ref from the foreign-domain paper>" — <paper-slug>, §<sec> / p.<page>

## Assumptions & risks

- <what must hold for the bridge to carry over; what breaks it>

## First validation step

<ONE concrete minimal experiment: data, method, metric, success criterion.>

## Decision log

<!-- Append-only: status changes with date and reason. -->
- <YYYY-MM-DD> <status>: <reason>
