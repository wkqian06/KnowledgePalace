"""Acceptance 4: nine read-only role contracts in both runtimes, thin adapters
that do not duplicate protocol bodies, and byte-identical AGENTS/CLAUDE
mirrors."""

import unittest
from pathlib import Path

from knowledge_palace.tools import ROLES

REPO = Path(__file__).resolve().parents[2]

# Section markers that may exist ONLY in the shared core, never in adapters.
FORBIDDEN_PROTOCOL_MARKERS = (
    "## Storage resolution",
    "## Write invariants",
    "## Weight rules",
    "## Multi-domain rules",
    "## Governance invariants",
    "# Hard limits",
    "### Ingest (single or batch)",
)

MAX_ADAPTER_MD = 2500
MAX_ADAPTER_TOML = 1500
MAX_SKILL = 6000


def _assert_no_protocol_body(testcase, path, text):
    for marker in FORBIDDEN_PROTOCOL_MARKERS:
        testcase.assertNotIn(marker, text, "%s duplicates protocol: %r" % (path, marker))


class TestMirrors(unittest.TestCase):
    def test_agents_and_claude_are_byte_identical(self):
        self.assertEqual(
            (REPO / "AGENTS.md").read_bytes(), (REPO / "CLAUDE.md").read_bytes()
        )


class TestSharedContracts(unittest.TestCase):
    def test_nine_full_contracts_exist(self):
        self.assertEqual(len(ROLES), 9)
        for role in ROLES:
            contract = REPO / "knowledge_palace" / "agents" / ("palace-%s.md" % role)
            self.assertTrue(contract.is_file(), contract)
            text = contract.read_text(encoding="utf-8")
            self.assertIn("# Hard limits", text, role)
            self.assertIn("## Verdict", text, role)
            self.assertIn("NEVER write, edit, or create files", text, role)


class TestClaudeAdapters(unittest.TestCase):
    def test_thin_readonly_and_pointing_at_shared_contract(self):
        for role in ROLES:
            adapter = REPO / ".claude" / "agents" / ("palace-%s.md" % role)
            self.assertTrue(adapter.is_file(), adapter)
            raw = adapter.read_bytes()
            self.assertLessEqual(len(raw), MAX_ADAPTER_MD, adapter)
            text = raw.decode("utf-8")
            self.assertIn("tools: Read, Grep, Glob", text, adapter)
            self.assertIn("name: palace-%s" % role, text)
            self.assertIn("knowledge_palace/agents/palace-%s.md" % role, text)
            _assert_no_protocol_body(self, adapter, text)


class TestCodexAdapters(unittest.TestCase):
    def test_thin_readonly_sandbox_no_model_pin(self):
        for role in ROLES:
            adapter = REPO / ".codex" / "agents" / ("palace-%s.toml" % role)
            self.assertTrue(adapter.is_file(), adapter)
            raw = adapter.read_bytes()
            self.assertLessEqual(len(raw), MAX_ADAPTER_TOML, adapter)
            text = raw.decode("utf-8")
            self.assertIn('sandbox_mode = "read-only"', text, adapter)
            self.assertIn('name = "palace-%s"' % role, text)
            self.assertIn("knowledge_palace/agents/palace-%s.md" % role, text)
            for line in text.splitlines():
                self.assertFalse(
                    line.strip().startswith("model ="),
                    "%s pins a model: %r" % (adapter, line),
                )
            _assert_no_protocol_body(self, adapter, text)


class TestSkillEntries(unittest.TestCase):
    def test_both_runtime_entries_are_thin_routers(self):
        entries = (
            REPO / ".claude" / "skills" / "knowledge-palace" / "SKILL.md",
            REPO / ".agents" / "skills" / "knowledge-palace" / "SKILL.md",
        )
        for entry in entries:
            self.assertTrue(entry.is_file(), entry)
            raw = entry.read_bytes()
            self.assertLessEqual(len(raw), MAX_SKILL, entry)
            text = raw.decode("utf-8")
            for pointer in (
                "knowledge_palace/protocol/PROTOCOL.md",
                "knowledge_palace/protocol/COMMANDS.md",
                "knowledge_palace/protocol/GRAPH_QUERY_PORT.md",
                "knowledge_palace.tools.task_package",
                "knowledge_palace.tools.git_guard",
            ):
                self.assertIn(pointer, text, entry)
            _assert_no_protocol_body(self, entry, text)

    def test_codex_skill_metadata_exists_without_protocol(self):
        meta = (
            REPO / ".agents" / "skills" / "knowledge-palace" / "agents" / "openai.yaml"
        )
        self.assertTrue(meta.is_file())
        text = meta.read_text(encoding="utf-8")
        self.assertIn("knowledge-palace", text)
        _assert_no_protocol_body(self, meta, text)


if __name__ == "__main__":
    unittest.main()
