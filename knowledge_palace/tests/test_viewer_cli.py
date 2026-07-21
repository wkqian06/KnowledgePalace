"""Output-path confinement and atomic writes."""

import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from knowledge_palace.graph.builder import write_index
from knowledge_palace.tools.config_resolver import resolve_roots
from knowledge_palace.viewer import cli

MINI = Path(__file__).resolve().parent / "fixtures" / "vault-mini"


class CliCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        self.vault = self.root / "vault"
        shutil.copytree(MINI, self.vault)
        self.state = self.root / "state"
        write_index(self.vault, self.state)
        self.source = self.root / "source"
        self.source.mkdir()
        self.workspace = self.root / "workspace"
        self.workspace.mkdir()
        self.toml = self.root / ".palace.toml"
        self.toml.write_text(
            'vault_dir = "vault"\nstate_dir = "state"\n'
            'source_dir = "source"\nworkspace_dir = "workspace"\n',
            encoding="utf-8",
        )
        self.roots = resolve_roots(str(self.toml))


class TestOutputPathConfinement(CliCase):
    def test_private_root_paths_rejected(self):
        for path in (
            self.vault / "sneaky.html",
            self.state / "sneaky.html",
            self.source / "sneaky.html",
            self.workspace / "sneaky.html",
        ):
            with self.assertRaises(ValueError):
                cli.resolve_output_path(str(path), self.roots)

    def test_outside_path_accepted(self):
        target = cli.resolve_output_path(str(self.root / "outside" / "v.html"), self.roots)
        self.assertEqual(target, (self.root / "outside" / "v.html").resolve())


class TestRunErrorHandling(CliCase):
    def test_private_root_output_reported_cleanly_not_a_traceback(self):
        code = cli.run([str(self.vault / "sneaky.html"), "--config", str(self.toml)])
        self.assertEqual(code, 1)

    def test_missing_config_reported_cleanly(self):
        code = cli.run(["--config", str(self.root / "no-such.toml")])
        self.assertEqual(code, 1)


class TestAtomicWrite(CliCase):
    def test_successful_export_writes_one_file_no_temp_litter(self):
        out = self.root / "outside" / "viewer.html"
        target = cli.export(str(out), str(self.toml))
        self.assertTrue(target.is_file())
        leftovers = list(target.parent.glob("*.part"))
        self.assertEqual(leftovers, [])

    def test_failed_render_leaves_no_partial_file_and_preserves_existing(self):
        out = self.root / "outside" / "viewer.html"
        out.parent.mkdir(parents=True)
        out.write_text("previous good export", encoding="utf-8")
        with mock.patch(
            "knowledge_palace.viewer.cli.render", side_effect=RuntimeError("boom")
        ):
            with self.assertRaises(RuntimeError):
                cli.export(str(out), str(self.toml))
        self.assertEqual(out.read_text(encoding="utf-8"), "previous good export")
        self.assertEqual(list(out.parent.glob("*.part")), [])

    def test_rerun_overwrites_cleanly(self):
        out = self.root / "outside" / "viewer.html"
        cli.export(str(out), str(self.toml))
        first = out.read_bytes()
        second_target = cli.export(str(out), str(self.toml))
        self.assertEqual(second_target, out.resolve())
        self.assertEqual(out.read_bytes(), first)  # same index state → identical bytes


if __name__ == "__main__":
    unittest.main()
