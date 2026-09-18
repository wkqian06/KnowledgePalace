"""Scale check at the realistic V1 ceiling (5k Works / 50k Edges).

Deliberately NOT auto-discovered (no ``test_`` prefix) so the fast unit
suite stays fast. Run explicitly:

    python3 -m knowledge_palace.tests.scale_check [--works N]

``--works`` below the default is a debugging convenience only: the
edge-floor stage relaxes, but the cap stages assume a graph dense enough
to fill every cap (roughly N ≥ 100).

Generates a synthetic Vault on a tmp root sized to the V1 scale target
ceiling, then measures and checks: identity parse (zero problems), index
build time, REBUILD idempotence (payload fingerprints byte-equal), the
frozen port contract at scale (pagination truncated ⇔ next_cursor, typed
stale refusal), and the bounded pipelines' caps with honest truncation on
the dense graph. Prints one JSON summary line per stage and exits 0 only
if every stage passed.
"""

import argparse
import json
import shutil
import sys
import tempfile
import time
from pathlib import Path

from ..graph.builder import build_payload, payload_fingerprint, write_index
from ..graph.identity import load_vault_identity
from ..graph.port import GraphQueryPort
from ..interaction.novelty import CLAIM_CAP, CORRIDOR_CAP, WORK_CAP, novelty_pipeline
from ..interaction.prefilter import CANDIDATE_CAP, find_candidates
from ..semantic.corridors import CORRIDOR_CAP as SHARED_CAP, find_corridors

TASKS_PER_DOMAIN = 25
PATTERNS = 20
GAPS_PER_DOMAIN = 50

# Titles are word-combination heterogeneous like real ones: any two differ
# by at least one full content word. The vast majority land well under
# identity's 0.92 fuzzy threshold; ~0.05% of pairs (near-substring words
# like fusion/diffusion) legitimately exceed it and surface as bounded
# confirmations — cheap, because the length/multiset upper bounds prune
# 99.8% of pairs before any full ratio() runs. (Round-1/2 review history:
# integer-suffix and truncated-hash titles both drove the O(N²) fuzzy
# pass into multi-minute territory with bulk false matches.)
ADJECTIVES = (
    "quantum", "neural", "hybrid", "sparse", "robust", "adaptive",
    "bayesian", "convex", "spectral", "kernel", "latent", "causal",
    "modular", "fuzzy", "greedy", "optimal", "parallel", "recursive",
    "stochastic", "symbolic",
)
NOUNS = (
    "drift", "fusion", "routing", "pruning", "caching", "masking",
    "scaling", "sampling", "encoding", "matching", "tracking", "ranking",
    "clustering", "alignment", "inference", "transport", "synthesis",
    "retrieval", "diffusion", "attention",
)
VERBS = (
    "improves", "degrades", "stabilizes", "accelerates", "compresses",
    "regularizes", "disentangles", "calibrates", "quantizes", "amortizes",
    "interpolates", "generalizes", "overfits", "saturates", "converges",
    "diverges", "sharpens", "smooths", "perturbs", "anchors",
)

CARD = """---
slug: {slug}
title: "{adj} {noun} {verb} shared keyword"
authors: [Auth, A.]
year: {year}
venue: "Scale Venue"
citations: {i}
citations_date: 2026-07
weight: medium
source: "10.99999/scale.{i}"
local: "fulltext/{slug}.pdf"
added: 2026-07-14
read_depth: skim
domain: [scale-{d}]
task: [task-{d}-{t}]
pattern: [pattern-shared-{p}, pattern-shared-{q}]
function: []
method: []
metric: []
failure-mode: []
gaps: ["gap-{d}-{g}:supports"]
code: none-stated
data: none-stated
compute: none-stated
---

# Scale work {i}

## Claims

- C1 [task-{d}-{t}]: "Claim one of work {i}." — §1 / p.1
- C2 [pattern-shared-{p}]: "Claim two of work {i}." — §2 / p.2
- C3: "Claim three of work {i}." — §3 / p.3
- C4: "Claim four of work {i}." — §4 / p.4
"""

GAP = """---
slug: gap-{d}-{g}
type: method
status: open
source_type: explicit_author
concepts: [task-{d}-{t}]
related: []
---

# gap-{d}-{g}

## Statement

Synthetic scale gap {g} in domain {d}.
"""


