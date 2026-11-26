"""Read-only paper editor discovery, isolated from real workspaces."""
import json
import subprocess
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from knowledge_palace.workspace.discovery import create_section, list_projects, project_details, save_section
from knowledge_palace.workspace.project import create_project, new_project
from knowledge_palace.workspace.revision import save_revision


class DiscoveryTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.workspace = Path(self.tmp.name)

    def test_cli_paper_workflow_in_isolated_roots(self):
        roots = self.workspace
        for name in ('vault', 'state', 'source', 'workspace'):
            (roots / name).mkdir()
        config = roots / 'config.toml'
        config.write_text(''.join(f'{name}_dir = "{roots / name}"\n' for name in ('vault', 'state', 'source', 'workspace')), encoding='utf-8')
        def run(module, *args):
            result = subprocess.run([sys.executable, '-m', module, '--config', str(config), *args], capture_output=True, text=True, encoding='utf-8')
            self.assertEqual(result.returncode, 0, result.stderr)
            return json.loads(result.stdout)
        create_project(roots / 'workspace', new_project('demo', 'paper', 'readers'))
        listing = run('knowledge_palace.workspace.discovery', 'list')
        self.assertEqual([p['slug'] for p in listing['projects']], ['demo'])
        run('knowledge_palace.workspace.discovery', 'create-section', 'demo', 'introduction')
        text = roots / 'text.txt'
        text.write_text('First draft', encoding='utf-8')
        saved = run('knowledge_palace.workspace.discovery', 'save-section', 'demo', 'introduction', '--expected=NONE', '--file', str(text))
        self.assertEqual(saved['revision'], 'r001.md')
        text.write_text('Second draft', encoding='utf-8')
        saved = run('knowledge_palace.workspace.discovery', 'save-section', 'demo', 'introduction', '--expected=r001.md', '--file', str(text))
        self.assertEqual(saved['revision'], 'r002.md')
        details = run('knowledge_palace.workspace.discovery', 'details', 'demo')
        self.assertEqual(details['sections'][0]['content'], 'Second draft')
        self.assertEqual((roots / 'workspace' / 'projects' / 'demo' / 'sections' / 'introduction' / 'r001.md').read_text(encoding='utf-8'), 'First draft')
        stale = subprocess.run([sys.executable, '-m', 'knowledge_palace.workspace.discovery', '--config', str(config), 'save-section', 'demo', 'introduction', '--expected=r001.md', '--file', str(text)], capture_output=True, text=True, encoding='utf-8')
        self.assertNotEqual(stale.returncode, 0)
        self.assertIn('revision conflict', stale.stderr)
        self.assertEqual(details['sections'][0]['revisions'], ['r001.md', 'r002.md'])
        self.assertFalse((roots / 'workspace' / 'projects' / 'demo' / 'sections' / 'introduction' / 'r003.md').exists())

    def test_empty_listing_and_validated_sorted_projects(self):
        self.assertEqual(list_projects(self.workspace), {"projects": []})
        for slug in ("zeta", "alpha"):
            create_project(self.workspace, new_project(slug, "paper", "readers"))
        bad = self.workspace / "projects" / "bad"
        bad.mkdir()
        (bad / "project.yaml").write_text("bad format", encoding="utf-8")
        self.assertEqual([p["slug"] for p in list_projects(self.workspace)["projects"]], ["alpha", "zeta"])
        with self.assertRaises(ValueError):
            project_details(self.workspace, "../alpha")
        with self.assertRaises(FileNotFoundError):
            project_details(self.workspace, "missing")

    def test_create_section_is_exclusive_and_savable(self):
        create_project(self.workspace, new_project("paper", "paper", "readers"))
        self.assertEqual(create_section(self.workspace, "paper", "intro"), {"section": "intro"})
        with self.assertRaises(FileExistsError):
            create_section(self.workspace, "paper", "intro")
        with self.assertRaises(ValueError):
            create_section(self.workspace, "paper", "../outside")
        self.assertEqual(save_section(self.workspace, "paper", "intro", "draft", None)["revision"], "r001.md")
        self.assertEqual(project_details(self.workspace, "paper")["sections"][0]["content"], "draft")

    def test_sections_and_latest_content(self):
        root = create_project(self.workspace, new_project("paper", "paper", "readers"))
        save_revision(root, "intro", "first")
        save_revision(root, "intro", "second")
        (root / "sections" / "intro" / "r999.txt").write_text("ignore")
        (root / "sections" / "empty").mkdir()
        (root / "outline" / "graph-intro.html").write_text("graph")
        result = project_details(self.workspace, "paper")
        self.assertEqual(result["sections"], [
            {"name": "empty", "revisions": [], "latest": None, "content": None,
             "graph_available": False, "graph_summary": None},
            {"name": "intro", "revisions": ["r001.md", "r002.md"], "latest": "r002.md",
             "content": "second", "graph_available": True,
             "graph_summary": {"error": "graph page could not be read"}},
        ])

    def test_symlinks_are_not_followed(self):
        root = create_project(self.workspace, new_project("paper", "paper", "readers"))
        outside = self.workspace / "outside"
        outside.mkdir()
        (outside / "r001.md").write_text("private")
        try:
            (root / "sections" / "linked").symlink_to(outside, target_is_directory=True)
            (root / "sections" / "empty").mkdir()
            (root / "sections" / "empty" / "r001.md").symlink_to(outside / "r001.md")
        except OSError:
            self.skipTest("symlinks unavailable")
        self.assertEqual(project_details(self.workspace, "paper")["sections"], [
            {"name": "empty", "revisions": [], "latest": None, "content": None,
             "graph_available": False, "graph_summary": None}])

    def test_confirmed_save_appends_and_rejects_stale_revision(self):
        root = create_project(self.workspace, new_project("paper", "paper", "readers"))
        save_revision(root, "intro", "original")
        result = save_section(self.workspace, "paper", "intro", "updated", "r001.md")
        self.assertEqual(result["revision"], "r002.md")
        with self.assertRaisesRegex(ValueError, "revision conflict"):
            save_section(self.workspace, "paper", "intro", "stale", "r001.md")
        self.assertEqual((root / "sections" / "intro" / "r001.md").read_text(encoding="utf-8"), "original")
        self.assertEqual((root / "sections" / "intro" / "r002.md").read_text(encoding="utf-8"), "updated")
        with self.assertRaises(FileNotFoundError):
            save_section(self.workspace, "paper", "missing", "text", None)

    def test_concurrent_edits_never_overwrite_revision(self):
        root = create_project(self.workspace, new_project("paper", "paper", "readers"))
        save_revision(root, "intro", "baseline")
        def attempt(text):
            try:
                return save_section(self.workspace, "paper", "intro", text, "r001.md")
            except ValueError:
                return None
        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = list(pool.map(attempt, ["first", "second"]))
        self.assertEqual(sum(result is not None for result in outcomes), 1)
        self.assertIn((root / "sections" / "intro" / "r002.md").read_text(encoding="utf-8"), ("first", "second"))
        self.assertFalse((root / "sections" / "intro" / "r003.md").exists())

    def test_oversize_revision_fails_closed(self):
        root = create_project(self.workspace, new_project("paper", "paper", "readers"))
        save_revision(root, "intro", "x" * (1024 * 1024 + 1))
        with self.assertRaisesRegex(ValueError, "1 MiB"):
            project_details(self.workspace, "paper")


if __name__ == "__main__":
    unittest.main()
