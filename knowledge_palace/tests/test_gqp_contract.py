"""Acceptance 6: GraphQueryPort contract tests — serialization, logical
references, bounded pagination, unknown node kinds, multi-parent entry parent,
Brief non-evidence role, zero authoritative writes, stale-index rejection."""

import json
import unittest
from pathlib import Path

from knowledge_palace.tests.fixtures.gqp.reference_stub import (
    INDEX_FINGERPRINT,
    OPERATIONS,
    ReferenceGraphQueryPort,
)
from knowledge_palace.tools.gqp_validator import load_schema, validate_response

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "gqp"

CANONICAL_CALLS = {
    "list_hierarchies": lambda port: port.list_hierarchies(),
    "list_levels": lambda port: port.list_levels("domain-concept-work"),
    "query_level": lambda port: port.query_level("domain-concept-work", 2),
    "query_context": lambda port: port.query_context("concept-gamma"),
    "get_content": lambda port: port.get_content("work-alpha-2020-echo"),
}

INVALID_EXPECTATIONS = {
    "abs-path.json": ("get_content", "drive-lettered"),
    "missing-snapshot.json": ("list_hierarchies", "required key missing"),
    "silent-omission.json": ("query_level", "silent omission"),
    "truncated-no-cursor.json": ("query_level", "iff truncated"),
    "stale-success.json": ("query_level", "stale index served"),
    "brief-evidence-edge.json": ("query_context", "brief node"),
    "bad-entry-parent.json": ("query_context", "siblings page is null"),
}