def generate_vault(root, works):
    vault = Path(root) / "vault"
    (vault / "papers").mkdir(parents=True)
    (vault / "gaps").mkdir()
    (vault / "domains.md").write_text(
        "# Domains\n\n| Slug | Name | Status | Seeded | Notes |\n|---|---|---|---|---|\n"
        "| scale-a | A | active | 2026-07-14 | synthetic |\n"
        "| scale-b | B | active | 2026-07-14 | synthetic |\n",
        encoding="utf-8",
    )
    lines = ["# Concept Registry (scale)", "", "## domain",
             "| Slug | Parents | Status | Aliases | Definition | Notes |",
             "|---|---|---|---|---|---|",
             "| scale-a | - | canonical | - | Domain A. | - |",
             "| scale-b | - | canonical | - | Domain B. | - |",
             "", "## task",
             "| Slug | Parents | Status | Aliases | Definition | Notes |",
             "|---|---|---|---|---|---|"]
    for domain in ("a", "b"):
        for t in range(TASKS_PER_DOMAIN):
            lines.append("| task-%s-%d | scale-%s | canonical | - | Task. | - |"
                         % (domain, t, domain))
    lines += ["", "## pattern",
              "| Slug | Parents | Status | Aliases | Definition | Notes |",
              "|---|---|---|---|---|---|"]
    for p in range(PATTERNS):
        lines.append("| pattern-shared-%d | - | canonical | - | Shared pattern. | - |" % p)
    for axis in ("method", "function", "metric", "failure-mode"):
        lines += ["", "## %s" % axis,
                  "| Slug | Parents | Status | Aliases | Definition | Notes |",
                  "|---|---|---|---|---|---|"]
    (vault / "concepts.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    for domain in ("a", "b"):
        for g in range(GAPS_PER_DOMAIN):
            (vault / "gaps" / ("gap-%s-%d.md" % (domain, g))).write_text(
                GAP.format(d=domain, g=g, t=g % TASKS_PER_DOMAIN), encoding="utf-8"
            )
    for i in range(works):
        domain = "a" if i % 2 == 0 else "b"
        slug = "scale-%s-%05d" % (domain, i)
        (vault / "papers" / (slug + ".md")).write_text(
            CARD.format(slug=slug, i=i, year=2000 + i % 25,
                        adj=ADJECTIVES[i % 20], noun=NOUNS[(i // 20) % 20],
                        verb=VERBS[(i // 400) % 20],
                        d=domain, t=i % TASKS_PER_DOMAIN, p=i % PATTERNS,
                        q=(i + 7) % PATTERNS, g=i % GAPS_PER_DOMAIN),
            encoding="utf-8",
        )
    return vault


def check(name, ok, **detail):
    print(json.dumps(dict({"stage": name, "ok": bool(ok)}, **detail),
                     ensure_ascii=False, sort_keys=True))
    return bool(ok)


def run(works):
    results = []
    with tempfile.TemporaryDirectory() as tmp:
        vault = generate_vault(tmp, works)
        state = Path(tmp) / "state"

        start = time.monotonic()
        identity = load_vault_identity(vault)
        parse_s = time.monotonic() - start
        results.append(check(
            "identity", not identity["parse_errors"],
            works=len(identity["works"]), claims=len(identity["claims"]),
            problems=len(identity["parse_errors"]), seconds=round(parse_s, 2),
        ))

        start = time.monotonic()
        payload = build_payload(vault)
        build_s = time.monotonic() - start
        edges = len(payload["edges"])
        results.append(check(
            "build", edges >= 50_000 or works < 5000,
            nodes=len(payload["nodes"]), edges=edges, seconds=round(build_s, 2),
        ))

        fingerprint = payload_fingerprint(payload)
        rebuilt = payload_fingerprint(build_payload(vault))
        write_index(vault, state)
        shutil.rmtree(state)  # the recovery move: Derived State is disposable
        write_index(vault, state)
        document = json.loads(
            (state / "graph-index" / "index.json").read_text(encoding="utf-8")
        )
        results.append(check(
            "rebuild-idempotent",
            fingerprint == rebuilt == document["payload_fingerprint"],
            fingerprint=fingerprint[:16],
        ))

        port = GraphQueryPort(vault, state)
        page = port.query_level("domain-concept-work", 2)  # works and gaps
        body = page.get("page") or {}  # flat envelope (schema v1.0)
        paged_ok = (
            body.get("truncated") is (body.get("next_cursor") is not None)
            and body.get("truncated") is True
        )
        second = (
            port.query_level("domain-concept-work", 2, cursor=body.get("next_cursor"))
            .get("page")
            or {}
        )
        results.append(check(
            "port-contract",
            paged_ok and second.get("returned"),
            page_returned=body.get("returned"),
        ))

        # Uniform synthetic labels tie-rank alphabetically into one domain
        # and the novelty stage derives domains from the CAPPED candidate
        # list, so the query names eight works per domain — a realistic
        # cross-domain idea text (real vaults have heterogeneous labels;
        # the tie-monoculture edge is recorded in the scale-check report).
        query = "shared keyword " + " ".join(
            ["scale-a-%05d" % (2 * k) for k in range(8)]
            + ["scale-b-%05d" % (2 * k + 1) for k in range(8)]
        )
        candidates = find_candidates(payload, query)
        corridors = find_corridors(payload, "scale-a", "scale-b")
        pipeline = novelty_pipeline(payload, query)
        start = time.monotonic()
        find_candidates(payload, query)
        query_s = time.monotonic() - start
        results.append(check(
            "bounded-pipelines",
            len(candidates) == CANDIDATE_CAP
            and corridors["returned"] == SHARED_CAP and corridors["truncated"]
            and len(pipeline["corridors"]["returned"]) == CORRIDOR_CAP
            and len(pipeline["works"]["returned"]) == WORK_CAP
            and len(pipeline["claims"]["returned"]) == CLAIM_CAP
            and all(pipeline[s]["truncated"] for s in ("corridors", "works", "claims")),
            prefilter=len(candidates), corridors=corridors["returned"],
            prefilter_seconds=round(query_s, 2),
        ))

    ok = all(results)
    print(json.dumps({"stage": "verdict", "ok": ok, "works": works},
                     sort_keys=True))
    return 0 if ok else 1


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--works", type=int, default=5000)
    args = parser.parse_args(argv)
    return run(args.works)


if __name__ == "__main__":
    sys.exit(main())
