"""Both runtime entries and the mirrored main-agent contract stay identical, and
every runtime adapter points at an existing shared role contract."""

import re
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
CONTRACTS = REPO / "knowledge_palace" / "agents"


class TestMirrors(unittest.TestCase):
    def test_agents_and_claude_are_byte_identical(self):
        self.assertEqual((REPO / "AGENTS.md").read_bytes(), (REPO / "CLAUDE.md").read_bytes())

    def test_both_skill_entries_are_byte_identical(self):
        claude = REPO / ".claude" / "skills" / "palace" / "SKILL.md"
        codex = REPO / ".agents" / "skills" / "palace" / "SKILL.md"
        self.assertEqual(claude.read_bytes(), codex.read_bytes())


class TestAdaptersPointAtContracts(unittest.TestCase):
    def test_every_adapter_names_an_existing_contract(self):
        adapters = sorted((REPO / ".claude" / "agents").glob("palace-*.md")) + sorted(
            (REPO / ".codex" / "agents").glob("palace-*.toml"))
        self.assertEqual(len(adapters), 2 * len(list(CONTRACTS.glob("palace-*.md"))))
        for adapter in adapters:
            text = adapter.read_text(encoding="utf-8")
            named = re.findall(r"knowledge_palace/agents/(palace-[a-z-]+\.md)", text)
            self.assertEqual(named, [adapter.stem + ".md"], adapter)
            self.assertTrue((CONTRACTS / named[0]).is_file(), adapter)


if __name__ == "__main__":
    unittest.main()
