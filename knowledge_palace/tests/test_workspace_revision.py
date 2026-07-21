"""Append-only rNNN revisions; no-save zero change."""

import hashlib
import tempfile
import unittest
from pathlib import Path

from knowledge_palace.workspace.project import create_project, new_project
from knowledge_palace.workspace.revision import (
    ASSEMBLED,
    latest,
    list_revisions,
    save_revision,
)


def tree_digest(base):
    digest = hashlib.sha256()
    for path in sorted(Path(base).rglob("*")):
        if path.is_file():
            digest.update(path.relative_to(base).as_posix().encode("utf-8"))
            digest.update(path.read_bytes())
    return digest.hexdigest()


class RevisionCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.workspace = Path(self._tmp.name)
        self.project_dir = create_project(
            self.workspace, new_project("echo-paper", "paper", "a")
        )


class TestAppendOnly(RevisionCase):
    def test_sequencing_and_prior_immutability(self):
        first = save_revision(self.project_dir, "introduction", "v1 text\n")
        self.assertEqual(first.name, "r001.md")
        before = first.read_bytes()
        second = save_revision(self.project_dir, "introduction", "v2 text\n")
        self.assertEqual(second.name, "r002.md")
        self.assertEqual(first.read_bytes(), before)  # prior bytes untouched
        self.assertEqual(list_revisions(self.project_dir, "introduction"),
                         ["r001.md", "r002.md"])
        self.assertEqual(latest(self.project_dir, "introduction"), "r002.md")
        self.assertFalse(  # no temp litter
            [p for p in first.parent.iterdir() if p.name.endswith(".tmp")]
        )

    def test_existing_revision_never_overwritten(self):
        save_revision(self.project_dir, "methods", "text\n")
        rogue = self.project_dir / "sections" / "methods" / "r002.md"
        rogue.write_text("occupied\n", encoding="utf-8")
        third = save_revision(self.project_dir, "methods", "next\n")
        self.assertEqual(third.name, "r003.md")  # numbering skips past it
        self.assertEqual(rogue.read_text(encoding="utf-8"), "occupied\n")

    def test_assembled_is_a_reserved_section(self):
        target = save_revision(self.project_dir, ASSEMBLED, "full document\n")
        self.assertEqual(target.parent.name, "assembled")

    def test_bad_section_name_rejected(self):
        for section in ("../escape", "methods\n", "Methods", ""):
            with self.assertRaises(ValueError):
                save_revision(self.project_dir, section, "x")


class TestNoSaveZeroChange(RevisionCase):
    def test_workspace_byte_identical_without_a_confirmed_save(self):
        save_revision(self.project_dir, "introduction", "v1\n")
        before = tree_digest(self.workspace)
        # A full no-save interaction touches nothing: reads only.
        list_revisions(self.project_dir, "introduction")
        latest(self.project_dir, "introduction")
        self.assertEqual(tree_digest(self.workspace), before)


if __name__ == "__main__":
    unittest.main()
