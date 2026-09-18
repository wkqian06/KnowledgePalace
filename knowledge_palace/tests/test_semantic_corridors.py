"""Bounded, deterministic, index-only typed corridors;
the frozen GraphQueryPort contract stays intact underneath."""

import shutil
import tempfile
import unittest
from pathlib import Path

from knowledge_palace.graph.builder import build_payload, write_index
from knowledge_palace.graph.port import GraphQueryPort
from knowledge_palace.semantic.corridors import CORRIDOR_CAP, find_corridors

MINI = Path(__file__).resolve().parent / "fixtures" / "vault-mini"


def synthetic_dense_payload(concepts=30):
    """Two domains, N shared-pattern concepts each attached from both sides."""
    nodes = {
        "domain:d-a": {"id": "domain:d-a", "kind": "domain", "label": "A"},
        "domain:d-b": {"id": "domain:d-b", "kind": "domain", "label": "B"},
        "concept:root-a": {"id": "concept:root-a", "kind": "concept", "label": "root-a",
                           "attrs": {"axis": "task"}},
        "concept:root-b": {"id": "concept:root-b", "kind": "concept", "label": "root-b",
                           "attrs": {"axis": "task"}},
    }
    parents = {"concept:root-a": ["domain:d-a"], "concept:root-b": ["domain:d-b"]}
    edges = []
    for index in range(concepts):
        cid = "concept:shared-%02d" % index
        nodes[cid] = {"id": cid, "kind": "concept", "label": cid,
                      "attrs": {"axis": "pattern"}}
        parents[cid] = []
        for side, root in (("a", "concept:root-a"), ("b", "concept:root-b")):
            wid = "work:w-%s-%02d" % (side, index)
            nodes[wid] = {"id": wid, "kind": "work", "label": wid}
            parents[wid] = [root]
            edges.append({"id": "%s|tag:pattern|%s" % (wid, cid),
                          "kind": "tag:pattern", "from": wid, "to": cid})
    return {"nodes": nodes, "parents": parents, "edges": edges,
            "hierarchies": [{"id": "h", "label": "h", "levels": []}]}


class TestVaultMiniCorridors(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.payload = build_payload(MINI)
        cls.result = find_corridors(cls.payload, "alpha-domain", "beta-domain")

    def test_transfer_corridor_found(self):
        transfers = [c for c in self.result["corridors"] if c["kind"] == "transfer"]
        self.assertEqual(len(transfers), 1)
        self.assertEqual(transfers[0]["via"], "transfer:transfer-echo-to-gamma")

    def test_shared_axis_corridor_found_with_both_sides(self):
        shared = [c for c in self.result["corridors"] if c["kind"] == "shared-axis"]
        self.assertEqual(len(shared), 1)
        corridor = shared[0]
        self.assertEqual(corridor["via"], "concept:concept-shared-pattern")
        self.assertEqual(corridor["axis"], "pattern")
        self.assertIn("work:alpha-2020-echo", corridor["side_a"])
        self.assertIn("work:beta-2021-foxtrot", corridor["side_b"])

    def test_transfers_rank_before_shared_axis_and_results_are_honest(self):
        kinds = [c["kind"] for c in self.result["corridors"]]
        self.assertEqual(kinds, sorted(kinds, key=("transfer", "shared-axis").index))
        self.assertEqual(self.result["total"], self.result["returned"])
        self.assertFalse(self.result["truncated"])

    def test_descriptors_carry_ids_only(self):
        for corridor in self.result["corridors"]:
            for value in corridor.values():
                text = str(value)
                self.assertNotIn("Synthetic card body", text)
                self.assertNotIn("Fixture paper", text)


class TestCapAndDeterminism(unittest.TestCase):
    def test_cap_enforced_on_dense_payload(self):
        payload = synthetic_dense_payload(concepts=30)
        result = find_corridors(payload, "d-a", "d-b")
        self.assertEqual(result["total"], 30)
        self.assertEqual(result["returned"], CORRIDOR_CAP)
        self.assertTrue(result["truncated"])
        again = find_corridors(payload, "d-a", "d-b")
        self.assertEqual(result, again)  # deterministic
        vias = [c["via"] for c in result["corridors"]]
        self.assertEqual(vias, sorted(vias))  # lexicographic within one axis

    def test_cap_parameter_is_bounded(self):
        payload = synthetic_dense_payload(concepts=5)
        result = find_corridors(payload, "d-a", "d-b", cap=99)
        self.assertEqual(result["returned"], 5)  # cap clamps to CORRIDOR_CAP max


class TestSemanticEdgesFlowThroughPort(unittest.TestCase):
    def test_binding_and_role_edges_reach_query_context(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            vault = base / "vault"
            shutil.copytree(MINI, vault)
            write_index(vault, base / "state")
            port = GraphQueryPort(vault, base / "state")
            context = port.query_context("claim:alpha-2020-echo#C1")
            edge_kinds = {e["kind"] for e in context["edges"]["items"]}
            self.assertIn("binds", edge_kinds)  # new edge kind flows through
            self.assertIn("role:method", edge_kinds)


if __name__ == "__main__":
    unittest.main()
