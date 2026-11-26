"""Style selection for the writing workspace and the graph summary it gates on."""

import json
import os
import tempfile
import unittest
from pathlib import Path

from knowledge_palace.workspace.argument_graph import render_view
from knowledge_palace.workspace.discovery import project_details, section_graph_summary
from knowledge_palace.workspace.project import create_project, load_project, new_project
from knowledge_palace.workspace.style import list_style_profiles, set_project_style


PROFILE = """---
name: journal-echo
type: journal
alias: "Echo Journal (test family)"
description: "A test profile for the writing picker."
updated: 2026-01-01
---

# journal-echo

| # | Rule | Support n/N | Maturity |
|---|---|---|---|
| D2.1 | Short verdicts | 3/3 | stable |
"""


class StyleCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        root = Path(self._tmp.name)
        self.workspace = root / "workspace"
        self.vault = root / "vault"
        self.workspace.mkdir()
        profiles = self.vault / "styles" / "profiles"
        profiles.mkdir(parents=True)
        (profiles / "journal-echo.md").write_text(PROFILE, encoding="utf-8")
        self.project = new_project("echo-paper", "paper", "readers", venue="Echo Journal")
        create_project(self.workspace, self.project)


class TestStyleList(StyleCase):
    def test_lists_regular_profiles_with_front_matter(self):
        rows = list_style_profiles(self.vault)
        self.assertEqual([row["name"] for row in rows["profiles"]], ["journal-echo"])
        self.assertEqual(rows["profiles"][0]["type"], "journal")
        self.assertEqual(rows["profiles"][0]["alias"], "Echo Journal (test family)")
        self.assertEqual(rows["counts"], {"journal": 1, "language": 0})

    def test_missing_bank_is_empty_not_an_error(self):
        empty = Path(self._tmp.name) / "nowhere"
        self.assertEqual(list_style_profiles(empty)["profiles"], [])


class TestStyleSet(StyleCase):
    def test_sets_and_clears_the_manifest_line(self):
        result = set_project_style(self.workspace, self.vault, "echo-paper", "journal-echo")
        self.assertEqual(result["style_profile"], "journal-echo")
        self.assertEqual(load_project(self.workspace, "echo-paper")["style_profile"], "journal-echo")
        self.assertEqual(load_project(self.workspace, "echo-paper")["audience"], "readers")
        set_project_style(self.workspace, self.vault, "echo-paper", "")
        self.assertEqual(load_project(self.workspace, "echo-paper")["style_profile"], "")

    def test_deduplicates_and_preserves_unknown_lines(self):
        manifest = self.workspace / "projects" / "echo-paper" / "project.yaml"
        manifest.write_text(manifest.read_text(encoding="utf-8") + "custom: keep\n", encoding="utf-8")
        set_project_style(self.workspace, self.vault, "echo-paper", "journal-echo; journal-echo")
        text = manifest.read_text(encoding="utf-8")
        self.assertIn("style_profile: journal-echo\n", text)
        self.assertIn("custom: keep\n", text)
        self.assertEqual(text.count("style_profile:"), 1)

    def test_refuses_unknown_profile_and_multiline_value(self):
        with self.assertRaises(FileNotFoundError):
            set_project_style(self.workspace, self.vault, "echo-paper", "journal-missing")
        with self.assertRaises(ValueError):
            set_project_style(self.workspace, self.vault, "echo-paper", "journal-echo\nother")
        with self.assertRaises(ValueError):
            set_project_style(self.workspace, self.vault, "echo-paper", "../escape")


class TestGraphSummary(StyleCase):
    def _section(self):
        (self.workspace / "projects" / "echo-paper" / "sections" / "introduction").mkdir()

    def _write_graph(self, graph, written=None):
        page = self.workspace / "projects" / "echo-paper" / "outline" / "graph-introduction.html"
        page.write_text(render_view(graph, written), encoding="utf-8")

    def test_counts_nodes_evidence_and_changes(self):
        self._section()
        graph = {
            "title": "t", "section": "introduction",
            "paragraphs": [{"id": "p1", "role": "opening", "point": "opening"}],
            "nodes": [
                {"id": "n1", "text": "a", "evidence": "claim:x#C1", "paragraph": "p1"},
                {"id": "n2", "text": "b", "evidence": " ", "paragraph": "p1"},
                {"id": "n3", "text": "c", "evidence": "待补", "paragraph": "p1"},
            ],
            "edges": [],
        }
        self._write_graph(graph)
        details = project_details(self.workspace, "echo-paper")
        section = next(row for row in details["sections"] if row["name"] == "introduction")
        self.assertTrue(section["graph_available"])
        self.assertEqual(section["graph_summary"]["nodes"], 3)
        self.assertEqual(section["graph_summary"]["without_evidence"], 1)
        self.assertEqual(section["graph_summary"]["pending_evidence"], 1)
        self.assertEqual(section["graph_summary"]["rewrite"], 0)

        changed = json.loads(json.dumps(graph))
        changed["nodes"][0]["text"] = "a changed"
        self._write_graph(changed, graph)
        summary = section_graph_summary(self.workspace, "echo-paper", "introduction")
        self.assertEqual(summary["graph_summary"]["rewrite"], 1)

    def test_graph_is_stale_when_the_text_is_newer(self):
        self._section()
        graph = {
            "title": "t", "section": "introduction",
            "paragraphs": [{"id": "p1", "role": "opening", "point": "opening"}],
            "nodes": [{"id": "n1", "text": "a", "evidence": "claim:x#C1", "paragraph": "p1"}],
            "edges": [],
        }
        self._write_graph(graph)
        page = self.workspace / "projects" / "echo-paper" / "outline" / "graph-introduction.html"
        revision = self.workspace / "projects" / "echo-paper" / "sections" / "introduction" / "r001.md"
        revision.write_text("new text", encoding="utf-8")
        base = 1_700_000_000
        os.utime(page, (base, base))
        os.utime(revision, (base + 10, base + 10))
        self.assertTrue(section_graph_summary(self.workspace, "echo-paper", "introduction")["graph_summary"]["stale"])
        details = project_details(self.workspace, "echo-paper")
        self.assertTrue(next(row for row in details["sections"] if row["name"] == "introduction")["graph_summary"]["stale"])
        os.utime(page, (base + 20, base + 20))
        self.assertFalse(section_graph_summary(self.workspace, "echo-paper", "introduction")["graph_summary"]["stale"])

    def test_missing_page_is_reported_not_raised(self):
        self.assertEqual(section_graph_summary(self.workspace, "echo-paper", "introduction"),
                         {"graph_available": False, "graph_summary": None})

    def test_manuscript_analysis_is_available_to_the_workspace(self):
        path = self.workspace / "projects" / "echo-paper" / "outline" / "manuscript-analysis.md"
        path.write_text("# analysis\nobjective + style rules\n", encoding="utf-8")
        self.assertEqual(project_details(self.workspace, "echo-paper")["analysis"],
                         path.read_bytes().decode("utf-8"))


if __name__ == "__main__":
    unittest.main()
