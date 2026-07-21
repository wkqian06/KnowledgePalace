"""The production GraphQueryPort passes the frozen
validator/contract semantics unchanged, and a stale index refuses every
operation."""

import shutil
import tempfile
import unittest
from pathlib import Path

from knowledge_palace.graph.builder import vault_fingerprint, write_index
from knowledge_palace.graph.port import GraphQueryPort
from knowledge_palace.tools.gqp_validator import load_schema, validate_response

MINI = Path(__file__).resolve().parent / "fixtures" / "vault-mini"

OPERATIONS = ("list_hierarchies", "list_levels", "query_level", "query_context", "get_content")


def canonical_calls(port):
    return {
        "list_hierarchies": port.list_hierarchies(),
        "list_levels": port.list_levels("domain-concept-work"),
        "query_level": port.query_level("domain-concept-work", 2),
        "query_context": port.query_context("concept:concept-gamma"),
        "get_content": port.get_content("work:alpha-2020-echo"),
    }


class PortCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schema = load_schema()
        cls._tmp = tempfile.TemporaryDirectory()
        base = Path(cls._tmp.name)
        cls.vault = base / "vault"
        cls.state = base / "state"
        shutil.copytree(MINI, cls.vault)
        write_index(cls.vault, cls.state)
        cls.fingerprint = vault_fingerprint(cls.vault)

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def port(self, page_limit=50):
        return GraphQueryPort(self.vault, self.state, page_limit=page_limit)


class TestContractConformance(PortCase):
    def test_every_operation_validates_cleanly(self):
        port = self.port()
        for op, message in canonical_calls(port).items():
            errors = validate_response(
                op, message, self.schema, current_vault_fingerprint=self.fingerprint
            )
            self.assertEqual(errors, [], "%s: %s" % (op, errors))

    def test_surface_is_exactly_the_five_operations(self):
        port = self.port()
        public = sorted(
            name
            for name in dir(port)
            if not name.startswith("_") and callable(getattr(port, name))
        )
        self.assertEqual(public, sorted(OPERATIONS))

    def test_cursor_walk_is_complete(self):
        port = self.port(page_limit=2)
        seen, cursor = [], None
        while True:
            response = port.query_level("domain-concept-work", 2, cursor=cursor)
            self.assertEqual(
                validate_response(
                    "query_level", response, self.schema,
                    current_vault_fingerprint=self.fingerprint,
                ),
                [],
            )
            page = response["page"]
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
        for message, op in ((grouped, "query_context"), (entered, "query_context")):
            self.assertEqual(
                validate_response(
                    op, message, self.schema, current_vault_fingerprint=self.fingerprint
                ),
                [],
            )
        bad = port.query_context("concept:concept-gamma", entry_parent="domain:nope")
        self.assertEqual(bad["error"]["code"], "invalid_request")

    def test_brief_stays_a_view(self):
        port = self.port()
        response = port.query_context("brief:2026-07-13-gaps")
        self.assertEqual(
            validate_response(
                "query_context", response, self.schema,
                current_vault_fingerprint=self.fingerprint,
            ),
            [],
        )
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
        for op_message in (work, claim):
            self.assertEqual(
                validate_response(
                    "get_content", op_message, self.schema,
                    current_vault_fingerprint=self.fingerprint,
                ),
                [],
            )

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
        for message in (
            port.list_levels("nope"),
            port.query_context("work:nope"),
        ):
            self.assertEqual(
                validate_response("query_context", message, self.schema), []
            )


class TestStaleAndAbsent(unittest.TestCase):
    def test_stale_index_refuses_every_operation(self):
        with tempfile.TemporaryDirectory() as td:
            vault = Path(td) / "vault"
            state = Path(td) / "state"
            shutil.copytree(MINI, vault)
            write_index(vault, state)
            port = GraphQueryPort(vault, state)
            with (vault / "papers" / "alpha-2020-echo.md").open("a", encoding="utf-8") as fh:
                fh.write("\n")
            schema = load_schema()
            for op, message in canonical_calls(port).items():
                self.assertEqual(message["error"]["code"], "stale_index", op)
                self.assertIn("rebuild", message["error"]["message"])
                self.assertEqual(validate_response(op, message, schema), [], op)

    def test_absent_index_raises_with_rebuild_hint(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(FileNotFoundError) as ctx:
                GraphQueryPort(MINI, Path(td) / "state")
            self.assertIn("--rebuild", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
