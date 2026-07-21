# KnowledgePalace — Agent Contract

Evidence-driven research knowledge OS with a public Framework and four private
storage roots. `CLAUDE.md` and `AGENTS.md` are identical mirrors and must be
updated together. The full protocol lives in the platform-neutral shared core
`knowledge_palace/` — `protocol/` (rules, commands, GraphQueryPort schema),
`agents/` (nine role contracts), `templates/`, and `tools/` (deterministic
stdlib Python). The runtime entries `.claude/skills/knowledge-palace/SKILL.md`
(Claude Code) and `.agents/skills/knowledge-palace/SKILL.md` (Codex, subagents
in `.codex/agents/`) are thin adapters and never duplicate protocol bodies.

## Triggers

Messages starting with `/palace` or natural-language equivalents route to the
knowledge-palace protocol. Command surface:

```
/palace ingest [<paths|dois>...]         # single or batch paper ingestion
/palace status                           # vault counts + consistency, computed live
/palace brief <onboard|map <concept>|gaps|ideas|transfers> [<domain>]
/palace brief bridges [<domain-a> <domain-b>]
/palace discover [<target>]              # cross-domain transfer scouting
/palace style <ingest|status|crystallize>
/palace domain <add <name>|list>
/palace govern                           # governance scan → proposals → confirmed edits
/palace audit [<card>...]                # auditor pass over the vault or given cards
/palace init <topic> [n]                 # bootstrap: topic search → candidates → batch ingest
/palace ask <question>                   # vault-grounded Q&A + expansion advice
/palace idea refine <text|file>          # critique + upgrade a user idea
/palace draft intro <topic>              # provenance-tagged introduction draft
/palace write <project> [<section>]      # section-wise Paper drafting (frozen brief)
/palace viewer export [<output-path>]    # one offline HTML file, local read-only graph browsing
```

## Storage and path boundary

The Framework root contains this contract, public policy, skills, agents,
and templates. Its local `.palace.toml` contains exactly four roots:
`vault_dir`, `state_dir`, `source_dir`, and `workspace_dir`.

- Resolve relative values against the directory containing `.palace.toml`,
  never against the shell CWD.
- The four resolved roots exist, are distinct, and lie outside the Framework
  worktree. Private-root Git topology is exclusively user-managed: whether a
  private root or its parent is a Git repository is invisible to Palace and
  never changes Palace behavior.
- `PALACE.md` is public static policy. Private domain and concept registries are
  `domains.md` and `concepts.md` in the configured Personal Vault.
- Card and manifest paths are Vault-relative unless the contract says otherwise.
  A paper card's `local` path is relative to `source_dir`.
- The orchestrator passes resolved absolute data, policy, and template paths to
  subagents. Subagents never infer a root from CWD and never scan outside the
  handed candidate set.

## Execution discipline

1. **Orchestrator role.** The main agent resolves the storage roots, runs
   INDEX-first grep prefilters, dispatches read-only subagents, aggregates their
   drafts, presents one packaged confirmation, and performs approved writes.
2. **INDEX-first prefilter.** Before dispatching palace-linker, select 5–15
   candidate cards from Vault INDEX files and `concepts.md`. Subagents never
   read the whole Vault.
3. **Store decisions, compute counts.** Support counts, hub degree, and
   governance triggers are computed live via grep, never cached as authority.
4. **Batch ingest.** Process 5–10 papers per batch with one merged confirmation;
   uncertain papers receive per-paper review.
5. **Language.** Artifacts, slugs, and card bodies are English; Summary and notes
   may be Chinese. Slugs are ASCII kebab-case.
6. **Git authority.** Palace may run Git only against the Public Framework.
   It never runs any Git command with a private root as CWD or target, including
   `init`, `add`, `commit`, `push`, or `remote`, even if the user later
   creates a repository there. Framework work forms at most one local commit per
   completed Goal and is never pushed automatically.

## Deterministic tools

