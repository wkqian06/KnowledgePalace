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

1. **The orchestrator** — the main LLM agent (Claude Code or Codex). It
   resolves the roots, runs INDEX-first grep prefilters, dispatches
   subagents, aggregates their drafts, presents **one packaged
   confirmation**, and performs every approved write itself.
2. **Nine read-only subagents** — extractor, linker, scout, auditor,
   analyst, stylist, expansion-reviewer, writer, reviewer. They can only
   read, grep, and list files; they never write and never scan outside the
   candidate set handed to them. Their platform-neutral contracts live in
   `knowledge_palace/agents/`; `.claude/agents/` and `.codex/agents/` are
   thin adapters.
3. **Deterministic tools** — stdlib-only Python under `knowledge_palace/`.
   No LLM in the loop: config resolution, diagnostics, graph indexing,
   query serving, refresh, expansion bookkeeping, workspace mechanics, and
   the viewer export are all plain, testable code (337 unit tests).

Core invariants (the full list is in `knowledge_palace/protocol/PROTOCOL.md`):

- No Claim without a **verbatim quote + anchor**; evidence is immutable
  (corrections append, never overwrite).
- **Store decisions, compute counts** — support counts, hub degree, and
  governance triggers are grep-computed live, never cached as authority.
- Authoritative writes happen **only after explicit user confirmation**;
  rejecting a confirmation leaves every root byte-identical.
- Palace runs Git **only against the Framework** — never in or against a
  private root, even if you make one a Git repository yourself.
- The network is touched **only** by `/palace refresh --live` (and live
  acquisition inside an ingest you confirmed). Everything else is offline.

## 2. Repository layout

```
KnowledgePalace/
├── CLAUDE.md / AGENTS.md      # identical mirrors: the main-agent contract
├── PALACE.md                  # public policy: axes, weight bands, thresholds, triggers
├── CONTEXT.md                 # ubiquitous language — every term defined
├── README.md / GUIDE.md / TUTORIAL.md
├── .palace.example.toml       # template for your local .palace.toml (git-ignored)
├── .claude/                   # Claude Code runtime adapter
│   ├── skills/knowledge-palace/SKILL.md    # entry point: routes /palace here
│   └── agents/palace-*.md                  # 9 subagent adapters (Read/Grep/Glob only)
├── .agents/ + .codex/         # Codex runtime adapter (same shape)
└── knowledge_palace/          # the platform-neutral shared core
    ├── protocol/              # PROTOCOL.md · COMMANDS.md · GRAPH_QUERY_PORT.md + schema
    ├── agents/                # 9 platform-neutral role contracts
    ├── templates/             # paper/gap/transfer/style/INDEX/expansion-run templates
    ├── tools/                 # config_resolver · doctor · git_guard · gqp_validator · task_package
    ├── graph/                 # Graph Index: identity · builder · port (GraphQueryPort)
    ├── metadata/              # providers · cache · impact · refresh (the ONLY network entry)
    ├── acquisition/           # receipt · providers · transaction (full-text acquisition)
    ├── expansion/             # candidates · run · engine · record (bounded expansion)
    ├── semantic/              # binding · profiles · corridors (claim↔concept layer)
    ├── interaction/           # session · coverage · proposal · prefilter · novelty · project_source
    ├── workspace/             # project · material · brief · writing · revision · requirements · proposal · export
    └── viewer/                # export · html_template · cli (offline HTML viewer)
```

Rule of thumb: `protocol/` says *what must happen*, `agents/` says *who
drafts it*, the Python packages *implement the deterministic parts*, and the
runtime adapters only *route* — they never duplicate protocol text.

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
├── materials/         # your drafts, data, figures, solicitations, reviewer comments
├── sources/           # project bibliography sources (Vault-first resolution)
├── requirements/      # anchored Requirements Matrix (proposals)
├── outline/           # frozen, fingerprinted ProjectBriefs
├── sections/<name>/rNNN.md   # append-only revisions; `assembled` is reserved
├── reviews/           # confirmed review records
├── bibliography/
└── exports/           # pandoc outputs — collision-free, never overwrite anything
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
supporters from ≥2 independent author clusters.

### 4.3 Weights

A paper's band is the **higher** of its IF band and its age-tiered citations
band (`PALACE.md` has the exact tables). The rules that matter downstream:

- Preprint/low-only evidence can never close or reverse a gap.
- "Established" needs ≥2 independent sources (author-disjoint, one-hop
  co-authorship check) including ≥1 high-weight.
- Papers <2 years old are provisional and re-derived at every `govern`.
- Weights stay qualitative; minority evidence is always displayed; there is
  deliberately no numeric scoring formula.

