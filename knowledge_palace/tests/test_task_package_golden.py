"""Acceptance 5: the same fixture produces a same-schema (byte-identical)
task package regardless of which runtime dispatch path builds it."""

import os
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path

from knowledge_palace.tools import ROLES
from knowledge_palace.tools.task_package import EXPECTED_OUTPUT, build, to_json

REPO = Path(__file__).resolve().parents[2]
FIXTURE = Path(__file__).resolve().parent / "fixtures" / "paper-synthetic.md"
GOLDEN_DIR = Path(__file__).resolve().parent / "fixtures" / "task_packages"
GOLDEN_ROLES = ("extractor", "writer")

PACKAGE_KEYS = {
    "schema_version",
    "package_kind",
    "role",
    "contract",
    "protocol",
    "templates_dir",
    "inputs",
    "constraints",
    "expected_output",
}


@contextmanager
def chdir(path):
    previous = os.getcwd()
    os.chdir(str(path))
    try:
        yield
    finally:
        os.chdir(previous)


class TestTaskPackage(unittest.TestCase):
    def test_matches_golden_bytes(self):
        for role in GOLDEN_ROLES:
            golden = (GOLDEN_DIR / ("%s.golden.json" % role)).read_text(encoding="utf-8")
            self.assertEqual(to_json(build(FIXTURE, role)), golden, role)

    def test_both_dispatch_paths_identical_and_cwd_independent(self):
        claude_path = build(FIXTURE, "extractor")
        codex_path = build(FIXTURE, "extractor")
        self.assertEqual(claude_path, codex_path)
        with tempfile.TemporaryDirectory() as td:
            with chdir(td):
                self.assertEqual(build(FIXTURE, "extractor"), claude_path)

    def test_schema_shape_and_constraints(self):
        package = build(FIXTURE, "analyst")
        self.assertEqual(set(package), PACKAGE_KEYS)
        self.assertEqual(package["package_kind"], "palace-task")
        self.assertEqual(
            package["constraints"],
            {
                "read_only": True,
                "tools": ["Read", "Grep", "Glob"],
                "writes_files": False,
                "whole_vault_scan": False,
            },
        )
        self.assertEqual(
            package["inputs"]["fixture"]["path"],
            "knowledge_palace/tests/fixtures/paper-synthetic.md",
        )
        self.assertEqual(len(package["inputs"]["fixture"]["sha256"]), 64)

    def test_every_role_builds_with_its_contract(self):
        self.assertEqual(set(EXPECTED_OUTPUT), set(ROLES))
        for role in ROLES:
            package = build(FIXTURE, role)
            self.assertEqual(
                package["contract"], "knowledge_palace/agents/palace-%s.md" % role
            )
            self.assertTrue((REPO / package["contract"]).is_file(), role)

    def test_unknown_role_is_refused(self):
        with self.assertRaises(ValueError):
            build(FIXTURE, "ghostwriter")


if __name__ == "__main__":
    unittest.main()
