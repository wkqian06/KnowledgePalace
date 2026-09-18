"""Full-text bytes never land under the Vault on the acquire→promote flow."""

import shutil
import tempfile
import unittest
from pathlib import Path

from knowledge_palace.acquisition.providers import LocalFileProvider
from knowledge_palace.acquisition.receipt import new_request
from knowledge_palace.acquisition.transaction import promote
from knowledge_palace.graph.builder import vault_fingerprint

MINI = Path(__file__).resolve().parent / "fixtures" / "vault-mini"
DOI = "10.99999/fixture.alpha2020"


class TestFulltextBoundary(unittest.TestCase):
    def test_full_flow_writes_only_state_and_source(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            state, source, vault = base / "state", base / "sources", base / "vault"
            state.mkdir()
            (source / "fulltext").mkdir(parents=True)
            shutil.copytree(MINI, vault)
            pdf = base / "paper.pdf"
            pdf.write_bytes(b"%PDF-1.4 body")
            (base / "paper.txt").write_bytes(("doi:%s text" % DOI).encode())
            vault_before = vault_fingerprint(vault)
            receipt = LocalFileProvider().acquire(
                new_request(work_slug="alpha-2020-echo", ids={"doi": DOI}, local_path=pdf),
                state,
            )
            promote(receipt, state, source)
            self.assertEqual(vault_fingerprint(vault), vault_before)
            self.assertFalse(list(vault.rglob("*.pdf")) + list(vault.rglob("*.txt")))
            self.assertTrue(any(state.rglob("*")))  # staging existed
            self.assertTrue((source / "fulltext" / "alpha-2020-echo.pdf").is_file())


if __name__ == "__main__":
    unittest.main()
