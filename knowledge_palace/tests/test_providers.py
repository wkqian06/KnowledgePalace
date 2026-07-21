"""Normalized provider records over injected transports,
cache-first behavior, rate limiting, typed failures with zero partial writes."""

import json
import tempfile
import unittest
from pathlib import Path

from knowledge_palace.metadata.cache import BibliographicCache, RateLimiter
from knowledge_palace.metadata.providers import (
    ADAPTERS,
    ArxivProvider,
    CrossrefProvider,
    OpenAlexProvider,
    ProviderError,
    SemanticScholarProvider,
)

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "providers"


def fixture_bytes(name):
    return (FIXTURES / name).read_bytes()


class CountingStub:
    """fetch(url, headers) stub dispatching on URL substring."""

    def __init__(self, routes):
        self.routes = routes
        self.calls = []

    def __call__(self, url, headers=None):
        self.calls.append(url)
        for needle, payload in self.routes.items():
            if needle in url:
                return payload
        raise AssertionError("unrouted url: %s" % url)


class TestOpenAlex(unittest.TestCase):
    def setUp(self):
        self.stub = CountingStub(
            {
                "filter=cites:": fixture_bytes("openalex-citing.json"),
                "/works/doi:": fixture_bytes("openalex-work.json"),
            }
        )
        self.provider = OpenAlexProvider(fetch=self.stub)

    def test_resolve_normalizes(self):
        record = self.provider.resolve({"doi": "https://doi.org/10.99999/Fixture.Alpha2020"})
        self.assertEqual(record["provider"], "openalex")
        self.assertEqual(record["ids"]["doi"], "10.99999/fixture.alpha2020")
        self.assertEqual(record["ids"]["openalex"], "W1234567")
        self.assertEqual(record["year"], 2020)
        self.assertEqual(record["citations"], 42)
        self.assertAlmostEqual(record["citation_percentile"], 93.0)
        self.assertEqual(record["categories"], ["Echo Processing", "Signal Systems"])
        self.assertEqual(record["venue"], "Fixture Letters")

    def test_references_and_cited_by(self):
        refs = self.provider.references({"doi": "10.99999/fixture.alpha2020"})
        self.assertEqual(refs["count"], 2)
        self.assertEqual(refs["items"][0]["ids"], {"openalex": "W1"})
        citing = self.provider.cited_by({"doi": "10.99999/fixture.alpha2020"}, limit=5)
        self.assertEqual(citing["count"], 42)
        self.assertEqual(citing["items"][0]["ids"]["openalex"], "W9")

    def test_arxiv_ref_routes_via_datacite_doi(self):
        self.provider.resolve({"arxiv": "2101.00001"})
        self.assertIn("doi:10.48550/arxiv.2101.00001", self.stub.calls[0])


class TestCrossref(unittest.TestCase):
    def test_resolve_and_references(self):
        stub = CountingStub({"/works/": fixture_bytes("crossref-work.json")})
        provider = CrossrefProvider(fetch=stub)
        record = provider.resolve({"doi": "10.99999/fixture.alpha2020"})
        self.assertEqual(record["year"], 2020)
        self.assertEqual(record["citations"], 40)
        self.assertIs(record["peer_reviewed"], True)
        refs = provider.references({"doi": "10.99999/fixture.alpha2020"})
        self.assertEqual(refs["count"], 2)
        self.assertEqual(refs["items"][0]["ids"], {"doi": "10.1000/ref.one"})

    def test_empty_date_parts_yield_none_year(self):
        message = {
            "message": {
                "DOI": "10.5/undated",
                "title": ["Undated work"],
                "issued": {"date-parts": [[]]},
                "type": "journal-article",
            }
        }
        stub = CountingStub({"/works/": json.dumps(message).encode("utf-8")})
        record = CrossrefProvider(fetch=stub).resolve({"doi": "10.5/undated"})
        self.assertIsNone(record["year"])

    def test_preprint_type_flag(self):
        message = {
            "message": {
                "DOI": "10.5/pre",
                "title": ["A preprint"],
                "issued": {"date-parts": [[2024]]},
                "type": "posted-content",
            }
        }
        stub = CountingStub({"/works/": json.dumps(message).encode("utf-8")})
        record = CrossrefProvider(fetch=stub).resolve({"doi": "10.5/pre"})
        self.assertIs(record["is_preprint"], True)


