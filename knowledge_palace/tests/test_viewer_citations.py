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
