"""Rich read-only network projection."""

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from knowledge_palace.graph.builder import write_index
from knowledge_palace.graph.network import build_network
from .test_viewer_citations import cache_entry
from .test_viewer_export import make_vault


class TestNetwork(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.vault = make_vault(self.root, works=3)
        self.state = self.root / "state"
        write_index(self.vault, self.state)

    def test_metadata_counts_and_determinism(self):
        first = build_network(self.state, self.vault)
        self.assertEqual(first, build_network(self.state, self.vault))
        works = [node for node in first["nodes"] if node["kind"] == "work"]
        self.assertEqual(len(works), 3)
        self.assertEqual(works[0]["year"], 2020)
        self.assertEqual(works[0]["citations"], 0)
        self.assertEqual(works[0]["read_depth"], "skim")
        self.assertEqual(first["completeness"]["works_with_citation_metrics"], 3)
        self.assertEqual(first["completeness"]["citation_metric_coverage"], 1.0)
        self.assertEqual(first["completeness"]["node_count"], len(first["nodes"]))
        self.assertEqual(first["completeness"]["link_count"], len(first["links"]))

    def test_citation_overlay_preserves_direction_and_neighbor_degree(self):
        cache_entry(self.state, "a", "10.9999/w0", "W100", ["W101"])
        cache_entry(self.state, "b", "10.9999/w1", "W101", ["W100"])
        result = build_network(self.state, self.vault)
        cites = [link for link in result["links"] if link["kind"] == "cites"]
        self.assertEqual(len(cites), 2)
        nodes = {node["id"]: node for node in result["nodes"]}
        self.assertEqual(nodes["work:work-0"]["citation_in"], 1)
        self.assertEqual(nodes["work:work-0"]["citation_out"], 1)
        # Reciprocal directed citations are one undirected neighbor for degree.
        self.assertEqual(nodes["work:work-0"]["degree"], 3)

    def test_similarity_requires_two_distinct_non_domain_concepts(self):
        # The fixture starts with one shared task concept and one domain tag: no similarity.
        first = build_network(self.state)
        self.assertFalse([link for link in first["links"] if link["kind"] == "similar"])
        concepts = (self.vault / "concepts.md").read_text(encoding="utf-8")
        concepts += "\n| u | d | canonical | - | U. | - |\n"
        (self.vault / "concepts.md").write_text(concepts, encoding="utf-8")
        for index in (0, 1):
            card = self.vault / "papers" / ("work-%d.md" % index)
            card.write_text(card.read_text(encoding="utf-8").replace("task: [t]", "task: [t, u]"), encoding="utf-8")
        write_index(self.vault, self.state)
        result = build_network(self.state)
        similar = [link for link in result["links"] if link["kind"] == "similar"]
        pair = next(link for link in similar if {link["from"], link["to"]} == {"work:work-0", "work:work-1"})
        self.assertEqual(pair["attrs"]["shared_concepts"], 2)
        nodes = {node["id"]: node for node in result["nodes"]}
        # Similarity is derived and excluded from structural degree.
        self.assertEqual(nodes["work:work-0"]["degree"], 3)

    def test_bounded_overview_is_deterministic_and_reports_totals(self):
        full = build_network(self.state, self.vault)
        first = build_network(self.state, self.vault, max_nodes=3, max_links=2)
        self.assertEqual(first, build_network(self.state, self.vault, max_nodes=3, max_links=2))
        self.assertEqual(len(first["nodes"]), 3)
        self.assertLessEqual(len(first["links"]), 2)
        self.assertTrue(first["completeness"]["truncated"])
        self.assertEqual(first["completeness"]["total_node_count"], len(full["nodes"]))
        self.assertGreaterEqual(first["completeness"]["total_link_count"], len(first["links"]))
        self.assertIn("canonical base graph", first["completeness"]["total_link_count_scope"])
        selected = {node["id"] for node in first["nodes"]}
        self.assertTrue(all(link["from"] in selected and link["to"] in selected for link in first["links"]))

    def test_bounded_browser_path_does_not_walk_full_viewer_bundle(self):
        with mock.patch("knowledge_palace.viewer.export.build_bundle", side_effect=AssertionError("full walk")):
            result = build_network(self.state, self.vault, max_nodes=500, max_links=3000)
        self.assertEqual(len([node for node in result["nodes"] if node["kind"] == "work"]), 3)
        self.assertEqual(result["completeness"]["citation_overlay"], "bibliographic-cache-selected-works")

    def test_bounded_citation_overlay_preserves_direction(self):
        cache_entry(self.state, "a", "10.9999/w0", "W100", ["W101"])
        cache_entry(self.state, "b", "10.9999/w1", "W101", ["W100"])
        result = build_network(self.state, self.vault, max_nodes=500, max_links=3000)
        self.assertEqual({(link["from"], link["to"]) for link in result["links"] if link["kind"] == "cites"}, {
            ("work:work-0", "work:work-1"), ("work:work-1", "work:work-0")
        })

    def test_without_vault_labels_overlay_not_requested(self):
        result = build_network(self.state)
        self.assertEqual(result["completeness"]["citation_overlay"], "not_requested")
        self.assertTrue(all(node["citations"] is None for node in result["nodes"] if node["kind"] == "work"))


if __name__ == "__main__":
    unittest.main()
