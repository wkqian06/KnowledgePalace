# Build or extend a literature collection

`init <topic> [n]` starts from a topic and can extend an existing collection.
`expand <target>` starts from papers, a question or an identified evidence hole
and follows related work and citations. Both finish selected papers through
[ingest](ingest.md). `discover` is cross-domain bridge analysis, not search.

Use the user's research question, inclusion conditions and requested breadth to
choose sources and queries. Search via available providers or browsing tools;
record queries, dates, source availability and selection reasons. Citation and
venue metadata are background, not scientific quality scores. Avoid fixed quotas
of classics/reviews/frontier papers when they distort the actual question.

Match candidate identities to the library and merge repeated discoveries. When
the user names papers or delegates selection within a clear scope, proceed within
that scope. Otherwise present a bounded candidate selection once. Unselected
records remain in the existing expansion/discovery state; they are not Claims.

An expansion batch (`expansion.engine.review_batch`) is decided by the user, or
by you within a scope the user delegated. Judge each candidate only from its
normalized metadata (identity, title, abstract, venue, year, citation signal,
discovery occurrences) against the run's scope; do not fetch full text or call
providers to decide. Each decision is `selected`, `deferred` or `rejected`, with
a one-line reason naming the field or occurrence it rests on. A rejection holds
for this scope only, never as a global blacklist. Mark at most one or two
exploratory picks per batch. Vault hits are acknowledged, never selected again
for ingestion. A metadata-only candidate is never a next-hop seed: only ingested
works, the user's roots and vault hits expand. When the batch exceeds the run
budget, rank, cut and report what was cut. Record the decisions with
`expansion.engine.apply_decisions`, `decided_via` naming who decided.

For selected library hits, reuse the card and read/update it when new information
is needed. For selected misses, acquire and read available material and create a
card, including explicitly limited cards when only abstracts/metadata are available.
Record unavailable full text and how it limits the requested analysis.

Report selected papers, reused/new cards and source coverage. When collection was
requested by another workflow, return those stable references and resume its
original question. An existing domain never requires a second domain bootstrap.
