"""Two-hop citation neighborhood, in knowledge-flow order, from the cache overlay."""

import tempfile
import unittest
from pathlib import Path

from knowledge_palace.graph.builder import write_index
from knowledge_palace.graph.neighborhood import build_citation_neighborhood

from .test_viewer_citations import cache_entry
from .test_viewer_export import make_vault


class TestCitationNeighborhood(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        root = Path(self._tmp.name)
        self.vault = make_vault(root, works=3)
        self.state = root / "state"
        write_index(self.vault, self.state)
        # work-0 cites work-1; work-1 cites work-2
        cache_entry(self.state, "a", "10.9999/w0", "W100", ["W101"])
        cache_entry(self.state, "b", "10.9999/w1", "W101", ["W102"])
        cache_entry(self.state, "c", "10.9999/w2", "W102")

    def bands(self, node_id):
        result = build_citation_neighborhood(self.state, self.vault, node_id)
        return {band["id"]: [item["id"] for item in band["items"]] for band in result["bands"]}, result

    def test_one_hop_both_directions(self):
        bands, result = self.bands("work:work-1")
        self.assertEqual(bands["sources"], ["work:work-2"])
        self.assertEqual(bands["citing"], ["work:work-0"])
        flows = {(link["from"], link["to"]) for link in result["links"]}
        self.assertIn(("work:work-2", "work:work-1"), flows)  # cited work feeds the citing one
        self.assertIn(("work:work-1", "work:work-0"), flows)

    def test_second_hop(self):
        bands, _ = self.bands("work:work-0")
        self.assertEqual(bands["sources"], ["work:work-1"])
        self.assertEqual(bands["sources2"], ["work:work-2"])
        bands, _ = self.bands("work:work-2")
        self.assertEqual(bands["citing"], ["work:work-1"])
        self.assertEqual(bands["citing2"], ["work:work-0"])

    def test_non_work_returns_none(self):
        self.assertIsNone(build_citation_neighborhood(self.state, self.vault, "domain:none"))


if __name__ == "__main__":
    unittest.main()
