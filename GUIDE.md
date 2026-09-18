> Current task routes: [Commands](knowledge_palace/protocol/COMMANDS.md). Selected literature is ingested; reading updates its card. `write` and `polish` share manuscript analysis; `feasibility` assesses a design. Direct manuscript tasks need no new project.

# KnowledgePalace Guide — Architecture and Usage

English | [中文](GUIDE.zh-CN.md)

This guide explains how KnowledgePalace is built, where every kind of data
lives, and how to use each command. For hands-on walkthroughs see
[TUTORIAL.md](TUTORIAL.md); for the binding protocol text see
`knowledge_palace/protocol/`; for term definitions see
[CONTEXT.md](CONTEXT.md).

## 1. The big picture

KnowledgePalace separates one **public Framework** (this Git repository) from
**four private roots** (your data, outside the repo):

```
┌─ Public Framework (this repo, the only Palace-managed Git boundary) ─┐
│  protocol · role contracts · templates · deterministic tools         │
│  runtime adapters (.claude/, .codex/, .agents/)                      │
└──────────────────────────────┬───────────────────────────────────────┘
                        .palace.toml (local, git-ignored)
              resolves four roots relative to the config file
                               │
   ┌───────────────┬───────────┴──────┬───────────────────┐
   ▼               ▼                  ▼                   ▼
 vault_dir      state_dir         source_dir         workspace_dir
 Personal       Derived State     Source Cache       Research
 Vault          (rebuildable,     (immutable         Workspace
 (confirmed     deletable)        full texts)        (writing
 knowledge)                                          projects)
```

Three kinds of actor operate on this layout:

1. **The main agent** — the LLM you talk to (Claude Code or Codex). It reads
   the requested workflow under `knowledge_palace/workflows/`, resolves the
   roots, reads bounded evidence, may delegate reading or drafting to a
   specialist, audits decisive evidence, and performs every authorized write
   itself.
2. **Nine optional read-only specialists** — extractor, linker, scout,
   auditor, analyst, stylist, expansion-reviewer, writer, reviewer. They are
   called when useful, never as a fixed sequence; they only read, grep and
   list files, receive resolved paths and a bounded reading scope, and never
   write. Their platform-neutral contracts live in `knowledge_palace/agents/`;
   `.claude/agents/` and `.codex/agents/` are thin adapters.
3. **Deterministic tools** — stdlib-only Python under `knowledge_palace/`.
   No LLM in the loop: config resolution, identity matching, paper saving,
   graph indexing, query serving, refresh, expansion bookkeeping, workspace
   mechanics and the viewer export are plain, testable code
   (`python3 -m pytest knowledge_palace/tests`).

Core invariants (the full list is in `knowledge_palace/protocol/PROTOCOL.md`):

- No Claim without a **verbatim quote + anchor**; the quote is immutable
  (corrections append, never overwrite). A quote that turns out not to be this
  paper's is retracted in place, not edited away.
- **Store decisions, compute counts** — support counts, hub degree, and
  governance triggers are grep-computed live, never cached as authority.
- Authoritative writes happen **only after explicit user confirmation**;
  rejecting a confirmation leaves every root byte-identical.
- Palace runs Git **only against the Framework** — never in or against a
  private root, even if you make one a Git repository yourself.
- The network is used only inside a task that needs it: collection,
  acquisition and requested external research within their scope, and
  `refresh` for bibliographic data. `govern` never fetches.

## 2. Repository layout

