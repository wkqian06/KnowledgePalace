"""Promotion only for verified material inside the
confirmed transaction; rejection changes nothing; snapshots are immutable;
staging is deletable Derived State."""

import hashlib
import shutil
import tempfile
import unittest
from pathlib import Path

from knowledge_palace.acquisition.providers import AcquisitionError, LocalFileProvider
from knowledge_palace.acquisition.receipt import new_request
from knowledge_palace.acquisition.transaction import promote

MINI = Path(__file__).resolve().parent / "fixtures" / "vault-mini"
DOI = "10.99999/fixture.alpha2020"
PDF_BYTES = b"%PDF-1.4 fake fixture body"
TXT_BYTES = ("Echo Cancellation in Alpha Systems\ndoi:%s\nbody" % DOI).encode()


def tree_digest(base):
    return [
        (p.relative_to(base).as_posix(), hashlib.sha256(p.read_bytes()).hexdigest())
        for p in sorted(Path(base).rglob("*"))
        if p.is_file()
    ]


class TransactionCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        base = Path(self._tmp.name)
        self.state = base / "state"
        self.source = base / "sources"
        self.vault = base / "vault"
        self.state.mkdir()
        (self.source / "fulltext").mkdir(parents=True)
        shutil.copytree(MINI, self.vault)
        pdf = base / "paper.pdf"
        pdf.write_bytes(PDF_BYTES)
        (base / "paper.txt").write_bytes(TXT_BYTES)
        self.request = new_request(
            work_slug="alpha-2020-echo", ids={"doi": DOI}, local_path=pdf
        )

    def acquire(self, **request_overrides):
        request = dict(self.request)
        request.update(request_overrides)
        return LocalFileProvider().acquire(request, self.state)


class TestPromotion(TransactionCase):
    def test_verified_receipt_promotes_pdf_and_txt(self):
        receipt = self.acquire()
        result = promote(receipt, self.state, self.source)
        self.assertEqual(result["status"], "promoted")
        locals_ = sorted(entry["local"] for entry in result["files"])
        self.assertEqual(
            locals_, ["fulltext/alpha-2020-echo.pdf", "fulltext/alpha-2020-echo.txt"]
        )
        self.assertEqual(
            (self.source / "fulltext" / "alpha-2020-echo.pdf").read_bytes(), PDF_BYTES
        )

    def test_repromotion_is_idempotent(self):
        receipt = self.acquire()
        promote(receipt, self.state, self.source)
        before = tree_digest(self.source)
        result = promote(receipt, self.state, self.source)
        self.assertEqual(result["status"], "already-present")
        self.assertEqual(tree_digest(self.source), before)

    def test_differing_existing_snapshot_is_refused(self):
        (self.source / "fulltext" / "alpha-2020-echo.pdf").write_bytes(b"OTHER BYTES")
        receipt = self.acquire()
        before = tree_digest(self.source)
        with self.assertRaises(AcquisitionError) as ctx:
            promote(receipt, self.state, self.source)
        self.assertIn("refusing to overwrite", str(ctx.exception))
        self.assertEqual(tree_digest(self.source), before)  # nothing half-written

    def test_unverified_and_quarantined_are_refused(self):
        bare_pdf = Path(self._tmp.name) / "bare.pdf"
        bare_pdf.write_bytes(PDF_BYTES)
        unverified = LocalFileProvider().acquire(
            new_request(work_slug="w", ids={"doi": DOI}, local_path=bare_pdf), self.state
        )
        self.assertEqual(unverified["identity_status"], "unverified")
        with self.assertRaises(AcquisitionError):
            promote(unverified, self.state, self.source)
        mismatched = self.acquire(expected_sha256="0" * 64)
        self.assertTrue(mismatched["quarantined"])
        with self.assertRaises(AcquisitionError):
            promote(mismatched, self.state, self.source)

    def test_rejection_means_nothing_changes(self):
        vault_before = tree_digest(self.vault)
        source_before = tree_digest(self.source)
        self.acquire()  # staged only; user rejects → promote is never called
        self.assertEqual(tree_digest(self.vault), vault_before)
        self.assertEqual(tree_digest(self.source), source_before)

    def test_staging_is_deletable_derived_state(self):
        receipt = self.acquire()
        promote(receipt, self.state, self.source)
        shutil.rmtree(self.state / "acquisition")
        self.assertEqual(
            sorted(p.name for p in (self.source / "fulltext").iterdir()),
            ["alpha-2020-echo.pdf", "alpha-2020-echo.txt"],
        )
        written = {p.relative_to(self.state).parts[0] for p in self.state.rglob("*")}
        self.assertEqual(written, set())  # state held nothing but acquisition/


if __name__ == "__main__":
    unittest.main()
