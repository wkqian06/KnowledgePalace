# KnowledgePalace Protocol — platform-neutral core

This file is the single authority for Palace behavior shared by every runtime.
Runtime entries (`.claude/skills/knowledge-palace/SKILL.md`,
`.agents/skills/knowledge-palace/SKILL.md`) are thin adapters: they route
commands here and must not duplicate the bodies below. Command surface and
per-command flows live in `COMMANDS.md`; the internal query contract lives in
`GRAPH_QUERY_PORT.md`; role contracts live in `../agents/`; card templates in
`../templates/`; deterministic tools in `../tools/`.

The configured Personal Vault is the single source of confirmed knowledge:
markdown, human-readable, and grep-computable. The Framework's `PALACE.md` is
public static policy; the Vault's `domains.md` and `concepts.md` are private
registries. The mirrored main-agent contract (`AGENTS.md` == `CLAUDE.md`)
applies to every flow.

## Storage resolution

Load exactly `<Framework root>/.palace.toml`. Resolve its `vault_dir`,
`state_dir`, `source_dir`, and `workspace_dir` values against the config file's
directory, never against the shell CWD (deterministic implementation:
`tools/config_resolver.py`). Treat card and INDEX paths as Vault-relative;
treat paper-card `local` values as `source_dir`-relative. Pass resolved
absolute data, policy, and template paths to subagents, which never discover
roots themselves. The four roots must exist, be distinct, and lie outside the
Framework worktree. Private-root Git topology is exclusively user-managed:
Palace neither inspects nor blocks repositories the user creates in or above a
private root. Every bare Framework path in this protocol is a logical label
resolved against the Framework root, never against CWD.

Only the Framework is a Palace-managed Git boundary. Never run any Git command
with a private root as CWD or target, regardless of whether the user placed a
`.git` marker there (advisory check: `tools/git_guard.py`). Confirmed private
writes do not create commits. Framework work forms at most one local commit
per completed Goal and is never pushed automatically.

## Roles and dispatch

The main agent is the orchestrator: it resolves roots, runs INDEX-first grep
prefilters, dispatches read-only subagents, aggregates drafts, presents one
packaged confirmation, and performs every approved write. Subagents never
write files and never scan outside the handed candidate set.

Nine platform-neutral role contracts live in `knowledge_palace/agents/`:

| Role | Mission |
|---|---|
| palace-extractor | full text + metadata → anchored paper-card draft |
| palace-linker | draft + prefiltered candidates → concepts and gap relations |
| palace-scout | target + shared axes → evidence-backed transfer candidates |
| palace-auditor | adversarial evidence, schema, and provenance review |
| palace-analyst | briefs, ask answers, idea critiques, and intro drafts |
| palace-stylist | style feature cards and crystallized profiles |
| palace-expansion-reviewer | scope-specific candidate selection for bounded expansion |
| palace-writer | genre-shaped draft/revise/assemble from frozen evidence packages |
| palace-reviewer | scholarly quality and genre-requirement review of drafts |

Dispatch is a task package built by `tools/task_package.py`: role, shared
contract path, protocol references, handed inputs (absolute paths + hashes),
read-only constraints, and the expected draft kind. Both runtimes build
packages through this one tool so the package schema cannot drift. In runtimes
without native subagent support, execute each contract in a separate read-only
context and return its draft to the orchestrator.

External capabilities are called but never modified: academic-search providers
for metadata and citations, plus downloader/reader providers for full text. If
they are unavailable, query OpenAlex metadata and ask the user for a local
full-text path.

## Write invariants

1. Subagents never write files; the main agent performs every approved write.
2. No Claim enters a card without a verbatim evidence anchor
   (`— §<section> [¶<para>] / p.<page>`). Every NEW Claim
   additionally binds at least one concrete Concept via the optional bracket
   group (`- C<n> [slug, …]:` — validated by `semantic/binding.py` before
   the packaged confirmation); historical claims stay valid unchanged until
   their dedicated migration packets.
3. Every gap status change appends a rationale citing relation weights.
4. Authoritative Vault, Source, Workspace, or Framework writes happen only
   after explicit user confirmation. Private writes never imply a Palace Git
   action.
5. Evidence is immutable: quotes are never edited in place; corrections append
   clearly marked entries and preserve the original.
6. Full paper texts live only in Source Cache. Vault cards store locators and
   `source_dir`-relative pointers.
7. Workspace revisions are append-only siblings of evidence immutability:
   every confirmed save creates the next `sections/<section>/rNNN.md`, prior
   revisions are never rewritten, and a no-save interaction leaves the
   Workspace byte-identical. Palace never runs Git against the Workspace;
   auto drafts and interim reviews live only in Derived State. Project
   Materials feed writing but can never become Vault Claim evidence.

## Schema (field-complete templates in `knowledge_palace/templates/`)

- **concepts.md** — 7 axis sections, table `| Slug | Parents | Status | Aliases |
  Definition | Notes |`; comma-separated Parents = multi-parent DAG; controlled
  vocabulary (cards use canonical slugs only); deprecated rows name successors,
  never deleted.
- **Card filenames** — a card is `<slug>.md` inside its store directory
  (`papers/`, `gaps/`, `transfers/`, `styles/bank/`, `styles/profiles/`; gap and
  transfer slugs already carry their `gap-`/`transfer-` prefixes); briefs are
  `briefs/<YYYY-MM-DD>-<view>.md`; confirmed compact expansion-run records
  are `expansions/<run-id>.md` (template `expansion-run.md`).