class TestSemanticScholarAndArxiv(unittest.TestCase):
    def test_s2_resolve(self):
        stub = CountingStub({"/paper/DOI:": fixture_bytes("s2-work.json")})
        record = SemanticScholarProvider(fetch=stub).resolve(
            {"doi": "10.99999/fixture.alpha2020"}
        )
        self.assertEqual(record["ids"]["s2"], "s2abc123")
        self.assertEqual(record["citations"], 41)

    def test_arxiv_resolve_and_typed_refusals(self):
        stub = CountingStub({"id_list=": fixture_bytes("arxiv-entry.xml")})
        provider = ArxivProvider(fetch=stub)
        record = provider.resolve({"arxiv": "2101.00001"})
        self.assertEqual(record["ids"]["arxiv"], "2101.00001")  # version stripped
        self.assertEqual(record["year"], 2021)
        self.assertIs(record["is_preprint"], True)
        self.assertEqual(record["title"], "Foxtrot Thresholds in Beta Regimes")
        with self.assertRaises(ProviderError):
            provider.references({"arxiv": "2101.00001"})
        with self.assertRaises(ProviderError):
            provider.cited_by({"arxiv": "2101.00001"})


class TestCacheAndFailures(unittest.TestCase):
    def test_cache_first_second_call_hits_disk(self):
        with tempfile.TemporaryDirectory() as td:
            cache = BibliographicCache(td, now=lambda: "2026-07-13T00:00:00+00:00")
            stub = CountingStub({"/works/doi:": fixture_bytes("openalex-work.json")})
            first = OpenAlexProvider(fetch=stub, cache=cache).resolve(
                {"doi": "10.99999/fixture.alpha2020"}
            )
            self.assertEqual(len(stub.calls), 1)
            self.assertEqual(first["fetched_at"], "2026-07-13T00:00:00+00:00")
            offline = OpenAlexProvider(fetch=None, cache=cache)
            second = offline.resolve({"doi": "10.99999/fixture.alpha2020"})
            self.assertEqual(len(stub.calls), 1)  # untouched
            self.assertEqual(second, first)

    def test_cache_only_miss_is_typed(self):
        with tempfile.TemporaryDirectory() as td:
            provider = OpenAlexProvider(fetch=None, cache=BibliographicCache(td))
            with self.assertRaises(ProviderError) as ctx:
                provider.resolve({"doi": "10.9/none"})
            self.assertIn("cache-only", str(ctx.exception))

    def test_transport_failure_leaves_no_partial_cache(self):
        with tempfile.TemporaryDirectory() as td:
            cache = BibliographicCache(td)

            def broken(url, headers=None):
                raise IOError("connection refused")

            provider = OpenAlexProvider(fetch=broken, cache=cache)
            with self.assertRaises(ProviderError) as ctx:
                provider.resolve({"doi": "10.9/x"})
            self.assertIn("transport failure", str(ctx.exception))
            self.assertEqual(list(Path(td).rglob("*.json")), [])

    def test_unparseable_payload_is_typed_and_uncached(self):
        with tempfile.TemporaryDirectory() as td:
            cache = BibliographicCache(td)
            stub = CountingStub({"/works/doi:": b"<html>rate limited</html>"})
            with self.assertRaises(ProviderError) as ctx:
                OpenAlexProvider(fetch=stub, cache=cache).resolve({"doi": "10.9/x"})
            self.assertIn("unparseable", str(ctx.exception))
            self.assertEqual(list(Path(td).rglob("*.json")), [])

    def test_rate_limiter_spaces_calls_with_fake_clock(self):
        ticks = iter([0.0, 0.2, 1.2, 1.4, 2.4])
        sleeps = []
        limiter = RateLimiter(min_interval=1.0, clock=lambda: next(ticks), sleep=sleeps.append)
        limiter.wait("openalex")  # t=0.0, no sleep
        limiter.wait("openalex")  # t=0.2 → sleep 0.8, re-clock 1.2
        limiter.wait("openalex")  # t=1.4 → sleep 0.8, re-clock 2.4
        self.assertEqual([round(s, 3) for s in sleeps], [0.8, 0.8])

    def test_adapter_registry_is_complete(self):
        self.assertEqual(
            sorted(ADAPTERS), ["arxiv", "crossref", "openalex", "semanticscholar"]
        )


if __name__ == "__main__":
    unittest.main()
