"""Evidence selection, unresolved review retention and project feedback."""

import copy
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from knowledge_palace.graph.builder import build_payload, write_index
from knowledge_palace.interaction.research_helpers import research_context, bridge_candidates
from knowledge_palace.semantic.update_helpers import load_updates, resolve_update, review_queue
from knowledge_palace.tests.test_research import MINI, ARGUMENT, SYNTHESIS
from knowledge_palace.workspace.project import create_project, new_project
from knowledge_palace.workspace.research_helpers import project_context


class TestContinuity(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.vault, self.state, self.workspace = (self.root / name for name in ("vault", "state", "workspace"))
        shutil.copytree(MINI, self.vault)
        self.paper = self.vault / "papers/alpha-2020-echo.md"
        self.paper.write_text(self.paper.read_text(encoding="utf-8") + ARGUMENT, encoding="utf-8")
        self.brief = self.vault / "briefs/2026-07-13-gaps.md"
        self.brief.write_text("---\ntopic: alpha-domain\nview: progress\ndate: 2026-07-13\n---\n" + SYNTHESIS, encoding="utf-8")

    def test_full_first_query_still_reads_alternative_and_current_evidence(self):
        payload = build_payload(self.vault)
        for n in range(20):
            nid = "work:aaa-%02d" % n
            node = copy.deepcopy(payload["nodes"]["work:beta-2021-foxtrot"])
            node.update(id=nid, label="broad-topic")
            payload["nodes"][nid] = node
            payload["parents"][nid] = []
        context = research_context(payload, "broad-topic", ["rare-window-token"])
        self.assertEqual(len(context["attempts"]), 2)
        self.assertLessEqual(len(context["candidates"]), 15)
        self.assertIn("claim:alpha-2020-echo#C1", context["claims"])
        self.assertIn("brief:2026-07-13-gaps", context["current_syntheses"])
        self.assertTrue(context["relations"])

    def test_latest_topic_synthesis_is_read_and_missing_sources_are_explicit(self):
        newer = self.vault / "briefs/2026-08-01-progress.md"
        newer.write_text(self.brief.read_text(encoding="utf-8").replace("2026-07-13", "2026-08-01"), encoding="utf-8")
        context = research_context(build_payload(self.vault), "alpha-domain")
        self.assertEqual(list(context["current_syntheses"]), ["brief:2026-08-01-progress"])
        self.assertIn("claim:alpha-2020-echo#C1", context["claims"])
        self.assertFalse(any(ref.startswith("claim:") for ref in context["unread_dependencies"]))

    def test_related_gap_content_does_not_bypass_reading_budget(self):
        payload = build_payload(self.vault)
        refs = []
        for n in range(25):
            nid = "gap:extra-%02d" % n
            node = copy.deepcopy(payload["nodes"]["gap:gap-echo-noise"])
            node.update(id=nid, label="unmatched gap")
            payload["nodes"][nid] = node
            payload["parents"][nid] = []
            refs.append(nid)
        brief = payload["nodes"]["brief:2026-07-13-gaps"]
        brief["attrs"]["synthesis"][0]["gaps"] = ", ".join(refs)
        context = research_context(payload, "alpha-domain")
        selected = {row["node_id"] for row in context["candidates"]}
        full_cards = set(context["works"]) | set(context["gaps"]) | set(context["current_syntheses"])
        self.assertLessEqual(len(full_cards), 15)
        self.assertLessEqual(full_cards, selected)
        self.assertTrue(set(refs) - selected <= set(context["unread_dependencies"]))
        self.assertTrue(all(set(row) == {"node_id", "canonical_ref"} for row in context["related_gaps"]))

    def test_conditions_only_revision_reaches_claim_consumers(self):
        self.paper.write_text(self.paper.read_text(encoding="utf-8").split("## Evidence relations")[0], encoding="utf-8")
        project = create_project(self.workspace, new_project("echo-study", "paper", "researchers"))
        ref = "claim:alpha-2020-echo#C1"
        (project / "outline/brief.json").write_text(json.dumps({"evidence": [{"ref": ref}],
            "sections": [{"name": "discussion", "evidence": [ref]}]}), encoding="utf-8")
        (project / "research.md").write_text(SYNTHESIS, encoding="utf-8")
        write_index(self.vault, self.state, self.workspace)
        self.paper.write_text(self.paper.read_text(encoding="utf-8").replace("rare-window-token", "a different sampling window"), encoding="utf-8")
        write_index(self.vault, self.state, self.workspace)
        affected = {(r["node_id"], r["entry"]) for r in load_updates(self.state)["entries"] if r["status"] == "pending"}
        for entry in ("argument", "section:discussion", "decision:S1"):
            self.assertIn(("project:echo-study", entry), affected)
        self.assertIn(("brief:2026-07-13-gaps", "S1"), affected)

    def test_pending_survives_unrelated_build_resolves_and_reopens(self):
        write_index(self.vault, self.state)
        other = self.vault / "papers/beta-2021-foxtrot.md"
        other.write_text(other.read_text(encoding="utf-8") + ARGUMENT.replace("partially_addresses", "disputes"), encoding="utf-8")
        write_index(self.vault, self.state)
        registry = self.vault / "concepts.md"
        registry.write_text(registry.read_text(encoding="utf-8").replace("| echo cancel |", "| echo cancel, resample |"), encoding="utf-8")
        write_index(self.vault, self.state)
        row = next(r for r in load_updates(self.state)["entries"] if r["node_id"] == "brief:2026-07-13-gaps")
        self.assertEqual(row["status"], "pending")
        self.assertEqual(len(row["events"]), 1)
        self.assertIn("question", row["suggestions"][0])
        resolve_update(self.state, row["node_id"], "S1", "retain", "Different measurement setting; retain the scoped judgment.")
        registry.write_text(registry.read_text(encoding="utf-8").replace("resample", "resampling"), encoding="utf-8")
        write_index(self.vault, self.state)
        row = next(r for r in load_updates(self.state)["entries"] if r["node_id"].startswith("brief:"))
        self.assertEqual(row["status"], "resolved")
        other.write_text(other.read_text(encoding="utf-8").replace("| disputes |", "| reframes |"), encoding="utf-8")
        write_index(self.vault, self.state)
        row = next(r for r in load_updates(self.state)["entries"] if r["node_id"].startswith("brief:"))
        self.assertEqual(row["status"], "pending")
        self.assertEqual(len(row["reviews"]), 1)
        self.assertEqual(len(row["events"]), 2)

    def test_evidence_change_reaches_bridge_project_and_section(self):
        project = create_project(self.workspace, new_project("echo-study", "paper", "researchers"))
        ref = "claim:alpha-2020-echo#C1"
        (project / "outline/brief.json").write_text(json.dumps({"evidence": [{"ref": ref}],
            "sections": [{"name": "discussion", "evidence": [ref]}]}), encoding="utf-8")
        (project / "research.md").write_text(SYNTHESIS, encoding="utf-8")
        write_index(self.vault, self.state, self.workspace)
        self.paper.write_text(self.paper.read_text(encoding="utf-8").replace("partially_addresses", "disputes"), encoding="utf-8")
        write_index(self.vault, self.state, self.workspace)
        entries = load_updates(self.state)["entries"]
        affected = {(r["node_id"], r["entry"]) for r in entries if r["status"] == "pending"}
        self.assertIn(("project:echo-study", "argument"), affected)
        self.assertIn(("project:echo-study", "section:discussion"), affected)
        self.assertIn(("project:echo-study", "decision:S1"), affected)
        self.assertTrue(any(nid.startswith("bridge:") for nid, entry in affected))

    def test_project_observation_and_selected_style_remain_distinct_from_claims(self):
        project = create_project(self.workspace, new_project("echo-study", "paper", "beginner in echo analysis"))
        style = self.root / "journal-fixture.md"
        style.write_text("# Journal fixture\nState the measured outcome first.\n", encoding="utf-8")
        (project / "outline/brief.json").write_text(json.dumps({"style_profile": str(style)}), encoding="utf-8")
        (project / "materials/materials.json").write_text(json.dumps([{"id": "material:experiment-1", "path": "materials/result.csv", "kind": "data"}]), encoding="utf-8")
        notes = "## Learning\nBackground: signal processing. Next: compare sampling windows.\n" + SYNTHESIS + """
## Observations
| ID | Source | Judgment | Outcome | Interpretation |
|---|---|---|---|---|
| O1 | material:experiment-1 | S1 | questions | The finite window did not transfer to this sample. |
"""
        (project / "research.md").write_text(notes, encoding="utf-8")
        context = project_context(self.workspace, "echo-study", self.vault)
        self.assertEqual(context["observation_feedback"][0]["outcome"], "questions")
        self.assertIn("not a literature Claim", context["observation_feedback"][0]["provenance"])
        self.assertIn("State the measured", context["style_profiles"][0]["rules"])
        self.assertIn("Background: signal", context["research_notes"])

    def test_one_domain_seed_suggests_a_foreign_function_match(self):
        selected = {"work:alpha-2020-echo"}
        self.assertEqual(bridge_candidates(build_payload(self.vault), selected), [])  # no binding Claims yet
        for name, old, new in (("alpha-2020-echo", "- C2:", "- C2 [concept-shared-pattern]:"),
                               ("beta-2021-foxtrot", "- C1:", "- C1 [concept-shared-pattern]:")):
            card = self.vault / "papers" / (name + ".md")
            card.write_text(card.read_text(encoding="utf-8").replace(old, new), encoding="utf-8")
        candidates = bridge_candidates(build_payload(self.vault), selected)
        self.assertEqual([row["node_id"] for row in candidates], ["work:beta-2021-foxtrot"])
        self.assertEqual(candidates[0]["local_claim"]["id"], "claim:alpha-2020-echo#C2")
        self.assertEqual(candidates[0]["claim"]["quote"], '"Thresholds drift under beta regimes."')

    def test_bridge_candidates_prefer_topic_then_rare_concepts(self):
        nodes = {"domain:home": {"kind": "domain"}, "domain:far": {"kind": "domain"}}
        parents, edges = {}, []
        for wid, domain in (("L", "home"), ("F1", "far"), ("F2", "far"), ("F3", "far"),
                            ("F4", "far"), ("X1", "far"), ("X2", "far"), ("X3", "far")):
            nodes["work:" + wid] = {"kind": "work", "canonical_ref": {"path": "papers/%s.md" % wid}}
            parents["work:" + wid] = ["domain:" + domain]
        # concept: (attached works, works whose C<n> binds it)
        concepts = {"common": (["L", "F1", "X1", "X2"], [("L", 1), ("F1", 1)]),
                    "rare": (["L", "F2"], [("L", 2), ("F2", 1)]),
                    "unbound": (["L", "F3"], [("L", 3)]),
                    "topic": (["L", "F4", "X1", "X2", "X3"], [("L", 4), ("F4", 1)])}
        for slug, (attached, bound) in concepts.items():
            nodes["concept:" + slug] = {"kind": "concept", "attrs": {"axis": "pattern"}}
            edges.extend({"kind": "tag:pattern", "from": "work:" + w, "to": "concept:" + slug} for w in attached)
            for work, n in bound:
                cid = "claim:%s#C%d" % (work, n)
                nodes[cid] = {"kind": "claim", "attrs": {"quote": "%s on %s" % (work, slug), "anchor": "p.1"}}
                parents[cid] = ["work:" + work]
                edges.append({"kind": "binds", "from": cid, "to": "concept:" + slug})
        payload = {"nodes": nodes, "parents": parents, "edges": edges}
        rows = bridge_candidates(payload, {"work:L"}, ["claim:claim:L#C4 (term:topic)"])
        self.assertEqual([(row["node_id"], row["via"]) for row in rows],
                         [("work:F4", "concept:topic"), ("work:F2", "concept:rare"), ("work:F1", "concept:common")])
        self.assertEqual(rows[1]["local_claim"]["quote"], "L on rare")
        self.assertEqual(rows[1]["claim"]["quote"], "F2 on rare")
        # A far-domain reading-set paper that shares none of these concepts leaves
        # the far side foreign for them.
        nodes["work:Y"] = {"kind": "work", "canonical_ref": {"path": "papers/Y.md"}}
        parents["work:Y"] = ["domain:far"]
        self.assertEqual(bridge_candidates(payload, {"work:L", "work:Y"}, ["claim:claim:L#C4 (term:topic)"]), rows)


class TestReviewQueue(unittest.TestCase):
    def test_every_pending_entry_is_listed_or_counted_never_dropped_silently(self):
        row = lambda node, entry, **extra: {"node_id": node, "entry": entry, "affected": True,
                                            "suggestions": ["review scope"], "dependencies": ["claim:p#C1"] * 40,
                                            "changed_nodes": ["claim:p#C1"], "changed_edges": [], **extra}
        document = {"entries": [row("gap:a", "S1"), row("gap:a", "S2", suggestions=["review scope", "question it"]),
                                row("gap:b", "S1"), row("project:x", "D1"),
                                row("project:y", "D1", status="resolved"), row("brief:z", "S1", affected=False)]}
        overview = review_queue(document)
        self.assertEqual((overview["pending_entries"], overview["by_kind"]), (4, {"gap:": 3, "project:": 1}))
        self.assertEqual(overview["rows"][0], {"node_id": "gap:a", "entries": ["S1", "S2"],
                                               "suggestions": ["review scope", "question it"]})
        self.assertEqual([r["node_id"] for r in overview["rows"]], ["gap:a", "gap:b", "project:x"])
        detail = review_queue(document, "gap:a")
        self.assertEqual([(r["entry"], len(r["dependencies"])) for r in detail["rows"]], [("S1", 40), ("S2", 40)])
        # Over the budget the lists become counts, then the rows stop, and the note says so.
        counted = review_queue(document, "gap:", budget=1000)
        self.assertEqual([r["dependencies"] for r in counted["rows"]], [40, 40, 40])
        self.assertIn("counted", counted["note"])
        cut = review_queue(document, "gap:", budget=300)
        self.assertEqual(len(cut["rows"]), 2)
        self.assertIn("Showing 2 of 3 rows", cut["note"])


if __name__ == "__main__":
    unittest.main()