```
KnowledgePalace/
├── CLAUDE.md / AGENTS.md      # identical mirrors: the main-agent contract
├── PALACE.md                  # public policy: axes, weight bands, thresholds, triggers
├── CONTEXT.md                 # ubiquitous language — every term defined
├── README.md / GUIDE.md / TUTORIAL.md
├── .palace.example.toml       # template for your local .palace.toml (git-ignored)
├── .claude/                   # Claude Code runtime adapter
│   ├── skills/palace/SKILL.md    # entry point: routes /palace here
│   └── agents/palace-*.md                  # 9 subagent adapters (Read/Grep/Glob only)
├── .agents/ + .codex/         # Codex runtime adapter (same shape)
└── knowledge_palace/          # the platform-neutral shared core
    ├── protocol/              # PROTOCOL.md · COMMANDS.md · EVIDENCE.md · GRAPH_QUERY_PORT.md
    ├── workflows/             # collection · ingest · discussion · manuscript-analysis · writing · feasibility
    ├── agents/                # 9 platform-neutral role contracts (optional specialists)
    ├── templates/             # paper/gap/transfer/style/INDEX/expansion-run/project-research templates
    ├── tools/                 # config_resolver
    ├── graph/                 # Graph Index: identity · builder · port (GraphQueryPort)
    ├── metadata/              # providers · cache · impact · refresh (bibliographic data)
    ├── acquisition/           # receipt · providers · transaction (full-text acquisition, save_paper)
    ├── expansion/             # candidates · run · engine · record (bounded expansion)
    ├── semantic/              # binding · evidence_helpers · update_helpers · corridors
    ├── interaction/           # prefilter · research · research_helpers · novelty · project_source
    ├── workspace/             # project · material · brief · writing · revision · research_helpers
    └── viewer/                # export · html_template · cli · obsidian (offline views)
```

Rule of thumb: `protocol/` says *what must hold*, `workflows/` says *how a
task runs*, `agents/` says *what a specialist may draft*, the Python packages
*implement the deterministic parts*, and the runtime adapters only *route* —
they never duplicate protocol text.

## 3. The four private roots

Configured in `.palace.toml` (four keys, resolved **relative to the config
file**, never the shell CWD). All four must exist, be distinct, and lie
outside the Framework worktree. Whether you version-control them is entirely
your business — Palace never inspects or touches private Git.

### 3.1 `vault_dir` — Personal Vault (the source of truth)

Human-readable markdown; everything here passed a confirmation.

```
vault/
├── domains.md                 # domain registry (table)
├── concepts.md                # concept registry: 7 axis sections, controlled vocabulary
├── papers/    INDEX.md + <firstauthor>-<year>-<titleword>.md
├── gaps/      INDEX.md + gap-<slug>.md
├── transfers/ transfer-<slug>.md
├── briefs/    <YYYY-MM-DD>-<view>.md          # dated, disposable views — never evidence
├── styles/    bank/<slug>.md + profiles/<journal-*|lang-*>.md
├── expansions/<run-id>.md                     # compact expansion-run records
└── governance/decisions.md                    # append-only governance log
```

- **Paper cards** hold frontmatter (metadata, `citations` + `citations_date`,
  `weight` with its derivation persisted inline, 7 concept-axis arrays,
  gap relations, optional reproducibility fields `code/data/compute/
  code_usage`) and a body of Summary / Claims (verbatim + anchor) /
  Limitations & gaps / Transfer notes. The `local:` pointer is
  `source_dir`-relative — full text never lives in the Vault.
- **Gap cards** hold a typed status (`open / partially-addressed / disputed /
  reframed / closed`), a relations table (Paper | Relation | Weight |
  Evidence | Anchor), and an append-only status rationale.
- **INDEX.md** files are flat tables used for dedup and prefiltering —
  subagents read INDEX rows plus 5–15 candidate cards, never the whole vault.

### 3.2 `state_dir` — Derived State (rebuildable, deletable)

Deleting anything here loses no knowledge:

```
state/
├── graph-index/       # canonical JSON snapshot of the Vault Graph (KP-03)
├── expansion/         # candidate pools + resumable run checkpoints
├── acquisition/       # staged downloads + MaterialReceipts
├── interaction/       # resumable Ask/Idea sessions
├── impact/            # ImpactSnapshots (dated provider observations)
└── workspace-drafts/  # unconfirmed drafts + interim reviews
```

### 3.3 `source_dir` — Source Cache (immutable full texts)

`fulltext/<slug>.<ext>` snapshots, promoted only through the confirmed
acquisition transaction (temp+rename; identical re-promotion is a no-op, a
differing hash is refused). Vault cards point here; nothing here is ever
edited.

### 3.4 `workspace_dir` — Research Workspace (writing projects)

