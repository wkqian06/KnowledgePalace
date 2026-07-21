# KnowledgePalace

English | [中文](README.zh-CN.md)

An evidence-driven research knowledge OS. An LLM orchestrator (Claude Code or
Codex) plus a deterministic, stdlib-only Python core turn the papers you read
into a human-readable markdown knowledge graph — where every stored statement
is a verbatim quote with an anchor, every count is computed live rather than
cached, and nothing is written without your explicit confirmation.

You talk to it in natural language or with `/palace` commands. It answers only
from evidence it actually holds, tells you exactly what it does not know, and
proposes bounded literature expansion to fill the holes.

## What it does

**Build an evidence base**

- **Ingest papers** (`/palace ingest`, `/palace init`) — full text + metadata
  become a *paper card*: verbatim claims with anchors (`— §sec [¶para] /
  p.page`), limitation-derived gap candidates, concept tags on 7 axes, and a
  qualitative weight band (impact factor × age-tiered citations).
- **Track research gaps** — gap cards accumulate weighted relations
  (`identifies / supports / partially_addresses / disputes / reframes`) as
  papers arrive; status changes always carry a rationale, and preprint-only
  evidence can never close a gap.
- **Bounded literature expansion** (`/palace expand`) — A→B→C citation
  traversal with explicit depth (≤2) and budget caps, scope-bound
  select/defer/reject decisions, and resumable checkpoints. Never an
  unbounded crawl.
- **Multi-domain by design** (`/palace domain add`) — per-domain concept
  subtrees over shared abstraction axes; between top-level domains there are
  only typed bridges, never hierarchy.

**Consult it**

- **Grounded Q&A** (`/palace ask`) — coverage-gated answers: every sentence
  is tagged `[C:slug]` (a paper claims it), `[S]` (synthesis), or `[H:slug]`
  (hypothesis). Partial coverage answers only the covered part and names the
  holes; insufficient coverage yields an expansion proposal, never a
  fabricated answer.
- **Briefs** (`/palace brief`) — six dated, disposable views: `onboard`
  (domain map + reading path), `map <concept>` (method timeline +
  disputes), `gaps`, `ideas` (gap × transfer opportunity cards),
  `transfers`, `bridges` (domain-pair connection report).
- **Cross-domain discovery** (`/palace discover`) — evidence-backed transfer
  candidates across shared pattern/function/failure-mode axes, each with
  non-stopword bridges and a first validation experiment.
- **Idea refinement** (`/palace idea refine`) — your idea, critiqued against
  the vault: supporting/opposing/unknown evidence side by side, closest prior
  work, falsifiers, and a minimal validation experiment. Novelty verdicts are
  profile-bound and vault-relative — never absolute claims.

**Write with it**

- **Paper/proposal workspace** (`/palace write`) — projects with frozen,
  fingerprinted evidence briefs; a writer/reviewer loop (≤2 automatic
  rounds); append-only `rNNN.md` revisions; anchored requirements matrices
  for proposals; replayable pandoc export plans. Results are never
  fabricated — a Results section without your data is placeholder-only.
- **Style library** (`/palace style`) — 7-dimension style feature cards from
  papers you admire, crystallized into journal/language profiles that bind
  drafting.
- **Provenance-tagged intros** (`/palace draft intro`) — an introduction
  skeleton where every sentence declares which evidence it rests on.

**Keep it healthy**

- **Governance and audit** (`/palace govern`, `/palace audit`) — live
  grep-computed trigger scans, concept promotion proposals with impact
  lists, adversarial anchor/provenance review. All edits confirm-first.
- **Offline graph viewer** (`/palace viewer export`) — one self-contained
  HTML file (zero dependencies, zero network) for read-only browsing of the
  domain → concept → work/gap graph.

## Design guarantees

- **Four private roots, outside this repo** — Vault (confirmed knowledge),
  Derived State (rebuildable caches), Source Cache (immutable full texts),
  Workspace (writing projects). Your data never lives in the Framework and
  Palace never runs Git against it.
