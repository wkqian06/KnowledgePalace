# Build or extend a literature collection

`init <topic> [n]` starts from a topic and can extend an existing collection.
`expand <target>` starts from papers, a question or an identified evidence hole
and follows related work and citations. Both finish selected papers through
[ingest](ingest.md). `discover` is cross-domain transfer analysis, not search.

Use the user's research question, inclusion conditions and requested breadth to
choose sources and queries. Search via available providers or browsing tools;
record queries, dates, source availability and selection reasons. Citation and
venue metadata are background, not scientific quality scores. Avoid fixed quotas
of classics/reviews/frontier papers when they distort the actual question.

Match candidate identities to the library and merge repeated discoveries. When
the user names papers or delegates selection within a clear scope, proceed within
that scope. Otherwise present a bounded candidate selection once. Unselected
records remain in the existing expansion/discovery state; they are not Claims.

For selected library hits, reuse the card and read/update it when new information
is needed. For selected misses, acquire and read available material and create a
card, including explicitly limited cards when only abstracts/metadata are available.
Record unavailable full text and how it limits the requested analysis.

Report selected papers, reused/new cards and source coverage. When collection was
requested by another workflow, return those stable references and resume its
original question. An existing domain never requires a second domain bootstrap.
