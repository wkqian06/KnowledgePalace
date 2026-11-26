"""Author-supplied reference strings resolve Vault-first through the research CLI's parser."""

import unittest
from pathlib import Path

from knowledge_palace.graph.identity import load_vault_identity
from knowledge_palace.interaction.project_source import resolve
from knowledge_palace.interaction.research import reference_from_text

MINI = Path(__file__).resolve().parent / "fixtures" / "vault-mini"


class TestReferenceFromText(unittest.TestCase):
    def test_identifier_forms(self):
        arxiv = {"ids": {"arxiv": "2101.00001"}}
        for text in ("arXiv:2101.00001v3", "https://arxiv.org/abs/2101.00001", "2101.00001v2"):
            self.assertEqual(reference_from_text(text), arxiv, text)
        for text in ("hep-th/9901001", "arXiv:hep-th/9901001"):
            self.assertEqual(reference_from_text(text), {"ids": {"arxiv": "hep-th/9901001"}}, text)
        self.assertEqual(reference_from_text("Alpha, A. (2020). Echo. https://doi.org/10.99999/Fixture.Alpha2020."),
                         {"ids": {"doi": "10.99999/fixture.alpha2020"}})
        self.assertEqual(reference_from_text("Echo Cancellation in Alpha Systems"),
                         {"title": "Echo Cancellation in Alpha Systems"})

    def test_library_hits(self):
        identity = load_vault_identity(MINI)
        self.assertEqual(resolve(reference_from_text("10.99999/fixture.alpha2020"), identity),
                         {"kind": "vault-hit", "work": "work:alpha-2020-echo"})
        self.assertEqual(resolve(reference_from_text("10.48550/arXiv.2101.00001"), identity)["work"],
                         "work:beta-2021-foxtrot")
        missing = resolve(reference_from_text("An Unread Paper"), identity)
        self.assertEqual((missing["kind"], missing["verified"]), ("project-source", False))


if __name__ == "__main__":
    unittest.main()