- **Confirm-before-write** — subagents are read-only; the orchestrator
  packages every change into one confirmation and writes only what you
  approve. Rejection changes nothing, byte-for-byte.
- **Evidence is immutable** — quotes are never edited in place; corrections
  append and preserve the original.
- **Offline by default** — `/palace refresh` is the only network entry, and
  only when you invoke it. `govern` reports stale data; it never fetches.
- **No numeric scoring theater** — weights are qualitative bands, minority
  evidence is displayed next to majority evidence, and support counts are
  grep-computed live, never cached as authority.

## Quick start

Requirements: Python ≥ 3.9 (standard library only — no pip install), and
Claude Code (or Codex; both runtimes share the same core).

```bash
git clone <this-repo> KnowledgePalace
cd KnowledgePalace

# 1. Create the four private roots OUTSIDE the repo worktree
mkdir -p ../KnowledgePalace-vault ../KnowledgePalace-state \
         ../KnowledgePalace-sources ../KnowledgePalace-workspace

# 2. Point Palace at them (paths resolve relative to the config file)
cp .palace.example.toml .palace.toml   # edit if you chose other locations

# 3. Verify the setup — read-only, zero writes, zero network
python3 -m knowledge_palace.tools.doctor
```

Then open Claude Code in the repo root and start talking:

```
/palace init transformer-interpretability 30   # bootstrap: search → you circle → batch ingest
/palace ingest 10.1038/s41586-021-03819-2      # or ingest one paper by DOI/path
/palace status                                 # live counts + consistency, no writes
/palace ask what limits sample efficiency here?
/palace brief gaps                             # ranked open problems
/palace viewer export                          # offline HTML graph browser
```

Every flow ends in one packaged confirmation before anything is written.

## Command surface

| Command | Purpose |
|---|---|
| `/palace init <topic> [n]` | bootstrap a topic corpus: search → one selection → batch ingest |
| `/palace ingest [<paths\|dois>...]` | single or batch paper ingestion |
| `/palace expand <work\|doi> [...]` | bounded A→B→C literature expansion |
| `/palace domain add <name>` · `list` | register a domain with a seeded concept subtree |
| `/palace status` | live vault counts + consistency report |
| `/palace brief <view> [<domain>]` | onboard · map · gaps · ideas · transfers · bridges |
| `/palace ask <question>` | coverage-gated, provenance-tagged Q&A |
| `/palace discover [<target>]` | cross-domain transfer scouting |
| `/palace idea refine <text\|file>` | critique + upgrade a research idea |
| `/palace draft intro <topic>` | provenance-tagged introduction draft |
| `/palace write <project> [<section>]` | section-wise paper/proposal drafting |
| `/palace style <ingest\|status\|crystallize>` | build the writing-style library |
| `/palace govern` · `audit` | governance scan · adversarial vault review |
| `/palace refresh <kind> [<scope>]` | explicit metadata/citation/impact refresh (the only network entry) |
| `/palace viewer export [<path>]` | one offline HTML file for graph browsing |

## Learn more

- **[GUIDE.md](GUIDE.md)** — architecture, repository layout, data model, and
  a detailed command reference.
- **[TUTORIAL.md](TUTORIAL.md)** — hands-on walkthroughs, from empty setup to
  writing a paper section.
- **[PALACE.md](PALACE.md)** — public policy: concept axes, weight bands,
  thresholds, governance triggers.
- **[CONTEXT.md](CONTEXT.md)** — the ubiquitous language (every domain term,
  defined).
- **`knowledge_palace/protocol/`** — the platform-neutral protocol:
  [PROTOCOL.md](knowledge_palace/protocol/PROTOCOL.md) (rules),
  [COMMANDS.md](knowledge_palace/protocol/COMMANDS.md) (per-command flows),
  [GRAPH_QUERY_PORT.md](knowledge_palace/protocol/GRAPH_QUERY_PORT.md) (query
  contract).