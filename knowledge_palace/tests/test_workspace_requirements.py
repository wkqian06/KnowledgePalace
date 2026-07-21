"""Anchored rows, named coverage, honest degradation."""

import unittest

from knowledge_palace.workspace.requirements import (
    GENERIC_ROWS,
    coverage,
    extract_requirements,
    generic_matrix,
    new_matrix,
    validate_matrix,
)

SOLICITATION = """Overview of the program.
Proposals must include a data management plan.
This paragraph is descriptive only.
The PI shall describe evaluation metrics.
Budgets are required for all subawards.
"""


class TestExtractor(unittest.TestCase):
    def test_modal_lines_become_anchored_rows(self):
        rows = extract_requirements(SOLICITATION)
        self.assertEqual([r["id"] for r in rows], ["R1", "R2", "R3"])
        self.assertEqual(rows[0]["anchor"], "line 2")
        self.assertEqual(rows[1]["anchor"], "line 4")
        self.assertIn("data management plan", rows[0]["text"])

    def test_deterministic(self):
        self.assertEqual(extract_requirements(SOLICITATION),
                         extract_requirements(SOLICITATION))

    def test_no_modal_lines_yields_empty(self):
        self.assertEqual(extract_requirements("just prose here"), [])


class TestMatrix(unittest.TestCase):
    def test_sourced_matrix_valid(self):
        matrix = new_matrix("NSF-24-501.txt", extract_requirements(SOLICITATION))
        self.assertEqual(validate_matrix(matrix), [])
        self.assertIs(matrix["compliance_verifiable"], True)

    def test_generic_fallback_born_unverifiable(self):
        matrix = generic_matrix("no solicitation supplied")
        self.assertIs(matrix["compliance_verifiable"], False)
        self.assertEqual(validate_matrix(matrix), [])
        self.assertEqual(len(matrix["rows"]), len(GENERIC_ROWS))

    def test_tampered_generic_flag_rejected(self):
        matrix = generic_matrix("no solicitation supplied")
        matrix["compliance_verifiable"] = True
        errors = validate_matrix(matrix)
        self.assertTrue(any("unverifiable" in e for e in errors))

    def test_generic_without_reason_rejected(self):
        matrix = generic_matrix("")
        errors = validate_matrix(matrix)
        self.assertTrue(any("name why it degraded" in e for e in errors))

    def test_duplicate_and_unanchored_rows_rejected(self):
        matrix = new_matrix("s.txt", [
            {"id": "R1", "text": "a", "anchor": "line 1"},
            {"id": "R1", "text": "b", "anchor": ""},
        ])
        errors = validate_matrix(matrix)
        self.assertTrue(any("duplicate" in e for e in errors))
        self.assertTrue(any("missing anchor" in e for e in errors))


class TestCoverage(unittest.TestCase):
    def test_uncovered_named_never_summarized(self):
        matrix = new_matrix("s.txt", extract_requirements(SOLICITATION))
        result = coverage(matrix, {"approach": ["R1"], "evaluation": ["R2"]})
        self.assertEqual(result["covered"], ["R1", "R2"])
        self.assertEqual(result["uncovered"], ["R3"])  # named, not counted
        self.assertEqual(result["unknown_refs"], [])

    def test_unknown_refs_surface(self):
        matrix = generic_matrix("none")
        result = coverage(matrix, {"summary": ["G1", "R99"]})
        self.assertEqual(result["unknown_refs"], ["summary -> R99"])


if __name__ == "__main__":
    unittest.main()
