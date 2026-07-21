"""The frozen brief bounds packages; the loop
terminates in two rounds; Results are never fabricated."""

import unittest

from knowledge_palace.workspace.brief import freeze, new_brief, validate_brief
from knowledge_palace.workspace.writing import (
    MAX_AUTO_ROUNDS,
    SectionLoop,
    new_package,
    validate_package,
)


def sample_brief(**overrides):
    base = dict(
        project="echo-paper",
        problem="echo cancellation drifts",
        contribution="a drift-aware canceller",
        sections=[
            {"name": "introduction", "kind": "introduction", "depends_on": []},
            {"name": "methods", "kind": "methods", "depends_on": ["introduction"]},
            {"name": "results", "kind": "results", "depends_on": ["methods"]},
        ],
        evidence=[
            {"ref": "claim:alpha-2020-echo#C1",
             "quote": "echo cancellation reduces drift",
             "anchor": "— §3 [¶2] / p.4"},
            {"ref": "project-source:doi:10.55555/elsewhere",
             "quote": "drift persists at scale",
             "anchor": "— §5 / p.11"},
        ],
        materials=["material:user-results-csv"],
    )
    base.update(overrides)
    return new_brief(**base)


class TestBrief(unittest.TestCase):
    def test_valid_brief_freezes_with_stable_fingerprint(self):
        brief = sample_brief()
        self.assertEqual(validate_brief(brief), [])
        self.assertEqual(freeze(brief)["fingerprint"], freeze(brief)["fingerprint"])

    def test_evidence_needs_id_shape_quote_and_anchor(self):
        bad = sample_brief(evidence=[{"ref": "the alpha paper", "quote": "q"}])
        errors = validate_brief(bad)
        self.assertTrue(any("not id-shaped" in e for e in errors))
        self.assertTrue(any("anchor required" in e for e in errors))

    def test_material_refs_are_barred_from_evidence(self):
        bad = sample_brief(
            evidence=[{"ref": "material:user-results-csv", "quote": "q", "anchor": "a"}]
        )
        errors = validate_brief(bad)
        self.assertTrue(any("never Claim evidence" in e for e in errors))

    def test_unknown_dependency_and_duplicate_names_rejected(self):
        bad = sample_brief(sections=[
            {"name": "methods", "kind": "methods", "depends_on": ["missing"]},
            {"name": "methods", "kind": "methods", "depends_on": []},
        ])
        errors = validate_brief(bad)
        self.assertTrue(any("unknown" in e for e in errors))
        self.assertTrue(any("unique" in e for e in errors))

    def test_invalid_brief_refuses_to_freeze(self):
        with self.assertRaises(ValueError):
            freeze(sample_brief(problem=""))

    def test_assembled_is_reserved(self):
        bad = sample_brief(sections=[
            {"name": "assembled", "kind": "other", "depends_on": []},
        ])
        errors = validate_brief(bad)
        self.assertTrue(any("reserved" in e for e in errors))


class TestPackage(unittest.TestCase):
    def setUp(self):
        self.brief = sample_brief()
        self.fingerprint = freeze(self.brief)["fingerprint"]

    def test_valid_package(self):
        package = new_package("methods", self.fingerprint,
                              evidence_refs=["claim:alpha-2020-echo#C1"])
        self.assertEqual(validate_package(package, self.brief), [])

    def test_beyond_brief_reference_rejected(self):
        package = new_package("methods", self.fingerprint,
                              evidence_refs=["claim:beta-2021-foxtrot#C1"])
        errors = validate_package(package, self.brief)
        self.assertTrue(any("outside the frozen brief" in e for e in errors))

    def test_stale_fingerprint_and_unknown_section_rejected(self):
        package = new_package("methods", "deadbeef")
        self.assertTrue(any("fingerprint" in e
                            for e in validate_package(package, self.brief)))
        package = new_package("acknowledgements", self.fingerprint)
        self.assertTrue(any("not in the brief" in e
                            for e in validate_package(package, self.brief)))

    def test_results_without_materials_must_be_placeholder_only(self):
        bare = new_package("results", self.fingerprint)
        errors = validate_package(bare, self.brief)
        self.assertTrue(any("never fabricated" in e for e in errors))
        with_data = new_package("results", self.fingerprint,
                                material_ids=["material:user-results-csv"])
        self.assertEqual(validate_package(with_data, self.brief), [])
        skeleton = new_package("results", self.fingerprint, placeholder_only=True)
        self.assertEqual(validate_package(skeleton, self.brief), [])

    def test_material_outside_brief_rejected(self):
        package = new_package("results", self.fingerprint,
                              material_ids=["material:not-registered"])
        errors = validate_package(package, self.brief)
        self.assertTrue(any("not in the frozen brief" in e for e in errors))

    def test_unfreezable_brief_reported_as_violation_not_raise(self):
        package = new_package("methods", self.fingerprint)
        errors = validate_package(package, sample_brief(problem=""))
        self.assertTrue(any("not freezable" in e for e in errors))


class TestSectionLoop(unittest.TestCase):
    def test_two_rounds_then_termination(self):
        loop = SectionLoop("methods")
        loop.record_draft()
        loop.record_review(["finding-1"])
        loop.record_revision()          # round 1
        loop.record_review(["finding-2"])
        loop.record_revision()          # round 2
        loop.record_review(["finding-3"])
        with self.assertRaises(ValueError):
            loop.record_revision()      # a third automatic round refuses
        result = loop.deliver()
        self.assertEqual(result["status"], "unresolved")
        self.assertEqual(result["unresolved"], ["finding-3"])
        self.assertEqual(result["rounds"], MAX_AUTO_ROUNDS)

    def test_clean_review_delivers_clean(self):
        loop = SectionLoop("introduction")
        loop.record_draft()
        loop.record_review([])
        with self.assertRaises(ValueError):
            loop.record_revision()      # nothing to revise
        self.assertEqual(loop.deliver()["status"], "clean")

    def test_state_machine_rejects_out_of_order_events(self):
        loop = SectionLoop("methods")
        with self.assertRaises(ValueError):
            loop.record_review([])      # review before draft
        loop.record_draft()
        with self.assertRaises(ValueError):
            loop.deliver()              # deliver before review


if __name__ == "__main__":
    unittest.main()
