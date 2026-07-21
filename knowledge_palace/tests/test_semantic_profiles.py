"""StudyProfiles are claim-reference views — one role
set, no free text, every field resolving to quote+anchor, no profile when
nothing applies."""

import unittest
from pathlib import Path

from knowledge_palace.graph.identity import load_vault_identity, parse_profile_section
from knowledge_palace.semantic.profiles import (
    ROLE_SETS,
    build_profile_view,
    classify_roles,
    validate_profile,
)

MINI = Path(__file__).resolve().parent / "fixtures" / "vault-mini"


class TestRoleSets(unittest.TestCase):
    def test_role_vocabularies_are_disjoint(self):
        seen = set()
        for fields in ROLE_SETS.values():
            self.assertFalse(seen & set(fields))
            seen |= set(fields)

    def test_classification(self):
        self.assertEqual(classify_roles({"method": ["C1"]}), ("empirical", []))
        self.assertEqual(classify_roles({"corpus": ["C1"], "synthesis": ["C2"]}), ("review", []))
        self.assertEqual(classify_roles({}), (None, []))
        kind, errors = classify_roles({"method": ["C1"], "corpus": ["C2"]})
        self.assertIsNone(kind)
        self.assertTrue(errors and "fit no role set" in errors[0])


class TestValidationAndView(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.identity = load_vault_identity(MINI)
        cls.claims = cls.identity["claims"]

    def test_vault_mini_alpha_profile_parses_and_validates(self):
        roles = self.identity["works"]["alpha-2020-echo"]["profile_roles"]
        self.assertEqual(roles, {"method": ["C1"], "limitations": ["C2"]})
        report = validate_profile("alpha-2020-echo", roles, self.claims)
        self.assertTrue(report["ok"], report)
        self.assertEqual(report["kind"], "empirical")

    def test_view_resolves_every_field_to_quote_and_anchor(self):
        roles = self.identity["works"]["alpha-2020-echo"]["profile_roles"]
        view = build_profile_view("alpha-2020-echo", roles, self.claims)
        self.assertEqual(view["kind"], "empirical")
        method = view["roles"]["method"][0]
        self.assertEqual(method["claim"], "alpha-2020-echo#C1")
        self.assertIn("improves by delta", method["quote"])
        self.assertEqual(method["anchor"], "§2 [¶1] / p.2")

    def test_no_roles_means_no_profile(self):
        self.assertEqual(self.identity["works"]["beta-2021-foxtrot"]["profile_roles"], {})
        self.assertIsNone(build_profile_view("beta-2021-foxtrot", {}, self.claims))

    def test_free_text_and_missing_claims_are_typed_errors(self):
        report = validate_profile(
            "alpha-2020-echo",
            {"method": ["a convolutional network"], "limitations": ["C9"]},
            self.claims,
        )
        self.assertFalse(report["ok"])
        self.assertTrue(any("free-text" in e for e in report["errors"]))
        self.assertTrue(any("missing claim C9" in e for e in report["errors"]))
        with self.assertRaises(ValueError):
            build_profile_view("alpha-2020-echo", {"method": ["C9"]}, self.claims)

    def test_profile_section_parser_reports_bad_lines(self):
        roles, problems = parse_profile_section(
            "## Study profile\n\n- method: C1\n- vibe: excellent\n- method: C2\n",
            "test",
        )
        self.assertEqual(roles, {"method": ["C1"]})
        self.assertEqual(len(problems), 2)  # free-text line + duplicate role


if __name__ == "__main__":
    unittest.main()