```
workspace/projects/<slug>/
├── project.yaml       # flat manifest: kind, audience, venue, language, citation_style, …
├── research.md        # research notes: questions, definitions, decisions, observations
├── materials/         # your drafts, data, figures, solicitations, reviewer comments
├── sources/           # project bibliography sources (Vault-first resolution)
├── requirements/      # solicitation notes for proposals
├── outline/           # brief.json (evidence contract) · manuscript-analysis.md
├── sections/<name>/rNNN.md   # append-only revisions; `assembled` is reserved
├── reviews/           # confirmed review records
├── bibliography/
└── exports/           # exported documents; never overwrite anything
```

Project materials feed writing but are schema-barred from ever becoming
Vault Claim evidence.

## 4. The data model

### 4.1 Identity: Work → Manifestation → Claim

A **Work** is one intellectual contribution regardless of venue or version; a
**Manifestation** is one published version (arXiv v2, journal VoR); a
**Claim** is an immutable, evidence-anchored statement extracted from a
specific Manifestation. Identity resolution (doi > openalex > arxiv > title
hash) prevents duplicate Works; exact external-id collisions and fuzzy title
matches surface as user confirmations, never silent merges.

### 4.2 The seven concept axes

`domain` and `task` are per-domain subtrees; `pattern`, `function`,
`method`, `metric`, `failure-mode` are shared across domains. Cross-domain
connections exist **only** as shared-axis co-tagging, transfer cards, or gap
`related:` links — never as `Parents` edges between domain subtrees.
`concepts.md` is a controlled vocabulary: cards use canonical slugs only,
new concepts start as `candidate` and are promoted at ≥3 genuine-use
supporters with evidence from distinct data or analyses.

### 4.3 Weights

A paper's bibliographic band is the **higher** of its IF band and its
age-tiered citations band (`PALACE.md` has the exact tables). It is displayed
as context. Gap judgments cite Claims, study design, scope and shared data or
analysis dependencies. Publication type, venue and author overlap do not decide
the conclusion. Provisional metadata is refreshed through explicit
`/palace refresh`; governance reports it without network access.

Argument and Conditions tables record the paper's reasoning and study setting.
Claim-level Evidence relations distinguish author responses from retrospective
comparisons. Synthesis entries name the Claims and Gaps they depend on; index
maintenance emits affected judgments for review. `/palace brief progress <topic>`
uses the same evidence context as `ask`, `brief gaps` and `brief ideas`.
See [EVIDENCE.md](knowledge_palace/protocol/EVIDENCE.md) for the table contract.

### 4.4 Source boundaries

Every brief, answer or draft keeps four kinds of statement apart:

| Kind | Meaning |
|---|---|
| `[C:slug]` | a paper states it — the quote + anchor is in the cited card |
| `[S]` | synthesis or inference; it names the cards it rests on (one card can suffice) |
| `[H]` | hypothesis pending validation; a Transfer card is cited when one exists |
| background / user | general explanation or your own observation, labeled as such |

The auditor, when asked, checks that a `[C]` has a verifiable anchor and that a
synthesis or hypothesis is not dressed up as a paper statement.

### 4.5 The Graph Index and GraphQueryPort

`knowledge_palace/graph/builder.py` projects the Vault into a canonical JSON
snapshot under `<state_dir>/graph-index/` (rebuildable; the Vault is opened
read-only). `graph/port.py` serves five read-only operations over it —
`list_hierarchies`, `list_levels`, `query_level`, `query_context`,
`get_content` — every response stamped with the snapshot. Callers run
`builder.ensure_index` first, which rebuilds the snapshot whenever the Vault
fingerprint changed. The viewer, prefilters, and novelty pipeline all go
through this port; nothing re-scans the raw Vault.

## 5. Command reference

Full flow definitions: `knowledge_palace/protocol/COMMANDS.md`. Summary of
what each command is *for* and what it *writes*:

### Intake

