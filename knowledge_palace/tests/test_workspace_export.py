"""CSL precedence and deterministic, collision-free,
source-untouched export plans (stub runner only — never live pandoc)."""

import tempfile
import unittest
from pathlib import Path

from knowledge_palace.workspace.export import FORMATS, build_plan, run_plan
from knowledge_palace.workspace.project import create_project, new_project
from knowledge_palace.workspace.revision import save_revision


class ExportCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.project = new_project("echo-paper", "paper", "a",
                                   citation_style="apa")
        self.project_dir = create_project(Path(self._tmp.name), self.project)
        self.revision = save_revision(self.project_dir, "assembled", "# Doc\n")


class TestCslPrecedence(ExportCase):
    def test_apa_default_manifest_and_override(self):
        plan = build_plan(self.project_dir, {"citation_style": ""},
                          "assembled", "r001.md", "docx")
        self.assertEqual(plan["csl"], "apa")
        plan = build_plan(self.project_dir, self.project,
                          "assembled", "r001.md", "docx")
        self.assertEqual(plan["csl"], "apa")  # from the manifest field
        plan = build_plan(self.project_dir,
                          dict(self.project, citation_style="ieee"),
                          "assembled", "r001.md", "docx")
        self.assertEqual(plan["csl"], "ieee")
        plan = build_plan(self.project_dir, self.project,
                          "assembled", "r001.md", "docx", csl="chicago")
        self.assertEqual(plan["csl"], "chicago")  # explicit override wins


class TestPlans(ExportCase):
    def test_deterministic(self):
        first = build_plan(self.project_dir, self.project,
                           "assembled", "r001.md", "pdf")
        second = build_plan(self.project_dir, self.project,
                            "assembled", "r001.md", "pdf")
        self.assertEqual(first, second)

    def test_all_formats_produce_relative_paths_and_args(self):
        for fmt in FORMATS:
            plan = build_plan(self.project_dir, self.project,
                              "assembled", "r001.md", fmt)
            self.assertEqual(plan["source"], "sections/assembled/r001.md")
            self.assertTrue(plan["output"].startswith("exports/"))
            self.assertEqual(plan["args"][0], "pandoc")
            self.assertIn("--citeproc", plan["args"])
            self.assertNotIn("/", plan["args"][1].split("sections")[0])  # relative
        pdf = build_plan(self.project_dir, self.project,
                         "assembled", "r001.md", "pdf")
        self.assertIn("--pdf-engine", pdf["args"])
        tex = build_plan(self.project_dir, self.project,
                         "assembled", "r001.md", "latex")
        self.assertTrue(tex["output"].endswith(".tex"))

    def test_missing_revision_bad_format_bad_name_rejected(self):
        with self.assertRaises(ValueError):
            build_plan(self.project_dir, self.project, "assembled", "r009.md", "docx")
        with self.assertRaises(ValueError):
            build_plan(self.project_dir, self.project, "assembled", "r001.md", "odt")
        with self.assertRaises(ValueError):
            build_plan(self.project_dir, self.project, "assembled", "notes.md", "docx")
        with self.assertRaises(ValueError):
            build_plan(self.project_dir, self.project, "../escape", "r001.md", "docx")

    def test_collision_free_naming(self):
        (self.project_dir / "exports" / "assembled-r001.docx").write_text(
            "occupied", encoding="utf-8"
        )
        plan = build_plan(self.project_dir, self.project,
                          "assembled", "r001.md", "docx")
        self.assertEqual(plan["output"], "exports/assembled-r001-2.docx")

    def test_stub_runner_gets_the_plan_and_source_stays_untouched(self):
        before = self.revision.read_bytes()
        seen = []

        def stub(plan):
            seen.append(plan)
            return "ok"

        plan = build_plan(self.project_dir, self.project,
                          "assembled", "r001.md", "docx")
        self.assertEqual(run_plan(plan, stub), "ok")
        self.assertEqual(seen, [plan])
        self.assertEqual(self.revision.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
