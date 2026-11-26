"""Citation overlay: DOI join against the Bibliographic Cache, offline."""

import json
import tempfile
import unittest
from pathlib import Path

from knowledge_palace.graph.builder import write_index
from knowledge_palace.viewer.export import build_bundle, citation_overlay

from .test_viewer_export import make_vault


def cache_entry(state, name, doi, oa_id, referenced=None):
    cache = Path(state) / "bibliographic-cache" / "openalex"
    cache.mkdir(parents=True, exist_ok=True)
    payload = {"doi": "https://doi.org/" + doi, "id": "https://openalex.org/" + oa_id}
    if referenced is not None:
        payload["referenced_works"] = ["https://openalex.org/" + r for r in referenced]
    (cache / (name + ".json")).write_text(
        json.dumps({"fetched_at": "2026-07-21", "payload": payload}), encoding="utf-8"
    )


class TestCitationOverlay(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        self.vault = make_vault(self.root, works=3)
        self.state = self.root / "state"
        write_index(self.vault, self.state)
        self.payload = build_bundle(self.vault, self.state)

    def test_missing_cache_is_empty_overlay(self):
        self.assertEqual(citation_overlay(self.payload, self.state), {"edges": []})

    def test_doi_join_produces_work_edges(self):
        # work-0 cites work-1 and an off-vault work; work-1 cites itself (dropped)
        cache_entry(self.state, "a", "10.9999/w0", "W100", ["W101", "W999"])
        cache_entry(self.state, "b", "10.9999/w1", "W101", ["W101"])
        cache_entry(self.state, "c", "10.9999/w2", "W102")  # ids only, no refs
        overlay = citation_overlay(self.payload, self.state)
        self.assertEqual(overlay, {"edges": [["work:work-0", "work:work-1"]]})

    def test_arxiv_url_source_joins(self):
        card = self.vault / "papers" / "work-2.md"
        card.write_text(
            card.read_text(encoding="utf-8").replace(
                'source: "10.9999/w2"', 'source: "https://arxiv.org/abs/2101.12345"'
            ),
            encoding="utf-8",
        )
        write_index(self.vault, self.state)
        payload = build_bundle(self.vault, self.state)
        cache_entry(self.state, "a", "10.48550/arxiv.2101.12345", "W200")
        cache_entry(self.state, "b", "10.9999/w0", "W100", ["W200"])
        overlay = citation_overlay(payload, self.state)
        self.assertEqual(overlay, {"edges": [["work:work-0", "work:work-2"]]})

    def _arxiv_card(self, name, arxiv_id):
        card = self.vault / "papers" / (name + ".md")
        old = 'source: "10.9999/%s"' % name.replace("work-", "w")
        card.write_text(card.read_text(encoding="utf-8").replace(old, 'source: "https://arxiv.org/abs/%s"' % arxiv_id), encoding="utf-8")
        write_index(self.vault, self.state)
        return build_bundle(self.vault, self.state)

    def test_merged_published_doi_still_matches_through_request_url(self):
        payload = self._arxiv_card("work-2", "2202.04200")
        cache = Path(self.state) / "bibliographic-cache" / "openalex"
        cache.mkdir(parents=True, exist_ok=True)
        record = {"doi": "https://doi.org/10.1109/cvpr.2022.01103", "id": "https://openalex.org/W300",
                  "ids": {"arxiv": "https://arxiv.org/abs/2202.04200"}, "referenced_works": ["https://openalex.org/W100"]}
        (cache / "m.json").write_text(json.dumps({"url": "https://api.openalex.org/works/doi:10.48550/arxiv.2202.04200", "payload": record}), encoding="utf-8")
        cache_entry(self.state, "a", "10.9999/w0", "W100", ["W300"])
        overlay = citation_overlay(payload, self.state)
        self.assertEqual(overlay, {"edges": [["work:work-0", "work:work-2"], ["work:work-2", "work:work-0"]]})

    def test_semantic_scholar_and_crossref_reference_lists_add_edges(self):
        payload = self._arxiv_card("work-2", "2306.06079")
        root = Path(self.state) / "bibliographic-cache"
        (root / "semanticscholar").mkdir(parents=True)
        (root / "semanticscholar" / "s.json").write_text(json.dumps({
            "url": "https://api.semanticscholar.org/graph/v1/paper/ARXIV:2306.06079/references?fields=title,externalIds&limit=100",
            "payload": {"data": [{"citedPaper": {"externalIds": {"DOI": "10.9999/W0"}}}, {"citedPaper": {"externalIds": {"ArXiv": "9999.00001"}}}]}}), encoding="utf-8")
        (root / "crossref").mkdir(parents=True)
        (root / "crossref" / "c.json").write_text(json.dumps({
            "url": "https://api.crossref.org/works/10.9999/w1",
            "payload": {"message": {"DOI": "10.9999/w1", "reference": [{"DOI": "10.9999/w0"}, {"unstructured": "no doi"}]}}}), encoding="utf-8")
        overlay = citation_overlay(payload, self.state)
        self.assertEqual(overlay, {"edges": [["work:work-1", "work:work-0"], ["work:work-2", "work:work-0"]]})

    def test_duplicate_doi_gets_no_edges(self):
        card = self.vault / "papers" / "work-1.md"
        card.write_text(
            card.read_text(encoding="utf-8").replace(
                'source: "10.9999/w1"', 'source: "10.9999/w0"'
            ),
            encoding="utf-8",
        )
        write_index(self.vault, self.state)
        payload = build_bundle(self.vault, self.state)
        cache_entry(self.state, "a", "10.9999/w0", "W100", ["W102"])
        cache_entry(self.state, "c", "10.9999/w2", "W102", ["W100"])
        overlay = citation_overlay(payload, self.state)
        self.assertEqual(overlay, {"edges": []})  # ambiguous DOI: neither card gets edges

    def test_corrupt_cache_entry_names_the_file(self):
        cache = self.state / "bibliographic-cache" / "openalex"
        cache.mkdir(parents=True)
        (cache / "bad.json").write_text("{not json", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "corrupt bibliographic cache entry"):
            citation_overlay(self.payload, self.state)

    def test_deterministic(self):
        cache_entry(self.state, "a", "10.9999/w0", "W100", ["W101"])
        cache_entry(self.state, "b", "10.9999/w1", "W101", ["W100"])
        first = citation_overlay(self.payload, self.state)
        self.assertEqual(first, citation_overlay(self.payload, self.state))
        # both directions present as distinct ordered pairs, sorted
        self.assertEqual(
            first["edges"],
            [["work:work-0", "work:work-1"], ["work:work-1", "work:work-0"]],
        )


if __name__ == "__main__":
    unittest.main()
