"""Acceptance 3: the Git target guard refuses private-root CWDs/targets with
evidence, passes Framework targets, and gates push on explicit authorization."""

import tempfile
import unittest
from pathlib import Path

from knowledge_palace.tools.git_guard import check


class TestGitGuard(unittest.TestCase):
    def setUp(self):
        self._td = tempfile.TemporaryDirectory()
        base = Path(self._td.name)
        self.framework = base / "KnowledgePalace"
        (self.framework / "sub").mkdir(parents=True)
        self.private = base / "KnowledgePalace-vault"
        self.private.mkdir()

    def tearDown(self):
        self._td.cleanup()

    def test_private_cwd_refused_with_evidence(self):
        allowed, reason = check(["status"], self.private, self.framework)
        self.assertFalse(allowed)
        self.assertIn(str(self.private.resolve()), reason)
        self.assertIn("outside the Public Framework", reason)

    def test_dash_c_private_target_refused(self):
        allowed, reason = check(
            ["-C", "../KnowledgePalace-vault", "log"], self.framework, self.framework
        )
        self.assertFalse(allowed)
        self.assertIn("-C target", reason)

    def test_git_dir_private_target_refused(self):
        allowed, reason = check(
            ["--git-dir=../KnowledgePalace-vault/.git", "log"],
            self.framework,
            self.framework,
        )
        self.assertFalse(allowed)
        self.assertIn("--git-dir", reason)

    def test_framework_operations_pass(self):
        for args in (["status"], ["-C", str(self.framework), "log"], ["commit", "-m", "x"]):
            allowed, reason = check(args, self.framework, self.framework)
            self.assertTrue(allowed, reason)
        allowed, reason = check(["status"], self.framework / "sub", self.framework)
        self.assertTrue(allowed, reason)

    def test_ref_like_arguments_are_not_paths(self):
        allowed, reason = check(
            ["log", "origin/main..main"], self.framework, self.framework
        )
        self.assertTrue(allowed, reason)

    def test_existing_outside_path_argument_refused(self):
        allowed, reason = check(
            ["add", "../KnowledgePalace-vault"], self.framework, self.framework
        )
        self.assertFalse(allowed)
        self.assertIn("resolves to", reason)

    def test_push_requires_explicit_user_authorization(self):
        allowed, reason = check(["push", "origin", "main"], self.framework, self.framework)
        self.assertFalse(allowed)
        self.assertIn("push refused", reason)
        allowed, reason = check(
            ["push", "origin", "main"], self.framework, self.framework, allow_push=True
        )
        self.assertTrue(allowed, reason)

    def test_dangling_dash_c_refused(self):
        allowed, reason = check(["-C"], self.framework, self.framework)
        self.assertFalse(allowed)
        self.assertIn("dangling", reason)


if __name__ == "__main__":
    unittest.main()
