# Risk controls

Each retained check names the actual error it prevents and what happens
differently when it fires. Scientific correctness is never one of these checks.

## Paper save boundary

- Location: `acquisition/transaction.py:save_paper`.
- Boundary: the one write path for paper cards and the papers INDEX.
- Prevents: a second card for a paper already in the library (shared DOI/arXiv id
  or identical title under another slug); silent edits to an existing Claim's
  quote or anchor; a metadata-only or abstract-only source labeled as a full or
  skimmed reading; new Claims bound to unregistered concepts; evidence relations
  pointing at Claims/Gaps that do not exist; a misspelled `source_coverage` that
  would bypass the abstract gate.
- Behavior: raise `ValueError` listing every violation; nothing is written. A
  correct save writes the card atomically, then rewrites only that slug's INDEX
  row. Re-saving identical text returns `unchanged` and touches nothing.
- Verification: `tests/test_transaction.py::TestSavePaper`.
- Retention: required while cards are the authoritative store and are edited
  through agents.

## Card evidence tables

- Location: `semantic/evidence_helpers.py:read_tables` and `graph/builder.py:build_payload`.
- Boundary: operator-authored optional Markdown tables and their Claim/Gap refs.
- Prevents: malformed rows, invalid roles/attribution/comparison, duplicate
  relations, or unresolved evidence/dependency references entering the graph.
- Behavior: report the affected card and row/ref in the index identity report;
  exclude the invalid relation from the graph. Absent sections are valid (legacy cards).
- Verification: `tests/test_research.py`, `tests/test_index_builder.py`.
- Retention: needed while Markdown cards are externally edited.

## Query contract

- Location: `graph/port.py`.
- Boundary: graph responses consumed by analysts and viewers.
- Prevents: a consumer reading an unknown node/hierarchy/level or an unusable page
  cursor as an empty-but-valid result.
- Behavior: typed error response (`unknown_node`, `unknown_hierarchy`,
  `invalid_request`, `bad_cursor`) instead of an exception or silent omission.
- Verification: `tests/test_port_contract.py`, `tests/test_viewer_export.py`.
- Retention: required by GraphQueryPort semantics.

## Research review and project observations

- Location: `semantic/update_helpers.py:resolve_update` and
  `workspace/research_helpers.py:project_context`.
- Boundary: operator review decisions and project-authored observation tables.
- Prevents: marking a non-pending or unknown update as reviewed; a review without
  rationale; an observation that names no registered material or no declared
  judgment being read as literature evidence.
- Behavior: reject the specific operation with its reason. Pending evidence events
  stay intact until explicit review; later changes reopen them.
- Verification: `tests/test_research_continuity.py`.
- Retention: required to distinguish completed review from unprocessed evidence
  and project observations from literature Claims.

## Revisions, roots and offline guarantee

- `workspace/revision.py:save_revision` links each `rNNN.md` with `os.link`, so an
  existing revision can never be overwritten; a collision raises and numbering
  moves on. Verified by `tests/test_workspace_revision.py`.
- `tools/config_resolver.py` requires the four private roots to exist, be distinct
  and resolve relative to `.palace.toml`; a bad configuration raises `ConfigError`
  before any read or write. Verified by `tests/test_config_resolver.py`.
- `tests/test_offline_guarantee.py` asserts that network markers appear only in
  `metadata/providers.py`, so no other module can reach the network by accident.
