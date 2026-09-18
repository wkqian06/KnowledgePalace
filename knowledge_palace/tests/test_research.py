"""Synthetic argument, retrieval, update and legacy regression cases."""

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from knowledge_palace.graph.builder import build_payload, ensure_index, write_index
from knowledge_palace.interaction.prefilter import find_candidates
from knowledge_palace.interaction.research_helpers import research_context, render_progress
from knowledge_palace.semantic.evidence_helpers import evidence_changes, read_tables

MINI = Path(__file__).parent / "fixtures" / "vault-mini"
ARGUMENT = """
## Argument

| Role | Claim | Paraphrase | Attribution | Scope |
|---|---|---|---|---|
| problem | C1 | Echo has a finite sampling window. | author | synthetic observations |
| advance | C1 | Sampling resolves echo. | system | synthetic observations |

## Conditions

| Dimension | Value | Evidence |
|---|---|---|
| sampling | rare-window-token | C1 |

## Evidence relations

| Claim | Relation | Target | Attribution | Comparison | Scope | Rationale |
|---|---|---|---|---|---|---|
| C1 | partially_addresses | gap:gap-echo-noise | system | retrospective | synthetic observations | A finite window was tested. |
"""
SYNTHESIS = """
## Synthesis

| ID | Statement | Claims | Gaps | Rationale |
|---|---|---|---|---|
| S1 | Echo has restricted support. | claim:alpha-2020-echo#C1 | gap:gap-echo-noise | Scope is one window. |
"""


