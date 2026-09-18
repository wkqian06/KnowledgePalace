"""Providers return one receipt schema over injected
transports; failures are typed with zero partial staging; Zotero stays
read-only; the institutional stub always refuses."""

import json
import tempfile
import unittest
from pathlib import Path

from knowledge_palace.acquisition.providers import (
    AcquisitionError,
    InstitutionalAccessProvider,
    LocalFileProvider,
    OpenAccessProvider,
    ZoteroReadOnlyProvider,
    acquire_via,
)
from knowledge_palace.acquisition.receipt import new_request, validate_receipt
from knowledge_palace.metadata.cache import BibliographicCache

DOI = "10.99999/fixture.alpha2020"
PDF_BYTES = b"%PDF-1.4 fake fixture body"
TXT_BYTES = ("Echo Cancellation in Alpha Systems\ndoi:%s\nbody text" % DOI).encode()

OPENALEX_WITH_OA = json.dumps(
    {
        "id": "https://openalex.org/W1234567",
        "doi": "https://doi.org/" + DOI,
        "display_name": "Echo Cancellation in Alpha Systems",
        "publication_year": 2020,
        "cited_by_count": 42,
        "topics": [],
        "primary_location": {"source": {"display_name": "Fixture Letters"}},
        "best_oa_location": {"pdf_url": "https://oa.example/alpha.pdf"},
    }
).encode()


class RoutedStub:
    def __init__(self, routes):
        self.routes = routes
        self.calls = []

    def __call__(self, url, headers=None):
        self.calls.append(url)
        for needle, payload in self.routes.items():
            if needle in url:
                if isinstance(payload, Exception):
                    raise payload
                return payload
        raise AssertionError("unrouted url: %s" % url)


class AcquisitionCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.base = Path(self._tmp.name)
        self.state = self.base / "state"
        self.state.mkdir()

    def staged_files(self):
        root = self.state / "acquisition"
        return sorted(p.name for p in root.rglob("*") if p.is_file()) if root.is_dir() else []


class TestLocalProvider(AcquisitionCase):
    def make_local(self, with_txt=True):
        pdf = self.base / "paper.pdf"
        pdf.write_bytes(PDF_BYTES)
        if with_txt:
            (self.base / "paper.txt").write_bytes(TXT_BYTES)
        return pdf

    def test_pdf_with_txt_companion_is_fully_eligible_material(self):
        pdf = self.make_local()
        request = new_request(work_slug="alpha-2020-echo", ids={"doi": DOI}, local_path=pdf)
        receipt = LocalFileProvider().acquire(request, self.state)
        self.assertEqual(validate_receipt(receipt), [])
        self.assertEqual(receipt["acquisition_status"], "acquired")
        self.assertEqual(receipt["text_status"], "ready")
        self.assertEqual(receipt["identity_status"], "verified")  # DOI in txt head
        self.assertEqual(len(receipt["sha256"]), 64)
        self.assertTrue(receipt["staged_path"].startswith("acquisition/staging/"))
        self.assertEqual(
            self.staged_files(), ["alpha-2020-echo.pdf", "alpha-2020-echo.txt"]
        )

    def test_bare_pdf_stays_not_attempted_and_unverified(self):
        pdf = self.make_local(with_txt=False)
        receipt = LocalFileProvider().acquire(
            new_request(work_slug="w", ids={"doi": DOI}, local_path=pdf), self.state
        )
        self.assertEqual(receipt["text_status"], "not_attempted")
        self.assertEqual(receipt["identity_status"], "unverified")
        self.assertIn("confirmation", receipt["next_action"])

    def test_missing_file_is_not_found(self):
        receipt = LocalFileProvider().acquire(
            new_request(local_path=self.base / "ghost.pdf"), self.state
        )
        self.assertEqual(receipt["acquisition_status"], "not_found")
        self.assertEqual(self.staged_files(), [])

    def test_sha_mismatch_quarantines(self):
        pdf = self.make_local()
        request = new_request(
            work_slug="w", ids={"doi": DOI}, local_path=pdf, expected_sha256="0" * 64
        )
        receipt = LocalFileProvider().acquire(request, self.state)
        self.assertEqual(receipt["identity_status"], "mismatch")
        self.assertTrue(receipt["quarantined"])
        self.assertTrue(receipt["staged_path"].endswith(".quarantine"))
        self.assertEqual(validate_receipt(receipt), [])
        self.assertEqual(
            self.staged_files(), ["w.pdf.quarantine", "w.txt.quarantine"]
        )

    def test_direct_txt_mismatch_quarantines_once_without_crash(self):
        txt = self.base / "paper.txt"
        txt.write_bytes(TXT_BYTES)
        request = new_request(
            work_slug="w", ids={"doi": DOI}, local_path=txt, expected_sha256="0" * 64
        )
        receipt = LocalFileProvider().acquire(request, self.state)
        self.assertEqual(receipt["identity_status"], "mismatch")
        self.assertTrue(receipt["quarantined"])
        self.assertEqual(receipt["staged_path"], receipt["staged_text_path"])
        self.assertTrue(receipt["staged_path"].endswith(".quarantine"))
        self.assertEqual(self.staged_files(), ["w.txt.quarantine"])
        self.assertEqual(validate_receipt(receipt), [])


