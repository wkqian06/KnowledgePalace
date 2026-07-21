"""CoverageReport verdict semantics and the
schema-level quarantine of external material."""

import unittest
from pathlib import Path

from knowledge_palace.graph.builder import build_payload
from knowledge_palace.interaction.coverage import (
    holes,
    new_external_source,
    new_report,
    new_subquestion,
    validate_report,
)

MINI = Path(__file__).resolve().parent / "fixtures" / "vault-mini"

COVERED = new_subquestion("what is echo?", "covered", ["claim:alpha-2020-echo#C1"])
HOLE = new_subquestion("what about foxtrot drift?", "hole")


class TestVerdictSemantics(unittest.TestCase):
    def test_sufficient_all_covered(self):
        report = new_report("sufficient", [COVERED])
        self.assertEqual(validate_report(report), [])

    def test_sufficient_cannot_carry_holes(self):
        report = new_report("sufficient", [COVERED, HOLE])
        self.assertTrue(any("cannot carry holes" in e for e in validate_report(report)))

    def test_covered_requires_evidence(self):
        bare = new_subquestion("q", "covered", [])
        errors = validate_report(new_report("sufficient", [bare]))
        self.assertTrue(any("without evidence" in e for e in errors))

    def test_partial_requires_both_sides(self):
        good = new_report("partial", [COVERED, HOLE])
        self.assertEqual(validate_report(good), [])
        for subs in ([COVERED], [HOLE]):
            errors = validate_report(new_report("partial", subs))
            self.assertTrue(any("partial verdict requires" in e for e in errors), subs)

    def test_insufficient_never_fabricates_and_needs_a_proposal(self):
        good = new_report("insufficient", [HOLE], proposal_ref="prop-1")
        self.assertEqual(validate_report(good), [])
        errors = validate_report(new_report("insufficient", [HOLE]))
        self.assertTrue(any("ExpansionProposal" in e for e in errors))
        errors = validate_report(
            new_report("insufficient", [COVERED, HOLE], proposal_ref="prop-1")
        )
        self.assertTrue(any("must not present" in e for e in errors))

    def test_unknown_verdict_and_empty_subquestions(self):
        self.assertTrue(validate_report(new_report("maybe", [COVERED])))
        self.assertTrue(any(
            "non-empty" in e for e in validate_report(new_report("sufficient", []))
        ))

    def test_holes_helper(self):
        report = new_report("partial", [COVERED, HOLE])
        self.assertEqual(holes(report), ["what about foxtrot drift?"])


class TestEvidenceRefs(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.payload = build_payload(MINI)

    def test_evidence_must_be_id_shaped(self):
        sub = new_subquestion("q", "covered", ["the paper says so"])
        errors = validate_report(new_report("sufficient", [sub]))
        self.assertTrue(any("not an index id" in e for e in errors))

    def test_evidence_resolution_against_payload(self):
        good = new_subquestion("q", "covered", ["work:alpha-2020-echo"])
        self.assertEqual(
            validate_report(new_report("sufficient", [good]), self.payload), []
        )
        ghost = new_subquestion("q", "covered", ["work:ghost-2020"])
        errors = validate_report(new_report("sufficient", [ghost]), self.payload)
        self.assertTrue(any("not in the index" in e for e in errors))


class TestExternalQuarantine(unittest.TestCase):
    def test_constructor_forces_the_flags(self):
        source = new_external_source("https://example.org/x", "found via web")
        self.assertIs(source["session_local"], True)
        self.assertIs(source["vault_eligible"], False)

    def test_tampered_flags_are_rejected(self):
        report = new_report(
            "partial",
            [COVERED, HOLE],
            external_sources=[
                {"locator": "https://x", "session_local": False, "vault_eligible": False},
                {"locator": "https://y", "session_local": True, "vault_eligible": True},
                {"note": "no locator"},
            ],
        )
        errors = validate_report(report)
        self.assertTrue(any("must be session_local" in e for e in errors))
        self.assertTrue(any("never be vault_eligible" in e for e in errors))
        self.assertTrue(any("needs a locator" in e for e in errors))


if __name__ == "__main__":
    unittest.main()
