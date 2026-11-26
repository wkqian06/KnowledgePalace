"""Reading one named section revision for the writing workspace history view."""

import tempfile
import unittest
from pathlib import Path

from knowledge_palace.workspace.discovery import read_revision
from knowledge_palace.workspace.project import create_project, new_project


class RevisionCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.workspace = Path(self._tmp.name) / "workspace"
        self.workspace.mkdir()
        create_project(self.workspace, new_project("echo-paper", "paper", "readers", venue="Echo Journal"))
        self.section = self.workspace / "projects" / "echo-paper" / "sections" / "introduction"
        self.section.mkdir()


class TestReadRevision(RevisionCase):
    def test_reads_named_revision(self):
        (self.section / "r001.md").write_bytes("first 文本\n".encode("utf-8"))
        (self.section / "r002.md").write_bytes(b"second\n")
        self.assertEqual(read_revision(self.workspace, "echo-paper", "introduction", "r001.md"),
                         {"section": "introduction", "revision": "r001.md", "content": "first 文本\n"})
        self.assertEqual(read_revision(self.workspace, "echo-paper", "introduction", "r002.md")["content"], "second\n")

    def test_rejects_invalid_revision_names(self):
        (self.section / "r001.md").write_text("text", encoding="utf-8")
        for name in ("../r001.md", "r1.md", "r001.md\n", "r001.txt", "", None):
            with self.subTest(name=name), self.assertRaises(ValueError):
                read_revision(self.workspace, "echo-paper", "introduction", name)

    def test_rejects_invalid_section_and_project(self):
        for section in ("../introduction", "Introduction", "intro/x", ""):
            with self.subTest(section=section), self.assertRaises(ValueError):
                read_revision(self.workspace, "echo-paper", section, "r001.md")
        with self.assertRaises(FileNotFoundError):
            read_revision(self.workspace, "missing-paper", "introduction", "r001.md")

    def test_missing_section_or_revision(self):
        with self.assertRaises(FileNotFoundError):
            read_revision(self.workspace, "echo-paper", "methods", "r001.md")
        with self.assertRaises(FileNotFoundError):
            read_revision(self.workspace, "echo-paper", "introduction", "r001.md")

    def test_revision_directory_is_not_a_file(self):
        (self.section / "r001.md").mkdir()
        with self.assertRaises(FileNotFoundError):
            read_revision(self.workspace, "echo-paper", "introduction", "r001.md")

    def test_rejects_revision_over_one_mebibyte(self):
        (self.section / "r001.md").write_bytes(b"x" * (1024 * 1024 + 1))
        with self.assertRaises(ValueError):
            read_revision(self.workspace, "echo-paper", "introduction", "r001.md")
        (self.section / "r002.md").write_bytes(b"x" * (1024 * 1024))
        self.assertEqual(len(read_revision(self.workspace, "echo-paper", "introduction", "r002.md")["content"]), 1024 * 1024)


if __name__ == "__main__":
    unittest.main()