class TestOpenAccessProvider(AcquisitionCase):
    def test_download_via_stub_transport(self):
        stub = RoutedStub(
            {"/works/doi:": OPENALEX_WITH_OA, "oa.example": PDF_BYTES}
        )
        provider = OpenAccessProvider(fetch=stub, cache=BibliographicCache(self.state))
        receipt = provider.acquire(
            new_request(work_slug="alpha-2020-echo", ids={"doi": DOI}), self.state
        )
        self.assertEqual(validate_receipt(receipt), [])
        self.assertEqual(receipt["acquisition_status"], "acquired")
        self.assertEqual(receipt["locator"], "https://oa.example/alpha.pdf")
        self.assertTrue(receipt["staged_path"].endswith(".pdf"))
        self.assertEqual(receipt["text_status"], "not_attempted")

    def test_cache_only_run_is_gated_not_fetched(self):
        provider = OpenAccessProvider(fetch=None, cache=BibliographicCache(self.state))
        receipt = provider.acquire(new_request(ids={"doi": DOI}), self.state)
        self.assertEqual(receipt["acquisition_status"], "failed")
        self.assertIn("network-acquisition authorization", receipt["next_action"])
        self.assertEqual(self.staged_files(), [])

    def test_download_failure_leaves_no_partial_staging(self):
        stub = RoutedStub(
            {"/works/doi:": OPENALEX_WITH_OA, "oa.example": IOError("reset")}
        )
        provider = OpenAccessProvider(fetch=stub, cache=BibliographicCache(self.state))
        receipt = provider.acquire(new_request(ids={"doi": DOI}), self.state)
        self.assertEqual(receipt["acquisition_status"], "failed")
        self.assertEqual(self.staged_files(), [])
        self.assertEqual(validate_receipt(receipt), [])


