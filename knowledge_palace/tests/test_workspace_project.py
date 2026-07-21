"""Layout, manifest round-trip, CWD independence."""

import os
import tempfile
import unittest
from pathlib import Path

from knowledge_palace.workspace.project import (
    PROJECT_DIRS,
    create_project,
    load_project,
    new_project,
    validate_project,
)


class WorkspaceCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.workspace = Path(self._tmp.name)


class TestValidation(unittest.TestCase):
    def test_valid_project(self):
        self.assertEqual(
            validate_project(new_project("echo-paper", "paper", "ML researchers")), []
        )

    def test_bad_slug_kind_and_multiline_rejected(self):
        self.assertTrue(validate_project(new_project("Echo Paper", "paper", "a")))
        self.assertTrue(validate_project(new_project("echo", "poem", "a")))
        self.assertTrue(validate_project(new_project("echo", "paper", "")))
        self.assertTrue(validate_project(new_project("echo", "paper", "a\nb")))

    def test_every_unicode_line_boundary_rejected(self):
        # The write guard must match load_project's splitlines() parser.
        for value in ("a\rb", "a\r", "a\vb", "a\u2028b", "a\x1cb"):
            self.assertTrue(
                validate_project(new_project("echo", "paper", value)), repr(value)
            )


class TestSkeleton(WorkspaceCase):
    def test_nine_entries_and_refusal_to_overwrite(self):
        project = new_project("echo-paper", "paper", "ML researchers", venue="NeurIPS")
        root = create_project(self.workspace, project)
        self.assertEqual(root, self.workspace / "projects" / "echo-paper")
        for name in PROJECT_DIRS:
            self.assertTrue((root / name).is_dir(), name)
        self.assertTrue((root / "project.yaml").is_file())
        self.assertEqual(len(PROJECT_DIRS) + 1, 9)  # eight dirs + manifest
        with self.assertRaises(ValueError):
            create_project(self.workspace, project)

    def test_manifest_round_trips(self):
        project = new_project(
            "echo-paper", "paper", "ML researchers",
            venue="Journal: Weird Colons", length="8 pages",
        )
        create_project(self.workspace, project)
        self.assertEqual(load_project(self.workspace, "echo-paper"), project)

    def test_cwd_independence(self):
        create_project(self.workspace, new_project("echo-paper", "paper", "a"))
        old = os.getcwd()
        self.addCleanup(os.chdir, old)
        with tempfile.TemporaryDirectory() as elsewhere:
            os.chdir(elsewhere)
            loaded = load_project(self.workspace, "echo-paper")
        self.assertEqual(loaded["slug"], "echo-paper")


if __name__ == "__main__":
    unittest.main()
