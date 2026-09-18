"""Acceptance 1: CWD-independent four-root resolution, strict config parsing,
distinctness validation, spaces-and-Unicode layout."""

import io
import os
import tempfile
import unittest
from contextlib import contextmanager, redirect_stderr, redirect_stdout
from pathlib import Path

from knowledge_palace.tools.config_resolver import (
    REQUIRED_KEYS,
    ConfigError,
    framework_root,
    parse_palace_toml,
    resolve_roots,
    run,
)

REPO = Path(__file__).resolve().parents[2]
FIXTURES = Path(__file__).resolve().parent / "fixtures"
PLAIN_CONFIG = FIXTURES / "roots-plain" / ".palace.toml"
UNICODE_CONFIG = FIXTURES / "roots-unicode" / ".palace.toml"


@contextmanager
def chdir(path):
    previous = os.getcwd()
    os.chdir(str(path))
    try:
        yield
    finally:
        os.chdir(previous)


class TestParser(unittest.TestCase):
    def test_exact_four_keys_parse(self):
        values = parse_palace_toml(PLAIN_CONFIG.read_text(encoding="utf-8"))
        self.assertEqual(tuple(sorted(values)), tuple(sorted(REQUIRED_KEYS)))

    def test_rejections_carry_line_evidence(self):
        cases = {
            'vault_dir = unquoted\n': "double-quoted",
            "vault_dir = 'single'\n": "double-quoted",
            "[section]\n": "expected",
            'vault_dir = "a" # trailing\n': "double-quoted",
            'vault_dir = "a"\nvault_dir = "b"\n': "duplicate key",
        }
        for text, needle in cases.items():
            with self.assertRaises(ConfigError) as ctx:
                parse_palace_toml(
                    text
                    + 'state_dir = "s"\nsource_dir = "c"\nworkspace_dir = "w"\n'
                )
            self.assertIn(needle, str(ctx.exception))

    def test_missing_and_extra_keys(self):
        with self.assertRaises(ConfigError) as ctx:
            parse_palace_toml('vault_dir = "v"\n')
        self.assertIn("missing", str(ctx.exception))
        full = 'vault_dir = "v"\nstate_dir = "s"\nsource_dir = "c"\nworkspace_dir = "w"\n'
        with self.assertRaises(ConfigError) as ctx:
            parse_palace_toml(full + 'bonus_dir = "b"\n')
        self.assertIn("extra", str(ctx.exception))


class TestResolution(unittest.TestCase):
    def test_identical_from_framework_nested_and_tmp(self):
        expected = resolve_roots(PLAIN_CONFIG)
        with tempfile.TemporaryDirectory() as td:
            for cwd in (REPO, REPO / "knowledge_palace" / "tools", Path(td)):
                with chdir(cwd):
                    self.assertEqual(resolve_roots(PLAIN_CONFIG), expected, cwd)

    def test_default_real_config_from_three_cwds(self):
        real = framework_root() / ".palace.toml"
        if not real.is_file():
            self.skipTest("no real .palace.toml on this machine")
        try:
            expected = resolve_roots(None)
        except ConfigError as err:
            self.skipTest("real roots not deployed here: %s" % err)
        with tempfile.TemporaryDirectory() as td:
            for cwd in (REPO, REPO / "knowledge_palace" / "tools", Path(td)):
                with chdir(cwd):
                    self.assertEqual(resolve_roots(None), expected, cwd)

    def test_spaces_and_unicode_layout(self):
        roots = resolve_roots(UNICODE_CONFIG)
        self.assertEqual(len(set(roots.values())), 4)
        vault = roots["vault_dir"]
        self.assertTrue(vault.is_dir())
        self.assertIn("Palace Vault α β", str(vault))
        self.assertIn("vault 库", str(vault))

    def test_distinctness_violation(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            (base / "same").mkdir()
            (base / "other").mkdir()
            (base / "third").mkdir()
            config = base / ".palace.toml"
            config.write_text(
                'vault_dir = "same"\nstate_dir = "./same"\n'
                'source_dir = "other"\nworkspace_dir = "third"\n',
                encoding="utf-8",
            )
            with self.assertRaises(ConfigError) as ctx:
                resolve_roots(config)
            self.assertIn("same directory", str(ctx.exception))

    def test_missing_root_directory(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            for name in ("state", "source", "workspace"):
                (base / name).mkdir()
            config = base / ".palace.toml"
            config.write_text(
                'vault_dir = "nope"\nstate_dir = "state"\n'
                'source_dir = "source"\nworkspace_dir = "workspace"\n',
                encoding="utf-8",
            )
            with self.assertRaises(ConfigError) as ctx:
                resolve_roots(config)
            self.assertIn("not an existing directory", str(ctx.exception))

    def test_config_not_found(self):
        with self.assertRaises(ConfigError) as ctx:
            resolve_roots("/nonexistent/.palace.toml")
        self.assertIn("config not found", str(ctx.exception))


class TestCli(unittest.TestCase):
    def test_prints_four_roots_and_exits_zero(self):
        out = io.StringIO()
        with redirect_stdout(out):
            code = run(["--config", str(PLAIN_CONFIG)])
        self.assertEqual(code, 0)
        lines = out.getvalue().strip().splitlines()
        self.assertEqual(len(lines), 4)
        self.assertTrue(lines[0].startswith("vault_dir = "))
        self.assertTrue(Path(lines[0].split(" = ", 1)[1]).is_absolute())

    def test_check_mode_is_quiet(self):
        out = io.StringIO()
        with redirect_stdout(out):
            code = run(["--config", str(PLAIN_CONFIG), "--check"])
        self.assertEqual(code, 0)
        self.assertEqual(out.getvalue(), "")

    def test_error_exit_code(self):
        err = io.StringIO()
        with redirect_stderr(err):
            code = run(["--config", "/nonexistent/.palace.toml"])
        self.assertEqual(code, 2)
        self.assertIn("config error", err.getvalue())


if __name__ == "__main__":
    unittest.main()