### 4.4 Provenance tags

Every sentence in every brief, ask answer, or intro draft carries exactly one:

| Tag | Meaning |
|---|---|
| `[C:slug]` | a paper states it — the claim + anchor is in the cited card |
| `[S]` | system-level synthesis across cards |
| `[H:slug]` | hypothesis pending validation (all transfer references) |

The auditor enforces the boundary: a `[C]` without a verifiable anchor or an
`[S]` smuggling a factual claim is a FAIL finding.

### 4.5 The Graph Index and GraphQueryPort

`knowledge_palace/graph/builder.py` projects the Vault into a canonical JSON
snapshot under `<state_dir>/graph-index/` (rebuildable; the Vault is opened
read-only). `graph/port.py` serves five read-only operations over it —
`list_hierarchies`, `list_levels`, `query_level`, `query_context`,
`get_content` — every response stamped with the snapshot; if the Vault
changed since the snapshot, queries get a typed `stale_index` refusal
instead of stale data. The viewer, prefilters, and novelty pipeline all go
through this port; nothing re-scans the raw Vault.

## 5. Command reference

Full flow definitions: `knowledge_palace/protocol/COMMANDS.md`. Summary of
what each command is *for* and what it *writes*:

### Intake

| Command | What happens | Writes (after confirmation) |
|---|---|---|
| `/palace ingest [<paths\|dois>...]` | fetch text+metadata → dedup gate → extractor draft → grep prefilter → linker alignment → one packaged confirmation. Batches of 5–10 get one merged confirmation; uncertain papers get per-paper review. Duplicate hits offer skip / deepen / correct. | paper cards, INDEX rows, registry candidates, gap backflow |
| `/palace init <topic> [n]` | bootstrap: domain add if needed → topic search (~n candidates, default 50, mix policy: ≥20% classics, 2–4 reviews, ≥25% frontier) → **one** candidate table you circle once → batch ingest | everything ingest writes |
| `/palace domain add <name>` | 1–2 review papers seed a concept subtree; shared axes are reused first | `domains.md` row + concept rows |
| `/palace expand <work\|doi> [--scope ..] [--depth 1\|2] [--max-new N]` | bounded citation traversal; scope-bound select/defer/reject (auto via palace-expansion-reviewer, or `--review manual`); checkpoints resume without duplicates | compact run record; selected candidates flow into normal ingest |
| `/palace refresh <impact\|citations\|metadata> [<scope>]` | **the only network entry**, explicit-invocation-only, cache-first (`--live` for real fetches) | Derived-State snapshots; card updates come back as proposals |

### Consultation (no-write computed views unless you ask to save)

| Command | What you get |
|---|---|
| `/palace status` | live counts (papers/gaps/transfers/briefs/styles/concepts/domains) + consistency checks (INDEX↔file parity, orphan tags) |
| `/palace brief onboard [<domain>]` | concept-tree map, core vocabulary, a 5–8 paper reading path |
| `/palace brief map <concept>` | chronological method timeline, established conclusions with weights, disputes side by side |
| `/palace brief gaps [<domain>]` | open/disputed gaps ranked qualitatively: who tried, why unresolved, open subquestions |
| `/palace brief ideas [<domain>]` | opportunity cards: gap × transfer → hypothesis, grounds, risks, minimal validation experiment |
| `/palace brief transfers [<domain>]` | the transfer radar by status |
| `/palace brief bridges [<a> <b>]` | domain-pair connection report; no args → full cross-domain matrix |
| `/palace ask <question>` | coverage-gated answer (see §6); `sufficient` answers, `partial` names holes, `insufficient` proposes expansion — never fabricates |
| `/palace discover [<target>]` | ≤5 transfer candidates, each with ≥2 non-stopword bridges, typed relation, two-sided evidence, one validation experiment |
| `/palace idea refine <text\|file>` | IdeaAssessment: evidence for/against/unknown, closest prior work, falsifiers + minimal experiment; novelty vault-relative on your confirmed profile dimensions |
| `/palace draft intro <topic>` | provenance-tagged introduction skeleton (coverage-checked; only covered aspects are drafted) |

Briefs, saved asks, idea assessments, and intro drafts land in
`briefs/<date>-….md` after an auditor pass and your confirmation. They are
dated, disposable **views** — they can cite sources but can never serve as
evidence themselves.

### Writing