- **paper card** (`templates/paper-card.md`) — slug `<firstauthor>-<year>-<titleword>`
  (grep INDEX for duplicates before assigning); frontmatter incl. `journal_if`,
  `citations`, `citations_date`, `weight` with its derivation persisted inline
  (e.g. `weight: high (citations 240 ≥ 100)`), `source` locator and `local`
  source_dir-relative pointer (full text never stored in the Vault),
  `read_depth` (full|skim) — the ingest confirmation validates that an
  external `source:` id is spec-shaped (DOI `10.<4–9 digits>/…` or an arXiv
  id) before it is persisted; malformed provider ids surface at the
  confirmation and are never written — 7 concept arrays — the `domain:`
  array always includes the domain-root slug so domain-filtered views stay
  grep-native — `gaps:` relations, optional `style_card`, and four optional
  reproducibility fields `code:`/`data:`/`compute:`/`code_usage:` (author-stated
  with anchors, `none-stated` when absent; `code_usage` is a
  dated display-only snapshot, never weight input). Body:
  Summary (may be Chinese) / Claims (verbatim quote + anchor `— §sec [¶para] /
  p.page`) / Limitations & gaps / Transfer notes (only if cross-domain or a
  transferable function).
  Paper→gap relations (5): `identifies | supports | partially_addresses |
  disputes | reframes`.
- **gap card** (`templates/gap-card.md`) — `type (theory|method|data|evaluation|
  generalization|physical|transfer)`, `status (open|partially-addressed|disputed|
  reframed|closed)`, `source_type (explicit_author|implicit_system)`, `concepts[]`
  (prefilter hooks), `related[]` (optional cross-gap analogy links, usually shared
  failure modes; justify in body). Body: one-sentence statement / Relations table
  (Paper | Relation | Weight | Claim/evidence | Anchor) / Status rationale
  (append-only) / Open subquestions.
- **transfer card** (`templates/transfer-card.md`) — `relation` enum (7):
  `similar_problem_pattern | transferable_method_function | shared_failure_mode |
  shared_validation_logic | prerequisite_or_enabler | analogy_only |
  spurious_relation` (the last two are report-and-drop, never stored);
  `a` (home-domain slug), `c` (foreign-domain slug), `bridges[]` (non-stopword),
  `status (candidate|monitor|pursuing|dropped)`, `gaps[]`, `papers[]`. Body:
  one-sentence hypothesis / Bridge evidence / Assumptions & risks / First
  validation step (one concrete experiment).
- **style bank card** (`templates/style-bank-entry.md`) — `slug/title/source
  (pointer)/venue/added/liked_aspects[]/user_note/profiles[]` + 7 dimension
  sections (argument-development, sentence-rhythm, assertion-hedging, lexicon,
  punctuation, structure-organization, results-presentation) + representative
  quotes.
- **style profile** (`templates/style-profile.md`) — `name (journal-<venue>|
  lang-<trait>)/type (journal|language)/alias/description/sources[]/updated` +
  rules table grouped D2 / D3 / Fix tone (`# | Rule | Support n/N | Maturity |
  Exemplar | Counter-example`) + Conflict log.
- **INDEX files** (`templates/papers-INDEX.md`, `templates/gaps-INDEX.md`) — flat
  tables for dedup and prefilter; papers INDEX carries IF / Cites / W columns.

## Multi-domain rules

- Stable skeleton = shared axes (pattern, function, failure-mode, generic
  metrics); variable layer = per-domain domain/task subtrees.
- Three connection forms between top-level domains, kept separate:
  1. **Structural** — shared abstract concepts (both domains' tasks hang under the
     same pattern/function row; grep-native).
  2. **Transfer** — transfer cards (evidence-backed, typed, directed edges with a
     validation plan; a↔c crossing domains is the inter-domain edge).
  3. **Analogy** — gap cards' optional `related:` field (cross-domain gaps sharing
     a failure mode), justified in the body.
- FORBIDDEN: inter-domain `Parents` edges. Between top-level domains there are
  only bridges, never hierarchy.
- `brief bridges` is a pure computed view: shared-concept intersection (grep both
  domains' cards' tags), transfer edges between the pair, cross-domain gap links;
  no arguments → full connection matrix (which domains are bridge-rich, which are
  isolated).

## Weight rules

Bands and qualitative rules live in `PALACE.md` and bind linker and analyst;
every weight-dependent verdict must cite the rule it applied. Key hard rules:
band = higher of IF/citations band; preprint/low-only can never close or
reverse a gap; "established" needs ≥2 independent teams incl. ≥1 high;
minority evidence is displayed, never drowned; no numeric weighting formula.

## Governance invariants

- Store decisions, compute counts (support, hub degree, triggers — grep live).
- INDEX-first prefilter; linker reads 5–15 candidate cards, never the full vault.
- Slugs: ASCII kebab-case English. Bodies English; Summary/notes may be Chinese.
- Subagents never write; no anchorless claims; gap status changes carry rationale;
  writes only after user confirmation; private writes never trigger Palace Git.
- Evidence immutable: corrections append, never overwrite.
- Palace Viewer export is read-only over the frozen GraphQueryPort and
  produces no authoritative write anywhere except the one user-confirmed
  output file, itself outside all four private roots.