class TestZoteroProvider(AcquisitionCase):
    def routes(self):
        return {
            "items?q=": json.dumps([{"key": "ITEMKEY1"}]).encode(),
            "/children": json.dumps(
                [{"key": "ATTKEY1", "data": {"contentType": "application/pdf"}}]
            ).encode(),
            "/file": PDF_BYTES,
        }

    def test_local_api_first_and_stable_keys(self):
        stub = RoutedStub(self.routes())
        provider = ZoteroReadOnlyProvider(fetch=stub)
        receipt = provider.acquire(
            new_request(work_slug="w", ids={"doi": DOI}), self.state
        )
        self.assertEqual(receipt["acquisition_status"], "acquired")
        self.assertEqual(receipt["locator"], "zotero:ITEMKEY1")
        self.assertTrue(stub.calls[0].startswith("http://localhost:23119/api/users/0"))
        self.assertEqual(validate_receipt(receipt), [])

    def test_gated_without_transport(self):
        receipt = ZoteroReadOnlyProvider(fetch=None).acquire(
            new_request(ids={"doi": DOI}), self.state
        )
        self.assertEqual(receipt["acquisition_status"], "failed")
        self.assertIn("network-acquisition authorization", receipt["next_action"])

    def test_surface_is_read_only(self):
        provider = ZoteroReadOnlyProvider()
        public = [n for n in dir(provider) if not n.startswith("_")]
        for banned in ("write", "post", "put", "delete", "create", "update"):
            self.assertFalse(
                any(banned in name.lower() for name in public),
                "zotero provider must expose no %s surface" % banned,
            )
        source = Path(
            __import__("knowledge_palace.acquisition.providers", fromlist=["x"]).__file__
        ).read_text(encoding="utf-8")
        # Usage markers, not prose: the docstring legitimately STATES the bans.
        self.assertNotIn("sqlite3", source)
        self.assertNotIn(".sqlite", source)
        for api_path in ("/notes", "/annotations", "/tags", "/collections"):
            self.assertNotIn(api_path, source, "read-only surface must not touch %s" % api_path)
        for method in ('"POST"', '"PUT"', '"DELETE"', '"PATCH"'):
            self.assertNotIn(method, source)


class TestInstitutionalStubAndChain(AcquisitionCase):
    def test_stub_always_refuses_with_typed_error(self):
        provider = InstitutionalAccessProvider()
        self.assertEqual(provider.maturity, "experimental (disabled)")
        with self.assertRaises(AcquisitionError) as ctx:
            provider.acquire(new_request(), self.state)
        self.assertIn("experimental", str(ctx.exception))

    def test_acquire_via_survives_a_refusing_provider(self):
        pdf = self.base / "paper.pdf"
        pdf.write_bytes(PDF_BYTES)
        (self.base / "paper.txt").write_bytes(TXT_BYTES)
        request = new_request(work_slug="w", ids={"doi": DOI}, local_path=pdf)
        receipt = acquire_via(
            [InstitutionalAccessProvider(), LocalFileProvider()], request, self.state
        )
        self.assertEqual(receipt["acquisition_status"], "acquired")
        self.assertEqual(receipt["channel"], "local")
        self.assertTrue(
            any(
                attempt["channel"] == "institutional"
                and "experimental" in attempt["outcome"]
                for attempt in receipt["attempts"]
            )
        )

    def test_acquire_via_all_refused_yields_failed_receipt(self):
        receipt = acquire_via([InstitutionalAccessProvider()], new_request(), self.state)
        self.assertEqual(receipt["acquisition_status"], "failed")
        self.assertEqual(receipt["channel"], "none")
        self.assertEqual(len(receipt["attempts"]), 1)
        self.assertEqual(validate_receipt(receipt), [])

    def test_acquire_via_carries_attempts_across_channels(self):
        pdf = self.base / "paper.pdf"
        pdf.write_bytes(PDF_BYTES)
        (self.base / "paper.txt").write_bytes(TXT_BYTES)
        request = new_request(work_slug="w", ids={"doi": DOI}, local_path=pdf)
        oa_miss = OpenAccessProvider(fetch=None, cache=BibliographicCache(self.state))
        receipt = acquire_via([oa_miss, LocalFileProvider()], request, self.state)
        self.assertEqual(receipt["acquisition_status"], "acquired")
        self.assertEqual(receipt["channel"], "local")
        channels = [attempt["channel"] for attempt in receipt["attempts"]]
        self.assertIn("openaccess", channels)  # the miss is carried over
        self.assertIn("local", channels)


if __name__ == "__main__":
    unittest.main()
