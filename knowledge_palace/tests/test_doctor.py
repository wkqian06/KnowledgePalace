"""Acceptance 2: doctor reports roots + both runtimes' contract completeness,
performs zero writes and zero network calls."""

import hashlib
import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from knowledge_palace.tools.doctor import run, run_checks

REPO = Path(__file__).resolve().parents[2]
FIXTURES = Path(__file__).resolve().parent / "fixtures"
PLAIN_CONFIG = FIXTURES / "roots-plain" / ".palace.toml"

EXPECTED_CHECKS = (
    "config.roots",
    "config.roots-distinct",
    "index.graph",
    "source.cache",
    "providers.institutional",
    "expansion.checkpoints",
    "interaction.sessions",
    "workspace.projects",
    "shared.protocol",
    "shared.role-contracts",
    "shared.templates",
    "runtime.claude",
    "runtime.codex",
)


def tree_digest(base):
    entries = []
    for path in sorted(base.rglob("*")):
        if path.is_file():
            entries.append((str(path), hashlib.sha256(path.read_bytes()).hexdigest()))
        else:
            entries.append((str(path), "dir"))
    return entries


class TestDoctor(unittest.TestCase):
    def test_real_framework_is_complete_for_both_runtimes(self):
        checks = run_checks(REPO, PLAIN_CONFIG)
        names = [name for name, _, _ in checks]
        for expected in EXPECTED_CHECKS:
            self.assertIn(expected, names)
        failures = [(name, detail) for name, ok, detail in checks if not ok]
        self.assertEqual(failures, [])

    def test_broken_framework_reports_failures_with_zero_writes(self):
        with tempfile.TemporaryDirectory() as td:
            broken = Path(td)
            proto = broken / "knowledge_palace" / "protocol"
            proto.mkdir(parents=True)
            (proto / "PROTOCOL.md").write_text("stub", encoding="utf-8")
            before = tree_digest(broken)
            checks = run_checks(broken, PLAIN_CONFIG)
            self.assertEqual(tree_digest(broken), before)  # zero writes
            failed = {name for name, ok, _ in checks if not ok}
            for expected in (
                "shared.protocol",
                "shared.role-contracts",
                "shared.templates",
                "runtime.claude",
                "runtime.codex",
            ):
                self.assertIn(expected, failed)
            detail = {name: d for name, _, d in checks}
            self.assertIn("missing", detail["shared.role-contracts"])

    def test_index_check_fresh_then_stale(self):
        import shutil

        from knowledge_palace.graph.builder import write_index

        mini = FIXTURES / "vault-mini"
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            vault = base / "vault"
            shutil.copytree(mini, vault)
            for name in ("state", "source", "workspace"):
                (base / name).mkdir()
            config = base / ".palace.toml"
            config.write_text(
                'vault_dir = "vault"\nstate_dir = "state"\n'
                'source_dir = "source"\nworkspace_dir = "workspace"\n',
                encoding="utf-8",
            )
            by_name = lambda checks: {name: (ok, detail) for name, ok, detail in checks}
            absent = by_name(run_checks(REPO, config))["index.graph"]
            self.assertTrue(absent[0])
            self.assertIn("rebuildable", absent[1])
            write_index(vault, base / "state")
            fresh = by_name(run_checks(REPO, config))["index.graph"]
            self.assertTrue(fresh[0])
            self.assertIn("fresh", fresh[1])
            with (vault / "papers" / "alpha-2020-echo.md").open("a", encoding="utf-8") as fh:
                fh.write("\n")
            stale = by_name(run_checks(REPO, config))["index.graph"]
            self.assertFalse(stale[0])
            self.assertIn("stale", stale[1])

    def test_cli_exit_codes(self):
        out = io.StringIO()
        with redirect_stdout(out):
            code = run(["--framework", str(REPO), "--config", str(PLAIN_CONFIG)])
        self.assertEqual(code, 0)
        self.assertIn("doctor: ", out.getvalue())
        with tempfile.TemporaryDirectory() as td:
            out = io.StringIO()
            with redirect_stdout(out):
                code = run(["--framework", td, "--config", str(PLAIN_CONFIG)])
            self.assertEqual(code, 1)
            self.assertIn("FAIL", out.getvalue())

    def test_zero_network_surface_in_tool_sources(self):
        tools = REPO / "knowledge_palace" / "tools"
        for name in ("doctor.py", "config_resolver.py"):
            source = (tools / name).read_text(encoding="utf-8")
            for banned in ("socket", "urllib", "http.client", "requests"):
                self.assertNotIn(banned, source, "%s must stay offline" % name)


if __name__ == "__main__":
    unittest.main()