Stdlib-only Python under `knowledge_palace/tools/` (3.9 floor; any new
dependency requires a named material-risk gate): `config_resolver` resolves
the four roots against the config file's directory, never the CWD; `doctor`
is read-only diagnostics — root resolvability/distinctness and both runtimes'
contract completeness, zero writes, zero network; `git_guard` pre-flights
every Palace Git invocation and refuses non-Framework CWDs/targets and
unauthorized push; `gqp_validator` enforces the GraphQueryPort contract
(`knowledge_palace/protocol/graph_query_port.schema.json`); `task_package`
builds the deterministic dispatch payload both runtimes share.

Metadata and impact live in `knowledge_palace/metadata/`:
`providers` (OpenAlex/Crossref/Semantic Scholar/arXiv over injected
transports), `cache` (Bibliographic Cache + rate limiting in Derived State),
`impact` (contextual ImpactSnapshot + classifier; bands only per Evaluation
Context, unknown stays unknown), and `refresh` — the ONLY network entry,
explicit-invocation-only and cache-first (`govern` never fetches). Card
updates leave refresh as proposal reports; weight changes need their own
migration gate.

Acquisition lives in `knowledge_palace/acquisition/`: `receipt`
(three-axis MaterialReceipt; Claim-eligible only when identity is verified
AND text is ready; mismatch quarantines), `providers` (local / read-only
Zotero / Open Access over injected transports; institutional access is a
disabled experimental stub), and `transaction` (the single Source Cache
write path — immutable temp+rename promotion inside the packaged
confirmation; rejection changes nothing). Staging and receipts are Derived
State; full text never enters the Vault.

