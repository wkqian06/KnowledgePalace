# Read and retain a paper

Used by ingest, selected init/expand results, and literature adopted during ask,
write, polish or feasibility. A completed reading creates or updates one paper
card. Search candidates that were not selected remain discovery records.

## Resolve and read

1. Resolve the configured roots only when accessing the library. Match the DOI,
   arXiv identity and title against existing papers; reuse the existing slug.
   For a preprint/published pair, verify the relationship and record the version
   actually read. A related title alone is not permission to merge.
2. Acquire the best available source through the existing local, Zotero or OA
   provider, or an available browsing/PDF tool. Store full text in Source Cache.
   Record `source_coverage: full-text|excerpt|abstract|metadata` and the actual
   `read_depth: full|skim|abstract|metadata`. Coverage and reading depth differ:
   possessing a full PDF does not mean it has been read fully.
3. Read to the user's question and requested depth. Use sections, figures,
   tables, equations and source blocks to locate evidence. PDF page indices and
   printed pages must be distinguishable. An abstract-only card can contain
   abstract quotes; a metadata-only card has no scientific Claims.
4. Explain the author's question, method, principal findings and boundaries.
   Relate load-bearing Claims to the supporting analysis, comparison or figure.
   Add relevant Argument and Conditions rows using existing Claim references.
   Record author-stated remaining questions separately from system inferences.
   Missing material remains missing, without filling template rows by invention.

## Place in a domain

Every card carries the root slug of a registered domain. Infer it from the paper
and from what the library holds: the question the paper asks and the literature
it cites and answers, read against each registered domain's scope in
`domains.md`, its concept subtree in `concepts.md`, and the papers and Gaps filed
under it (INDEX first). The domain criterion is in PALACE.md.

When a registered domain holds the paper, tag that root. When the paper is a
toolbox, or brings one to a question a registered domain asks, tag the domain
whose question it serves and put the toolbox on the shared axes. When the paper
belongs to a research community that no registered domain covers, open that
domain before saving the card:

1. Scope the domain to that community, so that the literature the paper cites
   and answers falls inside it.
2. Write the `domains.md` row, with the scope and what separates it from
   neighbouring domains in Notes, and the root concept row on the domain axis of
   `concepts.md`, with no Parents. The paper's new concepts hang under that root
   within the per-paper limit; shared-axis concepts are reused first, and no
   `Parents` edge joins two domain subtrees.
3. Append a Governance Decision to `governance/decisions.md`: the seed paper,
   the reasoning from the paper and the holdings, and the affected objects.

Papers of one batch that need the same new domain open it once.

## Save and connect

Use the paper template, omitting sections with no supported content. An optional
`## Analysis evidence` table uses `Claim | Analysis / figure | What it supports |
Boundary` for a compact reading record. This is prose for readers, not another
schema or an independent source of evidence. Add dated `## Reading notes` for
interpretation, the user's question and any unresolved reading work.

For an existing card, preserve all original Claim numbers; add new Claims only
when needed. A misread quote takes an appended correction and keeps its wording.
A quote whose wording or source is in doubt is checked against the cached source
before deciding: repair the wording in place when it drifted from the source, fix
the anchor when the quote sits elsewhere in this paper, retract the Claim when it
is not this paper's, and repoint any table row that cited it. A repair needs
`source_dir`; save_paper refuses wording the cached text does not carry.
Use available canonical concepts; do not invent a Gap just to populate the card.
Link to relevant existing Gaps when justified and update their current synthesis
only where the evidence changes it.

The main agent saves the reviewed paper through
`acquisition.transaction.save_paper(vault_dir, card_text, source_dir)`. It refuses
a duplicate identity under another slug, keeps every existing Claim's quote, refuses
a table row that cites a retracted Claim, checks that reading depth matches source
coverage, and updates the paper INDEX. Always pass `source_dir`: each new Claim's
quote must then be verbatim in the paper's cached text, an elided quote piece by
piece. A paper with no text cache, or an OCR one, is saved with its new quotes
unchecked, and the result's `quotes_checked` is false; report those cards. When a
correct quote is refused, the cache is damaged: re-extract it in reading order
rather than rewording the quote. After the
whole batch and any related Gap edits, call
`graph.builder.ensure_index(vault_dir, state_dir, workspace_dir)` once; without the
workspace root, project-level impacts are not recorded. Affected judgments are then
read with `python -m knowledge_palace.interaction.research updates`, not from the
return value. Subagents return reading drafts and never write authoritative files.

An explicit ingest request or an approved collection scope includes the selected
papers' cards, source preservation and a domain those papers open. Do not ask the
user to select them again. Ask only about a genuinely unresolved identity or
scope choice. Report saved paths, reading depth, unavailable material, a domain
opened with its scope and reasoning, and what the reading added.

A temporary ProjectSource is a discovery locator. When a paper is adopted, save
its card, rebuild the index, and run `interaction.project_source.resolve` again
against the fresh `load_vault_identity` result: the reference now returns the
Work to cite. Retain old project-source references for historical drafts; use
Vault refs for new work.