class TestResearch(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.vault = self.root / "vault"
        self.state = self.root / "state"
        shutil.copytree(MINI, self.vault)
        self.paper = self.vault / "papers/alpha-2020-echo.md"
        self.paper.write_text(self.paper.read_text(encoding="utf-8") + ARGUMENT, encoding="utf-8")
        registry = self.vault / "concepts.md"
        registry.write_text(registry.read_text(encoding="utf-8").replace(
            "| echo cancel |", "| echo cancel, 回声, EC |"), encoding="utf-8")
        brief = self.vault / "briefs/2026-07-13-gaps.md"
        brief.write_text(brief.read_text(encoding="utf-8") + SYNTHESIS, encoding="utf-8")

    def test_argument_and_claim_relation_keep_identity_and_source(self):
        payload = build_payload(self.vault)
        self.assertEqual(payload["identity_report"]["parse_errors"], [])
        self.assertEqual(payload["identity_report"]["unresolved_refs"], [])
        claim = payload["nodes"]["claim:alpha-2020-echo#C1"]
        edge = next(e for e in payload["edges"] if e.get("attrs", {}).get("claim_ref"))
        self.assertEqual(edge["attrs"]["anchor"], claim["attrs"]["anchor"])
        self.assertEqual(edge["attrs"]["attribution"], "system")
        self.assertEqual(edge["attrs"]["source_ref"], claim["canonical_ref"])
        self.assertEqual(edge["attrs"]["comparison"], "retrospective")
        self.assertEqual(edge["attrs"]["scope"], "synthetic observations")
        brief = "brief:2026-07-13-gaps"
        self.assertIs(payload["nodes"][brief]["attrs"]["evidence_capable"], False)
        self.assertEqual({e["kind"] for e in payload["edges"] if e["from"] == brief},
                         {"depends_on"})
        self.assertTrue(payload["nodes"]["work:beta-2021-foxtrot"])
        self.assertEqual(payload["nodes"]["work:beta-2021-foxtrot"]["attrs"]["argument"], [])

    def test_alias_claim_and_condition_retrieval(self):
        payload = build_payload(self.vault)
        for query in ("回声如何处理", "EC", "rare-window-token"):
            with self.subTest(query=query):
                ids = [c["node_id"] for c in find_candidates(payload, query)]
                self.assertIn("work:alpha-2020-echo", ids)
        context = research_context(payload, "EC")
        report = render_progress(context)
        self.assertIn("Problem evolution", report)
        self.assertIn("partially_addresses", report)
        self.assertIn("../papers/alpha-2020-echo.md#C1", report)

    def test_incremental_evidence_reaches_gap_dependencies(self):
        before = build_payload(self.vault)
        other = self.vault / "papers/beta-2021-foxtrot.md"
        other.write_text(other.read_text(encoding="utf-8") + ARGUMENT.replace(
            "partially_addresses", "disputes"), encoding="utf-8")
        after = build_payload(self.vault)
        updates = evidence_changes(before, after)
        self.assertTrue(updates[0]["affected"])
        self.assertTrue(any("question" in s for s in updates[0]["suggestions"]))
        self.assertFalse(evidence_changes(after, after)[0]["affected"])

    def test_domain_alias_reaches_domain_tagged_work(self):
        registry = self.vault / "concepts.md"
        registry.write_text(registry.read_text(encoding="utf-8").replace(
            "| alpha-domain | - | canonical | - |",
            "| alpha-domain | - | canonical | 声学 |"), encoding="utf-8")
        payload = build_payload(self.vault)
        self.assertEqual(payload["nodes"]["domain:alpha-domain"]["attrs"]["aliases"], ["声学"])
        ids = [row["node_id"] for row in find_candidates(payload, "声学研究进展")]
        self.assertIn("work:alpha-2020-echo", ids)

    def test_index_maintenance_records_synthesis_updates(self):
        write_index(self.vault, self.state)
        self.paper.write_text(self.paper.read_text(encoding="utf-8").replace(
            "rare-window-token", "updated-window-token"), encoding="utf-8")
        document = ensure_index(self.vault, self.state)
        candidates = find_candidates(document["payload"], "updated-window-token")
        self.assertIn("work:alpha-2020-echo", [row["node_id"] for row in candidates])
        update_file = self.state / "graph-index/synthesis-updates.json"
        self.assertTrue(json.loads(update_file.read_text(encoding="utf-8"))["entries"])

    def test_bad_new_tables_reported_legacy_allowed(self):
        self.assertEqual(read_tables("## Claims\n- C1: old", "old")[1], [])
        tables, errors = read_tables(ARGUMENT.replace("| author |", "| unknown |"), "new")
        self.assertTrue(errors)
        self.assertEqual(len(tables["Argument"]), 1)

    def test_schema_keys_do_not_supply_retrieval_evidence(self):
        payload = build_payload(MINI)
        self.assertEqual(find_candidates(payload, "under what conditions"), [])
        self.assertTrue(find_candidates(build_payload(self.vault), "rare-window-token"))

    def test_gap_owner_and_downstream_brief_receive_new_evidence(self):
        gap = self.vault / "gaps/gap-echo-noise.md"
        gap.write_text(gap.read_text(encoding="utf-8") + SYNTHESIS.replace(
            "| gap:gap-echo-noise |", "| - |"), encoding="utf-8")
        brief = self.vault / "briefs/2026-07-13-gaps.md"
        brief.write_text(SYNTHESIS.replace("claim:alpha-2020-echo#C1", "-"), encoding="utf-8")
        before = build_payload(self.vault)
        other = self.vault / "papers/beta-2021-foxtrot.md"
        other.write_text(other.read_text(encoding="utf-8") + ARGUMENT.replace(
            "partially_addresses", "disputes"), encoding="utf-8")
        updates = evidence_changes(before, build_payload(self.vault))
        updates = [row for row in updates if row["node_id"].startswith(("brief:", "gap:"))]
        self.assertTrue(all(row["affected"] for row in updates))
        self.assertEqual({row["node_id"] for row in updates},
                         {"gap:gap-echo-noise", "brief:2026-07-13-gaps"})

    def test_retrospective_author_attribution_is_rejected(self):
        tables, errors = read_tables(ARGUMENT.replace(
            "| system | retrospective |", "| author | retrospective |"), "new")
        self.assertTrue(errors)
        self.assertEqual(tables["Evidence relations"], [])


if __name__ == "__main__":
    unittest.main()