The interaction layer lives in `knowledge_palace/interaction/`:
`session` (resumable InteractionSessions in Derived State; hybrid/external
are recorded user opt-ins), `coverage` (the CoverageReport schema —
sufficient answers, partial names its holes, insufficient fabricates
nothing and must carry a proposal; external material is session-local and
never Vault-eligible by validation), `proposal` (holes → a bounded,
confirmable ExpansionRun; rejection changes nothing), `prefilter`
(deterministic ≤15 id-only retrieval with corridor cross-domain reach —
the whole Vault never enters a prompt), `novelty` (per-project
NoveltyProfile dimensions; the 10-corridor/15-work/30-claim coarse-to-fine
pipeline; the IdeaAssessment schema — falsifiers and a minimal experiment
required, verdicts vault-relative and profile-bound, external statements
valid only under a recorded opt-in's scope and date), and
`project_source` (author references: Vault-Hit reuse or verified
session-local sources that never auto-ingest; the one-hop ≤20-candidate
external request record).

The Workspace layer lives in `knowledge_palace/workspace/`:
`project` (the `projects/<slug>/` skeleton + flat manifest, resolved
against `workspace_dir` only; current revision computed, never stored),
`material` (writing inputs schema-barred from Claim evidence), `brief`
(the frozen fingerprinted ProjectBrief — id-shaped evidence refs with
quotes AND anchors), `writing` (writer packages validated against the
frozen brief; two automatic review rounds then unresolved delivery; a
Results-kind section without user materials must be placeholder-only),
and `revision` (append-only `sections/<section>/rNNN.md`; the assembled
document is the reserved name `assembled`; no-save leaves the Workspace
byte-identical; Palace never runs Git there). Also included:
`requirements` (anchored solicitation rows, named coverage, the generic
fallback born compliance-unverifiable), `proposal` (aims/approach
alignment findings; budget/institutional/preliminary-result facts only
with registered User Material), and `export` (replayable pandoc plans —
CSL override > manifest > APA, collision-free `exports/` outputs,
canonical Markdown untouched; the runner is injected and live runs are
confirmation territory).

The Viewer lives in `knowledge_palace/viewer/`: `export`
(walks the frozen GraphQueryPort's five operations exclusively — never
a raw Vault scan, never Source Cache — into one canonical JSON payload;
`query_context`'s `children`/`edges` are single-page by the port's own
contract, so `truncated`/`total` are reported honestly rather than
implied complete; a stale index aborts the whole walk), `html_template`
(a hand-rolled, dependency-free HTML/CSS/JS shell — zero outbound
network calls from the emitted page), `cli` (the `/palace viewer
export` write path: one user-confirmed output file outside all four
private roots, written via temp+rename). Not a live server — no open
network port, no new dependency; a future served Viewer is a separate
Goal.

The semantic layer lives in `knowledge_palace/semantic/`:
`binding` (every NEW Claim binds ≥1 concrete Concept via the optional
`- C<n> [slug,…]:` bracket group — validated before the packaged
confirmation; historical claims stay valid until their migration packets),
`profiles` (StudyProfile views from claim references only; one role set per
work, no fact duplication), `corridors` (typed cross-domain prefilter over
the Graph Index payload, ≤15 deterministic, id-only descriptors — an
internal helper, not a GraphQueryPort operation).

Expansion lives in `knowledge_palace/expansion/`: `candidates`
(one Candidate per Work identity, Discovery Occurrences, Scope-bound
decisions — no global blacklist by construction), `run` (state machine +
idempotent checkpoints under `state/expansion/`), `engine` (bounded
frontier: depth ≤2, budget = unique verified non-Vault candidates,
metadata-only never expands, Vault Hits verify edges only), `record` (the
compact run record — text only; the Vault write is packaged-confirmation +
gate territory).

The Graph Index lives in `knowledge_palace/graph/`: `identity`
parses cards and registries into Work/Manifestation/Claim identities (exact
external-id collisions and fuzzy titles surface as user confirmations, never
silent merges), `builder` writes the rebuildable canonical JSON snapshot
under `<state_dir>/graph-index/` (Vault read-only, always), and `port` is the
production GraphQueryPort — five read-only operations, snapshot on every
response, typed `stale_index` refusal when the Vault fingerprint no longer
matches. `doctor` reports the index as absent-rebuildable, fresh, or stale.

## Write invariants

1. Subagents never write files; the main agent performs every approved write.
2. No Claim enters a card without a verbatim evidence anchor
   (`— §<section> [¶<para>] / p.<page>`).
3. Every gap status change appends a rationale citing relation weights.
4. Authoritative Vault, Source, Workspace, or Framework writes happen only after
   explicit user confirmation. Private writes never imply a Palace Git action.
5. Evidence is immutable: quotes are never edited in place; corrections append
   clearly marked entries and preserve the original.
6. Full paper texts live only in Source Cache. Vault cards store locators and
   `source_dir`-relative pointers.

## Weight rules

- Weight band is the higher of the age-tiered citations band and IF band.
- Papers younger than two years are provisional; peer-reviewed papers younger
  than three years take the public policy's medium floor.
- Preprint/low-only evidence can never close or reverse a gap.
- "Established" requires at least two independent sources, including one
  high-weight source; consistent low-weight evidence is at most emerging
  consensus.
- Weights are qualitative, minority evidence is shown alongside majority
  evidence, and no numeric weighting formula is used.

## Subagents

All subagents are read-only — file reading, content search, and listing only
(Claude Code restricts tools to Read/Grep/Glob; Codex uses a read-only
sandbox). The platform-neutral role contracts live in
`knowledge_palace/agents/`; `.claude/agents/*.md` and `.codex/agents/*.toml`
are thin adapters. Every dispatch is a task package built by
`knowledge_palace/tools/task_package.py` — one code path for both runtimes.

| Agent | Role |
|---|---|
| palace-extractor | full text + metadata → anchored paper-card draft |
| palace-linker | draft + prefiltered candidates → concepts and gap relations |
| palace-scout | target + shared axes → evidence-backed transfer candidates |
| palace-auditor | adversarial evidence, schema, and provenance review |
| palace-analyst | briefs, ask answers, idea critiques, and intro drafts |
| palace-stylist | style feature cards and crystallized profiles |
| palace-expansion-reviewer | scope-specific expansion candidate decisions |
| palace-writer | genre-shaped draft/revise/assemble from frozen evidence |
| palace-reviewer | scholarly quality and genre-requirement review |

In runtimes without native subagent support, execute each contract in a separate
read-only context and return its draft to the orchestrator.

External capabilities are called but never modified: academic-search providers
for metadata and citations, plus downloader/reader providers for full text. If
they are unavailable, query OpenAlex metadata and ask the user for a local
full-text path.
