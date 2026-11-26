"""Deterministic, bounded, id-only retrieval with
corridor-powered cross-domain reach."""

import unittest
from pathlib import Path

from knowledge_palace.graph.builder import build_payload
from knowledge_palace.interaction.prefilter import (
    CANDIDATE_CAP,
    extract_terms,
    find_candidates,
    rank_matches,
)
from knowledge_palace.semantic.corridors import domain_resolver
from knowledge_palace.tests.test_semantic_corridors import synthetic_dense_payload

MINI = Path(__file__).resolve().parent / "fixtures" / "vault-mini"


class TestTerms(unittest.TestCase):
    def test_extraction_dedup_order_and_default_stopwords(self):
        terms = extract_terms("What does the ECHO cancellation echo imply?")
        self.assertEqual(terms, ["echo", "cancellation", "imply"])

    def test_injected_policy_stopwords(self):
        terms = extract_terms("deep-learning echo model", stopwords=["deep-learning", "model"])
        self.assertEqual(terms, ["echo"])


class TestRank(unittest.TestCase):
    def test_coverage_beats_corridors_and_tags_beat_quotes(self):
        matches = {"work:a": {"claim:a#C1 (term:pool)"} | {"corridor:concept:x%d" % n for n in range(18)},
                   "work:b": {"term:cold", "claim:b#C1 (term:pool)"}}
        self.assertEqual(rank_matches({"parents": {}}, matches), ["work:b", "work:a"])
        matches = {"work:c": {"claim:c#C1 (term:cold)", "claim:c#C2 (term:cold)"},
                   "work:d": {"concept:concept:cold-pool (term:cold)"}}
        self.assertEqual(rank_matches({"parents": {}}, matches), ["work:d", "work:c"])

    def test_claim_share_breaks_ties_not_card_length(self):
        parents = {"claim:long#C%d" % n: ["work:long"] for n in range(1, 11)}
        parents.update({"claim:short#C1": ["work:short"], "claim:short#C2": ["work:short"]})
        matches = {"work:long": {"term:cold", "claim:claim:long#C1 (term:cold)", "claim:claim:long#C2 (term:cold)"},
                   "work:short": {"term:cold", "claim:claim:short#C1 (term:cold)"}}
        self.assertEqual(rank_matches({"parents": parents}, matches), ["work:short", "work:long"])


class TestVaultMiniRetrieval(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.payload = build_payload(MINI)

    def test_deterministic_and_id_only(self):
        first = find_candidates(self.payload, "echo cancellation noise")
        second = find_candidates(self.payload, "echo cancellation noise")
        self.assertEqual(first, second)
        self.assertTrue(first)
        for candidate in first:
            self.assertEqual(sorted(candidate), ["canonical_ref", "node_id", "why"])
            self.assertNotIn("Fixture paper", str(candidate))  # no card text

    def test_direct_and_concept_attached_hits(self):
        candidates = find_candidates(self.payload, "echo cancellation")
        ids = [c["node_id"] for c in candidates]
        self.assertIn("work:alpha-2020-echo", ids)
        self.assertIn("gap:gap-echo-noise", ids)  # attached via concept-echo
        alpha = next(c for c in candidates if c["node_id"] == "work:alpha-2020-echo")
        self.assertTrue(any(why.startswith("term:") for why in alpha["why"]))

    def test_cross_domain_reach_via_corridors(self):
        candidates = find_candidates(self.payload, "shared pattern bridging")
        ids = {c["node_id"] for c in candidates}
        domains_of = domain_resolver(self.payload)
        touched = set()
        for node_id in ids:
            touched |= domains_of(node_id)
        self.assertIn("domain:alpha-domain", touched)
        self.assertIn("domain:beta-domain", touched)  # foreign side reached
        corridor_reasons = [
            why for c in candidates for why in c["why"] if why.startswith("corridor:")
        ]
        self.assertTrue(corridor_reasons)

    def test_no_hits_yields_empty_not_error(self):
        self.assertEqual(find_candidates(self.payload, "zzz qqq unrelated"), [])


class TestBoundedness(unittest.TestCase):
    def test_cap_enforced_on_dense_payload(self):
        payload = synthetic_dense_payload(concepts=30)
        candidates = find_candidates(payload, "shared")
        self.assertEqual(len(candidates), CANDIDATE_CAP)
        again = find_candidates(payload, "shared")
        self.assertEqual(candidates, again)

    def test_cap_parameter_clamps(self):
        payload = synthetic_dense_payload(concepts=30)
        self.assertEqual(len(find_candidates(payload, "shared", cap=99)), CANDIDATE_CAP)
        self.assertEqual(len(find_candidates(payload, "shared", cap=3)), 3)


if __name__ == "__main__":
    unittest.main()
