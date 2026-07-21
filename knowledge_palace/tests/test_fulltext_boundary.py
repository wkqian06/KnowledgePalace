"""Full-text bytes never land under the Vault — proven
behaviorally on the full acquire→promote flow and statically on the sources."""

import hashlib
import shutil
import tempfile
import unittest
from pathlib import Path

from knowledge_palace.acquisition.providers import LocalFileProvider
from knowledge_palace.acquisition.receipt import new_request
from knowledge_palace.acquisition.transaction import promote

CORE = Path(__file__).resolve().parents[1]
MINI = Path(__file__).resolve().parent / "fixtures" / "vault-mini"
DOI = "10.99999/fixture.alpha2020"


def tree_digest(base):
    return [
        (p.relative_to(base).as_posix(), hashlib.sha256(p.read_bytes()).hexdigest())
        for p in sorted(Path(base).rglob("*"))
        if p.is_file()
    ]


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
            vault_before = tree_digest(vault)
            receipt = LocalFileProvider().acquire(
                new_request(work_slug="alpha-2020-echo", ids={"doi": DOI}, local_path=pdf),
                state,
            )
            promote(receipt, state, source)
            self.assertEqual(tree_digest(vault), vault_before)
            self.assertTrue(any(state.rglob("*")))  # staging existed
            self.assertTrue((source / "fulltext" / "alpha-2020-echo.pdf").is_file())

    def test_acquisition_sources_never_reference_vault_writes(self):
        for name in ("receipt.py", "providers.py", "transaction.py"):
            source = (CORE / "acquisition" / name).read_text(encoding="utf-8")
            self.assertNotIn("vault_dir", source, name)
            for marker in ("urllib", "http.client", "socket", "requests"):
                self.assertNotIn(marker, source, "%s must use injected transports" % name)

    def test_promotion_targets_only_the_fulltext_dir(self):
        source = (CORE / "acquisition" / "transaction.py").read_text(encoding="utf-8")
        self.assertIn('FULLTEXT_DIRNAME = "fulltext"', source)
        self.assertEqual(source.count("source /"), 1)  # single destination join


if __name__ == "__main__":
    unittest.main()
