"""Two-hop hierarchy projection remains separate from GraphQueryPort."""
import shutil
import tempfile
import unittest
from pathlib import Path

from knowledge_palace.graph.builder import write_index
from knowledge_palace.graph.neighborhood import BAND_ORDER, build_neighborhood

MINI = Path(__file__).resolve().parent / "fixtures" / "vault-mini"


class NeighborhoodCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        base = Path(cls._tmp.name)
        cls.vault = base / "vault"
        cls.state = base / "state"
        shutil.copytree(MINI, cls.vault)
        write_index(cls.vault, cls.state)

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def test_five_bands_and_parent_only_links(self):
        result = build_neighborhood(self.state, "concept:concept-gamma")
        self.assertEqual([band["id"] for band in result["bands"]], list(BAND_ORDER))
        self.assertEqual(result["hop_relation"], "parent")
        self.assertEqual(result["max_hops"], 2)
        self.assertEqual(result["bands"][2]["items"][0]["id"], "concept:concept-gamma")
        self.assertTrue(all(edge["kind"] == "parent" for edge in result["links"]))
        self.assertFalse(result["truncated"])

    def test_multi_parent_and_categories_are_preserved(self):
        result = build_neighborhood(self.state, "concept:concept-gamma")
        bands = {band["id"]: band for band in result["bands"]}
        self.assertEqual(
            [item["id"] for item in bands["parents"]["items"]],
            ["domain:alpha-domain", "domain:beta-domain"],
        )
        self.assertEqual(bands["parents"]["kind_counts"], {"domain": 2})
        parent_edges = {(edge["from"], edge["to"]) for edge in result["links"]}
        self.assertIn(("domain:alpha-domain", "concept:concept-gamma"), parent_edges)
        self.assertIn(("domain:beta-domain", "concept:concept-gamma"), parent_edges)

    def test_cap_reports_omissions_without_dropping_center(self):
        result = build_neighborhood(self.state, "concept:concept-gamma", max_nodes=2)
        bands = {band["id"]: band for band in result["bands"]}
        self.assertEqual(bands["center"]["returned"], 1)
        self.assertTrue(result["truncated"])
        self.assertGreater(sum(band["omitted"] for band in result["bands"]), 0)
        self.assertTrue(result["warnings"])

    def test_unknown_node_is_typed_error(self):
        result = build_neighborhood(self.state, "work:nope")
        self.assertEqual(result["error"]["code"], "unknown_node")
        self.assertIn("snapshot", result)


if __name__ == "__main__":
    unittest.main()
