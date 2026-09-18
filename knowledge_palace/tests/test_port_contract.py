"""The production GraphQueryPort: five operations, honest pagination,
multi-parent context, brief-as-view, typed errors, absent-index refusal."""

import shutil
import tempfile
import unittest
from pathlib import Path

from knowledge_palace.graph.builder import write_index
from knowledge_palace.graph.port import GraphQueryPort

MINI = Path(__file__).resolve().parent / "fixtures" / "vault-mini"



class PortCase(unittest.TestCase):
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

    def port(self, page_limit=50):
        return GraphQueryPort(self.vault, self.state, page_limit=page_limit)


class TestContractConformance(PortCase):
    def test_every_response_carries_version_and_snapshot(self):
        port = self.port()
        for message in (
            port.list_hierarchies(),
            port.list_levels("domain-concept-work"),
            port.query_level("domain-concept-work", 2),
            port.query_context("concept:concept-gamma"),
            port.get_content("work:alpha-2020-echo"),
        ):
            self.assertEqual(message["schema_version"], "1.1")
            self.assertIn("vault_fingerprint", message["snapshot"])

    def test_cursor_walk_is_complete(self):
        port = self.port(page_limit=2)
        seen, cursor = [], None
        while True:
            page = port.query_level("domain-concept-work", 2, cursor=cursor)["page"]
            self.assertEqual(page["returned"], len(page["items"]))
            self.assertEqual(page["truncated"], page["next_cursor"] is not None)
            seen.extend(item["id"] for item in page["items"])
            if not page["truncated"]:
                break
            cursor = page["next_cursor"]
        self.assertEqual(len(seen), page["total"])
        self.assertEqual(len(seen), len(set(seen)))
        self.assertEqual(
            sorted(seen),
            sorted(
                nid
                for nid, view in port._payload["nodes"].items()
                if view["kind"] in ("work", "gap")
            ),
        )

    def test_multi_parent_entry_parent_semantics(self):
        port = self.port()
        grouped = port.query_context("concept:concept-gamma")
        self.assertIsNone(grouped["entry_parent"])
        self.assertIsNone(grouped["siblings"])
        self.assertEqual(
            [group["parent_id"] for group in grouped["sibling_groups"]],
            ["domain:alpha-domain", "domain:beta-domain"],
        )
        entered = port.query_context(
            "concept:concept-gamma", entry_parent="domain:alpha-domain"
        )
        self.assertEqual(entered["entry_parent"], "domain:alpha-domain")
        self.assertIsNone(entered["sibling_groups"])
        sibling_ids = [item["id"] for item in entered["siblings"]["items"]]
        self.assertIn("concept:concept-echo", sibling_ids)
        self.assertNotIn("concept:concept-gamma", sibling_ids)
        bad = port.query_context("concept:concept-gamma", entry_parent="domain:nope")
        self.assertEqual(bad["error"]["code"], "invalid_request")

    def test_brief_stays_a_view(self):
        port = self.port()
        response = port.query_context("brief:2026-07-13-gaps")
        attrs = response["node"]["attrs"]
        self.assertEqual(attrs["role"], "view")
        self.assertIs(attrs["evidence_capable"], False)
        self.assertEqual(response["edges"]["total"], 0)

    def test_get_content_work_and_claim(self):
        port = self.port()
        work = port.get_content("work:alpha-2020-echo")
        self.assertIn("Echo Cancellation in Alpha Systems", work["content"])
        self.assertEqual(work["canonical_ref"]["path"], "papers/alpha-2020-echo.md")
        claim = port.get_content("claim:alpha-2020-echo#C1")
        self.assertIn("improves by delta", claim["content"])
        self.assertIn("§2 [¶1] / p.2", claim["content"])
        self.assertEqual(claim["canonical_ref"]["anchor"], "C1")

    def test_typed_errors(self):
        port = self.port()
        self.assertEqual(
            port.list_levels("nope")["error"]["code"], "unknown_hierarchy"
        )
        self.assertEqual(
            port.query_level("domain-concept-work", 9)["error"]["code"], "invalid_request"
        )
        self.assertEqual(port.query_context("work:nope")["error"]["code"], "unknown_node")
        self.assertEqual(
            port.query_level("domain-concept-work", 2, cursor="nope")["error"]["code"],
            "bad_cursor",
        )


class TestAbsent(unittest.TestCase):
    def test_absent_index_raises_with_rebuild_hint(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(FileNotFoundError) as ctx:
                GraphQueryPort(MINI, Path(td) / "state")
            self.assertIn("--rebuild", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