| Command | What happens | Writes (after confirmation) |
|---|---|---|
| `/palace ingest [<paths\|dois\|slugs>...]` | match identity against the vault (a hit reuses the card) → acquire the best available material → read to the requested depth → card draft with verbatim Claims, Argument/Conditions, optional Analysis evidence and dated Reading notes → `save_paper` (refuses duplicates, keeps old Claims) → `ensure_index` once per batch. Abstract-only material yields a card that says so. | paper cards, INDEX rows, synthesis update items |
| `/palace init <topic> [n]` | build or extend a topic collection: domain add only if the domain is new → search via available providers or browsing → one bounded candidate selection → every selected paper is ingested | everything ingest writes |
| `/palace expand <target> [--depth 1\|2] [--max-new N]` | follow references/related work from papers, a question or an evidence hole; scope-bound select/defer/reject; checkpoints resume without duplicates; selected papers are ingested | run record + everything ingest writes |
| `/palace domain add <name>` · `list` | register a domain and its initial concepts (shared axes reused first) · list domains | `domains.md` row + concept rows |
| `/palace refresh <impact\|citations\|metadata> [<scope>]` | bibliographic refresh, cache-first (`--live` for real fetches) | Derived-State snapshots; card updates come back as proposals |

### Consultation (no-write computed views unless you ask to save)

| Command | What you get |
|---|---|
| `/palace status` | live counts (papers/gaps/transfers/briefs/styles/concepts/domains) + consistency checks (INDEX↔file parity, orphan tags) |
| `/palace brief onboard [<domain>]` | concept-tree map, core vocabulary, a 5–8 paper reading path |
| `/palace brief map <concept>` | chronological method timeline, established conclusions with context, disputes side by side |
| `/palace brief progress <topic>` | question evolution, claimed advances, disputes, remaining subquestions and evidence coverage |
| `/palace brief gaps [<domain>]` | open/disputed gaps ranked qualitatively: who tried, why unresolved, open subquestions |
| `/palace brief ideas [<domain>]` | opportunity cards: gap × transfer → hypothesis, grounds, risks, minimal validation experiment |
| `/palace brief transfers [<domain>]` | the transfer radar by status |
| `/palace brief bridges [<a> <b>]` | domain-pair connection report; no args → full cross-domain matrix |
| `/palace ask <question>` | explanation, comparison or continuing discussion (see §6); library statements cite Claims, background and hypotheses are labeled; collects and ingests literature when that would change the answer, then resumes |
| `/palace research <project>` | project research notes: questions, working definitions, decisions, constraints, material-linked observations; updated when you ask to keep a discussion |
| `/palace updates` · `updates resolve <node> <entry>` | judgments whose declared evidence changed at index maintenance · record your review (retain / revise / withdraw) |
| `/palace feasibility <idea\|file\|project>` | 可执行 / 满足明确条件后可执行 / 需调整方案 / 目前无法判断, with decisive conditions and the smallest useful pilot; scientific identifiability separated from operational feasibility |
| `/palace discover [<target>]` | ≤5 transfer candidates, each with ≥2 non-stopword bridges, typed relation, two-sided evidence, one validation experiment |
| `/palace idea refine <text\|file>` | IdeaAssessment: evidence for/against/unknown, closest prior work, falsifiers + minimal experiment; novelty vault-relative on your confirmed profile dimensions |

Briefs, saved asks and idea assessments land in `briefs/<date>-….md` after your
confirmation; ask for an auditor pass when you want an independent check. They
are dated, disposable **views** — they can cite sources but can never serve as
evidence themselves. Discussion outcomes you want to keep go into the project's
`research.md`.

### Writing

| Command | What happens |
|---|---|
| `/palace write <project\|materials> [<section>]` | manuscript analysis first (reused when still valid) → argument and paragraph roles → draft from selected evidence and your materials → one focused review, at most two automatic revisions, unresolved findings reported → append-only `rNNN.md` on confirmation. Direct materials need no project. Proposals use the same route with the solicitation as a registered material. A Results section without your data is placeholder-only. |
| `/palace polish <text\|file\|project>` | manuscript analysis first → decide whether the issue is wording, paragraph logic or the scientific claim → revise only the requested passage → check numbers, units, terms, citations, claim strength against the original. Substantive restructuring belongs to `write`. A scientific problem is reported, never polished over. |
| `/palace draft intro <topic>` | `write` with section = introduction |
| `/palace style ingest\|status\|crystallize` | 7-dimension feature cards from papers whose writing you liked (`liked_aspects` come from you, never guessed) → dual-axis profiles (`journal-<venue>` × `lang-<trait>`); rules become `stable` at support ≥3 with no open conflicts |

