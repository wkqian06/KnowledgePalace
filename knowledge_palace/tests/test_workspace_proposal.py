"""Aims/approach alignment, the User Material fact
boundary, and writing package rules enforced through the proposal path."""

import unittest

from knowledge_palace.tests.test_workspace_writing import sample_brief
from knowledge_palace.workspace.brief import freeze
from knowledge_palace.workspace.proposal import (
    PROPOSAL_SECTION_KINDS,
    new_proposal_package,
    validate_alignment,
    validate_proposal_package,
)
from knowledge_palace.workspace.requirements import generic_matrix, new_matrix


def proposal_brief():
    return sample_brief(sections=[
        {"name": "specific-aims", "kind": "specific-aims", "depends_on": []},
        {"name": "approach", "kind": "approach", "depends_on": ["specific-aims"]},
        {"name": "preliminary-results", "kind": "preliminary-results",
         "depends_on": ["approach"]},
    ])


class TestAlignment(unittest.TestCase):
    def test_full_map_passes(self):
        findings = validate_alignment(
            ["aim-1", "aim-2"],
            {"experiment-a": ["aim-1"], "experiment-b": ["aim-2", "aim-1"]},
        )
        self.assertEqual(findings, [])

    def test_orphans_on_both_sides_named(self):
        findings = validate_alignment(
            ["aim-1", "aim-2"],
            {"experiment-a": ["aim-1"], "experiment-x": [], "experiment-y": ["aim-9"]},
        )
        self.assertTrue(any("orphan" in f and "aim-2" in f for f in findings))
        self.assertTrue(any("maps to no aim" in f for f in findings))
        self.assertTrue(any("unknown aim 'aim-9'" in f for f in findings))


class TestProposalPackage(unittest.TestCase):
    def setUp(self):
        self.brief = proposal_brief()
        self.fingerprint = freeze(self.brief)["fingerprint"]
        self.matrix = new_matrix("s.txt", [
            {"id": "R1", "text": "aims required", "anchor": "line 1"},
        ])

    def test_ten_section_kinds(self):
        self.assertEqual(len(PROPOSAL_SECTION_KINDS), 10)

    def test_valid_package_with_matrix_ref(self):
        package = new_proposal_package(
            "approach", self.fingerprint,
            evidence_refs=["claim:alpha-2020-echo#C1"],
            requirement_refs=["R1"],
        )
        self.assertEqual(
            validate_proposal_package(package, self.brief, self.matrix), []
        )

    def test_requirement_outside_matrix_rejected(self):
        package = new_proposal_package("approach", self.fingerprint,
                                       requirement_refs=["R99"])
        errors = validate_proposal_package(package, self.brief, self.matrix)
        self.assertTrue(any("not in the matrix" in e for e in errors))

    def test_user_facts_require_materials(self):
        bare = new_proposal_package("approach", self.fingerprint,
                                    user_facts=["budget"])
        errors = validate_proposal_package(bare, self.brief, self.matrix)
        self.assertTrue(any("never come from the model" in e for e in errors))
        backed = new_proposal_package(
            "approach", self.fingerprint,
            material_ids=["material:user-results-csv"], user_facts=["budget"],
        )
        self.assertEqual(
            validate_proposal_package(backed, self.brief, self.matrix), []
        )

    def test_unknown_user_fact_kind_rejected(self):
        package = new_proposal_package(
            "approach", self.fingerprint,
            material_ids=["material:user-results-csv"], user_facts=["vibes"],
        )
        errors = validate_proposal_package(package, self.brief, self.matrix)
        self.assertTrue(any("user fact" in e for e in errors))

    def test_kp09_rules_still_enforced_through_proposal_path(self):
        stale = new_proposal_package("approach", "deadbeef")
        errors = validate_proposal_package(stale, self.brief, self.matrix)
        self.assertTrue(any("fingerprint" in e for e in errors))
        beyond = new_proposal_package(
            "approach", self.fingerprint,
            evidence_refs=["claim:beta-2021-foxtrot#C1"],
        )
        errors = validate_proposal_package(beyond, self.brief, self.matrix)
        self.assertTrue(any("outside the frozen brief" in e for e in errors))
        bare_prelim = new_proposal_package("preliminary-results", self.fingerprint)
        errors = validate_proposal_package(bare_prelim, self.brief,
                                           generic_matrix("none"))
        self.assertTrue(any("never fabricated" in e for e in errors))


if __name__ == "__main__":
    unittest.main()
