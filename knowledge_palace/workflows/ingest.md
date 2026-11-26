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
   printed pages must be distinguishable: a PDF's text companion marks each
   `===== [PDF page N] =====`, where N is the PDF page index, not the printed
   page number. An abstract-only card can contain
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

Align the draft with the registry and the Gap landscape from a prefiltered set:
the relevant `concepts.md` sections, 5–15 gap and paper cards and their INDEX
rows, never the whole Vault; when that set is insufficient, say so in the report
rather than reading wider. Map each concept term to its canonical slug, through
Aliases where they match, or mark it `NEW` or `DROP` with a reason. A new concept
stays within the per-paper limit in PALACE.md, with its axis, Parents, status
`candidate` and a one-line justification; no `Parents` edge joins two domain
subtrees. Do not invent a Gap just to populate the card. Evidence relations
follow EVIDENCE.md: a `gap:` target takes `identifies`, `supports`,
`partially_addresses`, `disputes` or `reframes`; a `claim:` target takes
`same_question`, `overlaps`, `broader_than`, `narrower_than` or
`different_question`. When the paper identifies a gap no card covers, draft a gap
card from `knowledge_palace/templates/gap-card.md` (status `open`, `source_type`
set) and, where it shares a failure mode with an existing gap, including one in
another domain, propose a `related:` link with a one-line reason. Update a Gap's
current synthesis only where the evidence changes it. The paper's `weight` follows
the bands in PALACE.md.

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
return value.

A long paper, or several papers read in parallel, can go to palace-extractor.
Give it the absolute paths of the cached text, this workflow,
`knowledge_palace/templates/paper-card.md`, the existing card if any and the
relevant `concepts.md` sections, with the source version, the reading question
and the depth. This context then receives the draft instead of the paper; you
align it, review it and save it as above. A draft that ends with an interruption
note is incomplete; have the remaining sections read again. A subagent returns a
reading draft and never writes authoritative files.

Review the judgments this batch put in the queue before the ingest ends, while its
papers are still in context. For each Gap, brief or bridge entry, propose in the
report whether to retain the judgment or revise it within its conditions; after
the user confirms, write the revisions and record each decision with
`research resolve`. A revision that would move a Gap's status waits for the next
govern, which applies the counting rules across the library and has
palace-auditor review the move. An entry this ingest cannot review also waits for
govern; name it in the report. Project entries are the user's research decisions:
list them in the report and leave them open.

An explicit ingest request or an approved collection scope includes the selected
papers' cards, source preservation and a domain those papers open. Do not ask the
user to select them again. Ask only about a genuinely unresolved identity or
scope choice. Report saved paths, reading depth, unavailable material, a domain
opened with its scope and reasoning, and what the reading added.

A temporary ProjectSource is a discovery locator. When a paper is adopted, save
its card, rebuild the index, and resolve the reference again
(`research source "<DOI, arXiv id or title>"`): the reference now returns the
Work to cite. Retain old project-source references for historical drafts; use
Vault refs for new work.
