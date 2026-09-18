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
from knowledge_palace.acquisition.transaction import promote, save_paper
from knowledge_palace.graph.builder import vault_fingerprint

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


NEW_CARD = """---
slug: delta-2024-drift
title: "Drift Compensation in Delta Systems"
year: 2024
venue: "Fixture Letters"
source: "10.99999/fixture.delta2024"
added: 2026-09-13
read_depth: full
source_coverage: full-text
domain: [alpha-domain]
---

# Drift Compensation in Delta Systems

## Claims

- C1 [concept-echo]: "Drift is compensated by delta." — §2 [¶1] / p.2
"""


class TestSavePaper(TransactionCase):
    def test_new_card_is_written_with_its_index_row(self):
        result = save_paper(self.vault, NEW_CARD)
        self.assertEqual((result["status"], result["new_claims"]), ("created", 1))
        card = self.vault / "papers" / "delta-2024-drift.md"
        self.assertEqual(card.read_text(encoding="utf-8"), NEW_CARD)
        index = (self.vault / "papers" / "INDEX.md").read_text(encoding="utf-8")
        self.assertIn("| delta-2024-drift |", index)

    def test_duplicate_identity_under_another_slug_is_refused(self):
        same_doi = NEW_CARD.replace("fixture.delta2024", "fixture.alpha2020")
        with self.assertRaises(ValueError) as ctx:
            save_paper(self.vault, same_doi)
        self.assertIn("already exists as alpha-2020-echo", str(ctx.exception))
        same_title = NEW_CARD.replace(
            "Drift Compensation in Delta Systems", "Echo Cancellation in Alpha Systems")
        with self.assertRaises(ValueError):
            save_paper(self.vault, same_title)
        self.assertFalse((self.vault / "papers" / "delta-2024-drift.md").exists())

    def test_existing_card_keeps_old_claims_and_accepts_new_ones(self):
        text = (self.vault / "papers" / "alpha-2020-echo.md").read_text(encoding="utf-8")
        save_paper(self.vault, text)  # first save normalizes the INDEX row
        before = vault_fingerprint(self.vault)
        self.assertEqual(save_paper(self.vault, text)["status"], "unchanged")
        self.assertEqual(vault_fingerprint(self.vault), before)
        altered = text.replace('"Echo cancellation improves by delta."', '"Echo cancellation improves."')
        with self.assertRaises(ValueError) as ctx:
            save_paper(self.vault, altered)
        self.assertIn("C1's new quote is not verbatim", str(ctx.exception))
        self.assertEqual(vault_fingerprint(self.vault), before)
        # A provenance check that relocates an intact quote may fix its anchor.
        relocated = text.replace("— §2 [¶1] / p.2", "— §3 [¶4] / p.5")
        self.assertEqual(save_paper(self.vault, relocated)["status"], "updated")
        save_paper(self.vault, text)  # restore the fixture anchor for the rest
        extended = text.replace(
            "## Study profile",
            '- C3 [concept-echo]: "A later reading adds this." — §6 / p.10\n\n## Study profile')
        result = save_paper(self.vault, extended)
        self.assertEqual((result["status"], result["new_claims"]), ("updated", 1))

    def test_quote_repair_needs_the_source_to_carry_the_new_wording(self):
        text = (self.vault / "papers" / "alpha-2020-echo.md").read_text(encoding="utf-8")
        save_paper(self.vault, text)
        (self.source / "fulltext" / "alpha-2020-echo.txt").write_text(
            "Body. Echo cancellation improves by delta\nfactors. More body.", encoding="utf-8")
        repaired = text.replace(
            '"Echo cancellation improves by delta."',
            '"Echo cancellation improves by delta factors."')
        # the source cannot be consulted, so the old wording must come back unchanged
        with self.assertRaises(ValueError) as ctx:
            save_paper(self.vault, repaired)
        self.assertIn("C1's new quote is not verbatim", str(ctx.exception))
        # with the source, a repair toward it is accepted across its line break
        self.assertEqual(save_paper(self.vault, repaired, source_dir=self.source)["status"], "updated")
        # but wording the source does not carry stays refused
        invented = repaired.replace("by delta factors.", "by a wide margin.")
        before = vault_fingerprint(self.vault)
        with self.assertRaises(ValueError):
            save_paper(self.vault, invented, source_dir=self.source)
        self.assertEqual(vault_fingerprint(self.vault), before)

    def test_ocr_text_cannot_authorize_a_quote_repair(self):
        text = (self.vault / "papers" / "alpha-2020-echo.md").read_text(encoding="utf-8")
        save_paper(self.vault, text)
        # an OCR cache says the page as the scanner read it, typos and all
        (self.source / "fulltext" / "alpha-2020-echo.txt").write_text(
            "TOOL: RapidOCR on 300dpi renders\n\nEcho cancellatlon improves by delta.",
            encoding="utf-8")
        toward_ocr = text.replace(
            '"Echo cancellation improves by delta."', '"Echo cancellatlon improves by delta."')
        before = vault_fingerprint(self.vault)
        with self.assertRaises(ValueError):
            save_paper(self.vault, toward_ocr, source_dir=self.source)
        self.assertEqual(vault_fingerprint(self.vault), before)

    def test_retracted_claim_stays_but_stops_being_citable(self):
        text = (self.vault / "papers" / "alpha-2020-echo.md").read_text(encoding="utf-8")
        save_paper(self.vault, text)
        retracted = text.replace(
            "\n## Study profile",
            '\n- Retraction of C2 (2026-09-18): not this paper; it is beta-2021-drift\'s.\n'
            "\n## Study profile")
        self.assertEqual(save_paper(self.vault, retracted)["status"], "updated")
        cited = retracted.replace(
            "\n## Limitations & gaps",
            "\n## Argument\n\n"
            "| Role | Claim | Paraphrase | Attribution | Scope |\n"
            "|---|---|---|---|---|\n"
            "| remaining | C2 | Noise is unresolved | author | fixture |\n"
            "\n## Limitations & gaps")
        with self.assertRaises(ValueError) as ctx:
            save_paper(self.vault, cited)
        self.assertIn("Argument row cites retracted C2", str(ctx.exception))

    def test_reading_depth_must_match_the_material(self):
        cases = (
            ("read_depth: full", "read_depth: metadata", "metadata-only material"),
            ("source_coverage: full-text", "source_coverage: abstract", "limited source coverage"),
            ("source_coverage: full-text", "source_coverage: fulltext", "source_coverage must be"),
        )
        for old, new, message in cases:
            with self.assertRaises(ValueError) as ctx:
                save_paper(self.vault, NEW_CARD.replace(old, new))
            self.assertIn(message, str(ctx.exception))
        self.assertFalse((self.vault / "papers" / "delta-2024-drift.md").exists())


if __name__ == "__main__":
    unittest.main()