class TestReferencePortConforms(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schema = load_schema()
        cls.port = ReferenceGraphQueryPort()

    def test_every_operation_validates_cleanly(self):
        for op, call in CANONICAL_CALLS.items():
            errors = validate_response(
                op, call(self.port), self.schema, current_vault_fingerprint=INDEX_FINGERPRINT
            )
            self.assertEqual(errors, [], "%s: %s" % (op, errors))

    def test_serialization_round_trips(self):
        for op, call in CANONICAL_CALLS.items():
            message = call(self.port)
            self.assertEqual(json.loads(json.dumps(message)), message, op)

    def test_valid_fixture_files_are_frozen_stub_output(self):
        for op, call in CANONICAL_CALLS.items():
            frozen = json.loads((FIXTURES / "valid" / (op + ".json")).read_text(encoding="utf-8"))
            self.assertEqual(frozen, call(self.port), op)
            errors = validate_response(
                op, frozen, self.schema, current_vault_fingerprint=INDEX_FINGERPRINT
            )
            self.assertEqual(errors, [], op)

    def test_zero_write_surface(self):
        public = sorted(
            name
            for name in dir(self.port)
            if not name.startswith("_") and callable(getattr(self.port, name))
        )
        self.assertEqual(public, sorted(OPERATIONS))
        self.assertEqual(sorted(self.schema["operations"]), sorted(OPERATIONS))

    def test_error_code_set_is_closed(self):
        self.assertEqual(
            self.schema["error_codes"],
            ["stale_index", "unknown_hierarchy", "unknown_node", "unknown_operation", "bad_cursor", "invalid_request"],
        )
        self.assertEqual(
            self.schema["error_codes"],
            self.schema["$defs"]["Error"]["properties"]["code"]["enum"],
        )


class TestPagination(unittest.TestCase):
    def setUp(self):
        self.schema = load_schema()
        self.port = ReferenceGraphQueryPort(page_limit=1)

    def test_cursor_walk_is_complete_and_bounded(self):
        seen = []
        cursor = None
        pages = 0
        while True:
            response = self.port.query_level("domain-concept-work", 2, cursor=cursor)
            errors = validate_response(
                "query_level", response, self.schema, current_vault_fingerprint=INDEX_FINGERPRINT
            )
            self.assertEqual(errors, [], errors)
            page = response["page"]
            seen.extend(item["id"] for item in page["items"])
            pages += 1
            self.assertLessEqual(pages, page["total"] + 1)
            if not page["truncated"]:
                self.assertIsNone(page["next_cursor"])
                break
            cursor = page["next_cursor"]
        self.assertEqual(len(seen), len(set(seen)))
        self.assertEqual(len(seen), page["total"])
        final = self.port.query_level("domain-concept-work", 2, limit=500)
        self.assertEqual(sorted(seen), [item["id"] for item in final["page"]["items"]])

    def test_bad_cursor_is_typed(self):
        response = self.port.query_level("domain-concept-work", 2, cursor="nope")
        self.assertEqual(response["error"]["code"], "bad_cursor")
        self.assertEqual(
            validate_response("query_level", response, self.schema), []
        )


class TestContextAndBrief(unittest.TestCase):
    def setUp(self):
        self.schema = load_schema()
        self.port = ReferenceGraphQueryPort(page_limit=5)

    def test_multi_parent_without_entry_groups_by_parent(self):
        response = self.port.query_context("concept-gamma")
        self.assertEqual(validate_response("query_context", response, self.schema), [])
        self.assertIsNone(response["entry_parent"])
        self.assertIsNone(response["siblings"])
        parents = [group["parent_id"] for group in response["sibling_groups"]]
        self.assertEqual(parents, ["domain-alpha", "domain-beta"])

    def test_entry_parent_is_kept(self):
        response = self.port.query_context("concept-gamma", entry_parent="domain-alpha")
        self.assertEqual(validate_response("query_context", response, self.schema), [])
        self.assertEqual(response["entry_parent"], "domain-alpha")
        self.assertIsNone(response["sibling_groups"])
        sibling_ids = [item["id"] for item in response["siblings"]["items"]]
        self.assertIn("concept-echo", sibling_ids)
        self.assertNotIn("concept-gamma", sibling_ids)

    def test_entry_parent_must_be_a_parent(self):
        response = self.port.query_context("concept-gamma", entry_parent="domain-nope")
        self.assertEqual(response["error"]["code"], "invalid_request")

    def test_unknown_node_kind_is_accepted(self):
        response = self.port.query_context("vista-echo-panorama")
        self.assertEqual(validate_response("query_context", response, self.schema), [])
        level = self.port.query_level("domain-concept-work", 2, limit=500)
        kinds = {item["kind"] for item in level["page"]["items"]}
        self.assertIn("hologram-view", kinds)
        self.assertEqual(
            validate_response("query_level", level, self.schema), []
        )

    def test_brief_view_role_is_conforming(self):
        response = self.port.query_context("brief-2026-07-01-gaps")
        self.assertEqual(validate_response("query_context", response, self.schema), [])
        attrs = response["node"]["attrs"]
        self.assertEqual(attrs["role"], "view")
        self.assertIs(attrs["evidence_capable"], False)

    def test_logical_references_only(self):
        response = self.port.get_content("work-alpha-2020-echo")
        self.assertEqual(validate_response("get_content", response, self.schema), [])
        path = response["canonical_ref"]["path"]
        self.assertFalse(path.startswith("/"))
        self.assertNotIn("..", path)

    def test_url_path_is_rejected(self):
        response = self.port.get_content("work-alpha-2020-echo")
        response["canonical_ref"]["path"] = "https://example.org/papers/x.md"
        errors = validate_response("get_content", response, self.schema)
        self.assertTrue(any("URL" in error for error in errors), errors)

    def test_sibling_groups_must_cover_every_parent(self):
        response = self.port.query_context("concept-gamma")
        response["sibling_groups"] = response["sibling_groups"][:1]
        errors = validate_response("query_context", response, self.schema)
        self.assertTrue(
            any("cover each parent exactly once" in error for error in errors), errors
        )


class TestStaleIndex(unittest.TestCase):
    def setUp(self):
        self.schema = load_schema()

    def test_every_operation_rejects_stale(self):
        stale_port = ReferenceGraphQueryPort(current_vault_fingerprint="fp-vault-002")
        for op, call in CANONICAL_CALLS.items():
            response = call(stale_port)
            self.assertEqual(response["error"]["code"], "stale_index", op)
            self.assertIn("rebuild", response["error"]["message"])
            self.assertEqual(validate_response(op, response, self.schema), [], op)

    def test_unknown_operation_is_reported(self):
        errors = validate_response("mutate_graph", {"schema_version": "1.0"}, self.schema)
        self.assertTrue(errors and "unknown operation" in errors[0])


class TestInvalidFixtures(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schema = load_schema()

    def test_each_invalid_fixture_is_rejected_for_its_reason(self):
        seen = set()
        for name, (op, needle) in INVALID_EXPECTATIONS.items():
            message = json.loads((FIXTURES / "invalid" / name).read_text(encoding="utf-8"))
            errors = validate_response(
                op, message, self.schema, current_vault_fingerprint=INDEX_FINGERPRINT
            )
            self.assertTrue(errors, name)
            self.assertTrue(
                any(needle in error for error in errors),
                "%s: expected %r in %s" % (name, needle, errors),
            )
            seen.add(name)
        on_disk = {p.name for p in (FIXTURES / "invalid").glob("*.json")}
        self.assertEqual(seen, on_disk)

    def test_posix_absolute_path_is_rejected_by_schema_pattern(self):
        message = json.loads(
            (FIXTURES / "invalid" / "abs-path.json").read_text(encoding="utf-8")
        )
        message["canonical_ref"]["path"] = "/home/user/vault/papers/alpha.md"
        errors = validate_response("get_content", message, self.schema)
        self.assertTrue(any("does not match pattern" in error for error in errors), errors)


if __name__ == "__main__":
    unittest.main()