| Command | What happens |
|---|---|
| `/palace write <project> [<section>]` | create/open a Workspace project → register materials and sources → freeze a fingerprinted ProjectBrief → per-section writer/reviewer loop (≤2 automatic rounds, then auditor; unresolved findings are delivered, never looped away) → one confirmation per save → append-only `rNNN.md`. Proposals add the anchored Requirements Matrix, aims↔approach alignment, and user-fact validation (budget/institutional/preliminary facts require registered materials). The export step builds a replayable pandoc plan (CSL override > manifest > APA); outputs never overwrite anything. |
| `/palace style ingest\|status\|crystallize` | 7-dimension feature cards from papers whose writing you liked (`liked_aspects` come from you, never guessed) → dual-axis profiles (`journal-<venue>` × `lang-<trait>`); rules become `stable` at support ≥3 with no open conflicts |

### Maintenance

| Command | What happens |
|---|---|
| `/palace govern` | grep-computed trigger scan (concept promotions, provisional re-derivations, recurring unregistered terms, orphan tags, deprecated-slug migrations) → proposals each with a `grep -l` impact list → confirmed edits → dated append-only Governance Decision |
| `/palace audit [<card>...]` | adversarial auditor pass: verbatim anchor checks, orphan tags, `source_type` correctness, `[C]/[S]/[H]` boundary violations. Report-only; fixes go through the normal confirm-then-write path |
| `/palace viewer export [<path>]` | deterministic build (no LLM): walks the frozen GraphQueryPort into one self-contained offline HTML file, written temp+rename to a path **outside** all four roots (default `./palace-viewer.html`) |

## 6. How Ask decides what it may say

`/palace ask` is gated by **coverage**, not by domain membership:

1. The question is decomposed into subquestions inside a resumable
   InteractionSession (Derived State).
2. A deterministic prefilter selects ≤15 id-only candidates from the Graph
   Index (typed corridors reach cross-domain material); the whole Vault
   never enters a prompt.
3. The analyst drills candidates through the GraphQueryPort and returns a
   CoverageReport: `sufficient` | `partial` | `insufficient` per
   subquestion, with id-shaped evidence.
4. Sufficient → a fully tagged answer. Partial → only the covered part is
   answered and every hole is named. Insufficient → **no answer is
   fabricated**; you get a bounded ExpansionProposal (seeds/queries, depth
   ≤2, budget ≤50) instead. Accepting it runs a normal `/palace expand`;
   afterwards the same session resumes and recomputes coverage.
5. `hybrid`/`external` modes are explicit opt-ins recorded in the session;
   external material stays session-local and is schema-barred from the
   Vault.

## 7. Deterministic tools (CLI)

All stdlib-only, runnable from the Framework root:

```bash
python3 -m knowledge_palace.tools.config_resolver     # resolve + print the four roots
python3 -m knowledge_palace.tools.doctor              # read-only diagnostics (roots, contracts, index, sources)
python3 -m knowledge_palace.graph.builder --rebuild   # (re)build the Graph Index snapshot
python3 -m knowledge_palace.graph.builder --check     # is the index fresh / stale / absent?
python3 -m knowledge_palace.tools.git_guard -- <git args>   # pre-flight any Palace Git command
python3 -m knowledge_palace.tools.task_package --fixture <input> --role <role>  # build a dispatch payload
python3 -m knowledge_palace.tools.gqp_validator <payload.json>  # validate a GraphQueryPort payload
python3 -m knowledge_palace.metadata.refresh --kind citations --scope all       # cache-only; add --live for network
python3 -m knowledge_palace.viewer.cli [output.html] [--config <toml>]          # viewer export build step
```

Run the test suite:

```bash
python3 -m unittest discover -s knowledge_palace/tests -t .   # 337 tests, a few seconds
```

## 8. The safety model, condensed

| Boundary | Rule |
|---|---|
| Writes | subagents never write; orchestrator writes only after one packaged confirmation; rejection = byte-identical roots |
| Evidence | verbatim + anchored, immutable; corrections append |
| Network | `refresh --live` and confirmed acquisition only; `govern` never fetches; the viewer page makes zero outbound calls |
| Git | Framework only, pre-flighted by `git_guard`; ≤1 local commit per completed Goal, never auto-pushed; private-root Git is invisible to Palace |
| Context | INDEX-first prefilters; 5–15 candidate cards per dispatch; ≤15 ask candidates; ≤10/15/30 novelty pipeline stages — the whole Vault never enters a prompt |
| Full text | Source Cache only; Vault stores pointers; Workspace materials never become Claim evidence |

## 9. Extending

- **New domain**: `/palace domain add` — no code, just registry + subtree.
- **New runtime**: add a thin adapter that routes to
  `knowledge_palace/protocol/` and binds the nine role contracts; adapters
  never duplicate protocol bodies.
- **New dependency**: there are none, deliberately; adding one requires a
  named material-risk gate (see `CLAUDE.md`).
