"""Exhaustive/honest walk, determinism, redaction."""

import json
import tempfile
import unittest
from pathlib import Path

from knowledge_palace.graph.builder import write_index
from knowledge_palace.viewer.export import build_bundle, canonical_bytes

MINI = Path(__file__).resolve().parent / "fixtures" / "vault-mini"

DOMAIN = "# Domains\n\n| Slug | Name | Status | Seeded | Notes |\n|---|---|---|---|---|\n| d | D | active | 2026-07-14 | fixture |\n"
CONCEPTS = (
    "# Concepts\n\n## domain\n| Slug | Parents | Status | Aliases | Definition | Notes |\n"
    "|---|---|---|---|---|---|\n| d | - | canonical | - | D. | - |\n"
    "\n## task\n| Slug | Parents | Status | Aliases | Definition | Notes |\n|---|---|---|---|---|---|\n"
    "| t | d | canonical | - | T. | - |\n"
)
CARD = """---
slug: {slug}
title: "Work {i}"
authors: [A.]
year: 2020
venue: "V"
citations: {i}
citations_date: 2026-07
weight: medium
source: "10.9999/w{i}"
local: "fulltext/{slug}.pdf"
added: 2026-07-14
read_depth: skim
domain: [d]
task: [t]
pattern: []
function: []
method: []
metric: []
failure-mode: []
gaps: []
code: none-stated
data: none-stated
compute: none-stated
---

# Work {i}

## Claims

{claims}
"""


def make_vault(root, works=1, claims_per_work=1):
    vault = Path(root) / "vault"
    (vault / "papers").mkdir(parents=True)
    (vault / "gaps").mkdir()
    (vault / "domains.md").write_text(DOMAIN, encoding="utf-8")
    (vault / "concepts.md").write_text(CONCEPTS, encoding="utf-8")
    for i in range(works):
        slug = "work-%d" % i
        claim_lines = "\n".join(
            '- C%d: "Claim %d of work %d." — §1 / p.%d' % (c + 1, c + 1, i, c + 1)
            for c in range(claims_per_work)
        )
        (vault / "papers" / (slug + ".md")).write_text(
            CARD.format(slug=slug, i=i, claims=claim_lines), encoding="utf-8"
        )
    return vault


class ExportCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)


class TestVaultMiniWalk(ExportCase):
    def test_exhaustive_over_graph_reachable_nodes(self):
        state = self.root / "state"
        write_index(MINI, state)
        payload = build_bundle(MINI, state)
        kinds = {}
        for view in payload["nodes"].values():
            kinds[view["kind"]] = kinds.get(view["kind"], 0) + 1
        # 19 of 20 vault-mini nodes: the one brief is parent-less and
        # edge-less by design (builder.py: "Briefs are views: they emit
        # zero edges") — genuinely unreachable through the frozen port,
        # not a walk defect.
        self.assertEqual(sum(kinds.values()), 19)
        self.assertNotIn("brief", kinds)
        self.assertEqual(kinds.get("transfer"), 1)  # edge-only reachable

    def test_deterministic(self):
        state = self.root / "state"
        write_index(MINI, state)
        first = canonical_bytes(build_bundle(MINI, state))
        second = canonical_bytes(build_bundle(MINI, state))
        self.assertEqual(first, second)

    def test_no_card_prose_or_source_paths_leak(self):
        state = self.root / "state"
        write_index(MINI, state)
        blob = json.dumps(build_bundle(MINI, state))
        self.assertNotIn(str(MINI.resolve()), blob)
        self.assertNotIn('"root": "source"', blob)
        self.assertNotIn('"root":"source"', blob)


class TestPaginationHonesty(ExportCase):
    def test_query_level_pagination_followed_to_completion(self):
        vault = make_vault(self.root, works=5)
        state = self.root / "state"
        write_index(vault, state)
        payload = build_bundle(vault, state, page_limit=2)  # forces multi-page level walk
        level2 = next(
            lvl for h in payload["hierarchies"] for lvl in h["levels"] if lvl["level"] == 2
        )
        self.assertEqual(len(level2["node_ids"]), 5)
        self.assertEqual(sum(1 for v in payload["nodes"].values() if v["kind"] == "work"), 5)

    def test_children_and_edges_pagination_reaches_all_claims(self):
        vault = make_vault(self.root, works=1, claims_per_work=5)
        state = self.root / "state"
        write_index(vault, state)
        payload = build_bundle(vault, state, page_limit=2)  # forces work's children to truncate
        work_ctx = payload["contexts"]["work:work-0"]
        self.assertFalse(work_ctx["children"]["truncated"])
        self.assertEqual(work_ctx["children"]["total"], 5)
        self.assertEqual(work_ctx["children"]["returned"], 5)
        claim_count = sum(1 for v in payload["nodes"].values() if v["kind"] == "claim")
        self.assertEqual(claim_count, 5)


if __name__ == "__main__":
    unittest.main()