### Maintenance

| Command | What happens |
|---|---|
| `/palace govern` | grep-computed trigger scan (concept promotions, provisional re-derivations, recurring unregistered terms, orphan tags, deprecated-slug migrations) → proposals each with a `grep -l` impact list → confirmed edits → dated append-only Governance Decision |
| `/palace audit [<card>...]` | adversarial auditor pass: verbatim anchor checks, orphan tags, `source_type` correctness, `[C]/[S]/[H]` boundary violations. Report-only; fixes go through the normal confirm-then-write path |
| `/palace viewer export [<path>]` | deterministic build (no LLM): walks the GraphQueryPort into one self-contained offline HTML file, written temp+rename to a path **outside** all four roots (default `./palace-viewer.html`) |
| `/palace wiki export [<dir>]` | regenerate the marked Obsidian hub pages; user notes and original cards stay authoritative |

## 6. How Ask answers

`/palace ask` follows `knowledge_palace/workflows/discussion.md`:

1. It starts from your question, your definitions, prior project decisions and
   any material you supplied; nothing requires a Gap or Transfer card first.
2. It chooses what the question needs: background explanation, paper evidence,
   a cross-paper comparison, a tentative explanation or a research decision.
3. For library evidence it runs
   `python3 -m knowledge_palace.interaction.research ask "<topic>" --json`,
   which returns a bounded context (≤15 candidates, Claims, relations,
   current syntheses, pending updates); the whole Vault never enters a prompt.
   Decisive Claims are read in their source context.
4. Library-backed sentences cite Claims; background explanation, hypotheses and
   your observations are labeled. Missing coverage is stated, not fabricated,
   and never blocks a clearly labeled explanation.
5. When more literature would change the answer and the request allows it,
   Palace runs `init`/`expand`, ingests what you select, and continues the same
   question with the new Claims. On "keep this", the working definitions,
   decisions, alternatives and next action go into the project's `research.md`.

## 7. Deterministic tools (CLI)

All stdlib-only, runnable from the Framework root:

```bash
python3 -m knowledge_palace.tools.config_resolver     # resolve + print the four roots
python3 -m knowledge_palace.graph.builder --rebuild   # (re)build the Graph Index snapshot
python3 -m knowledge_palace.graph.builder --check     # is the index fresh / stale / absent?
python3 -m knowledge_palace.metadata.refresh --kind citations --scope all       # cache-only; add --live for network
python3 -m knowledge_palace.viewer.cli [output.html] [--config <toml>]          # viewer export build step
python3 -m knowledge_palace.viewer.obsidian [dir] [--config <toml>]             # Obsidian hub export
python3 -m knowledge_palace.interaction.research ask "<topic>" --json           # bounded research context
python3 -m knowledge_palace.interaction.research progress "<topic>"            # progress view
python3 -m knowledge_palace.interaction.research updates                        # judgments awaiting review
```

Run the test suite:

```bash
python3 -m pytest knowledge_palace/tests -q   # a few seconds
```

## 8. The safety model, condensed

| Boundary | Rule |
|---|---|
| Writes | subagents never write; orchestrator writes only after one packaged confirmation; rejection = byte-identical roots |
| Evidence | verbatim + anchored; quote immutable, corrections append, wrong-source quotes retract in place |
| Network | collection, acquisition, requested external research and `refresh`, each within its task; `govern` never fetches; the viewer page makes zero outbound calls |
| Git | all Git writes are yours; Palace never stages, commits or pushes and never targets a private root |
| Context | bounded research context (≤15 candidates); 5–15 candidate cards per delegation; ≤10/15/30 novelty pipeline stages — the whole Vault never enters a prompt |
| Full text | Source Cache only; Vault stores pointers; Workspace materials never become Claim evidence |

## 9. Extending

- **New domain**: `/palace domain add` — no code, just registry + subtree.
- **New runtime**: add a thin adapter that routes to
  `knowledge_palace/protocol/` and `workflows/` and binds the nine role
  contracts; adapters never duplicate protocol bodies.
- **New dependency**: there are none, deliberately; adding one requires a
  named material-risk gate (see `CLAUDE.md`).
