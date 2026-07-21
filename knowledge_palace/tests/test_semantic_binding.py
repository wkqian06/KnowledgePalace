"""The new-ingest binding rule — bound drafts pass,
unbound/unknown fail with typed reasons, historical claims stay valid."""

import unittest
from pathlib import Path

from knowledge_palace.graph.identity import load_vault_identity, parse_claims
from knowledge_palace.semantic.binding import validate_claims, validate_draft

MINI = Path(__file__).resolve().parent / "fixtures" / "vault-mini"
REGISTRY = {"concept-echo": {}, "method-delta": {}, "concept-gamma": {}}

BOUND_DRAFT = """## Claims

- C1 [concept-echo]: "Quote one." — §1 / p.1
- C2 [concept-echo, method-delta]: "Quote two." — §2 / p.2
"""

UNBOUND_DRAFT = """## Claims

- C1 [concept-echo]: "Quote one." — §1 / p.1
- C2: "Historical-style claim." — §2 / p.2
"""

UNKNOWN_DRAFT = """## Claims

- C1 [concept-ghost]: "Quote one." — §1 / p.1
"""


class TestBindingRule(unittest.TestCase):
    def test_bound_draft_passes(self):
        report = validate_draft(BOUND_DRAFT, REGISTRY)
        self.assertTrue(report["ok"], report)
        self.assertEqual(report["bound"], [1, 2])
        self.assertEqual(report["claims"], 2)

    def test_unbound_claim_fails_with_typed_reason(self):
        report = validate_draft(UNBOUND_DRAFT, REGISTRY)
        self.assertFalse(report["ok"])
        self.assertEqual(report["unbound"], [(2, "no concept binding")])
        self.assertEqual(report["bound"], [1])

    def test_unknown_slug_fails_and_names_the_slugs(self):
        report = validate_draft(UNKNOWN_DRAFT, REGISTRY)
        self.assertFalse(report["ok"])
        self.assertEqual(report["unknown"], [(1, ["concept-ghost"])])

    def test_empty_draft_fails(self):
        report = validate_draft("## Claims\n\nno claims here\n", REGISTRY)
        self.assertFalse(report["ok"])
        self.assertIn((0, "draft contains no claims"), report["unbound"])

    def test_missing_anchor_still_fails_via_parse_problems(self):
        report = validate_draft(
            '## Claims\n\n- C1 [concept-echo]: "No anchor here."\n', REGISTRY
        )
        self.assertFalse(report["ok"])
        self.assertTrue(report["parse_problems"])


class TestBackwardCompatibility(unittest.TestCase):
    def test_bracket_group_is_optional_and_additive(self):
        claims, problems = parse_claims(
            '- C1: "Old style." — §1 / p.1\n'
            '- C2 [concept-echo]: "New style." — §2 / p.2\n',
            "test",
        )
        self.assertEqual(problems, [])
        self.assertEqual(claims[0]["concepts"], [])
        self.assertEqual(claims[1]["concepts"], ["concept-echo"])
        self.assertEqual(claims[0]["quote"], '"Old style."')
        self.assertEqual(claims[1]["anchor"], "§2 / p.2")

    def test_vault_mini_parses_with_bindings_and_history_intact(self):
        identity = load_vault_identity(MINI)
        self.assertEqual(identity["parse_errors"], [])
        self.assertEqual(len(identity["claims"]), 4)  # count unchanged
        bound = identity["claims"]["alpha-2020-echo#C1"]
        self.assertEqual(bound["concepts"], ["concept-echo", "method-delta"])
        self.assertEqual(identity["claims"]["alpha-2020-echo#C2"]["concepts"], [])
        # Historical claims (validated as a batch) are simply not run through
        # the new-ingest rule; when they are, they report unbound — proving
        # the rule is enforceable at migration time too.
        report = validate_claims(
            [identity["claims"]["beta-2021-foxtrot#C1"]], {"concept-foxtrot": {}}
        )
        self.assertFalse(report["ok"])


if __name__ == "__main__":
    unittest.main()
