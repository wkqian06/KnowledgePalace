"""Global candidate identity, occurrence merging, and
Scope-bound decisions with no global blacklist."""

import unittest
from pathlib import Path

from knowledge_palace.expansion.candidates import (
    CandidatePool,
    build_hit_index,
    candidate_key,
    vault_hit,
)
from knowledge_palace.graph.identity import load_vault_identity

MINI = Path(__file__).resolve().parent / "fixtures" / "vault-mini"


class TestIdentityKeys(unittest.TestCase):
    def test_precedence_doi_over_openalex_over_arxiv_over_title(self):
        record = {
            "ids": {"doi": "10.9/X", "openalex": "W1", "arxiv": "1234.5678"},
            "title": "Some Title",
        }
        self.assertEqual(candidate_key(record), "doi:10.9/x")
        del record["ids"]["doi"]
        self.assertEqual(candidate_key(record), "openalex:w1")
        del record["ids"]["openalex"]
        self.assertEqual(candidate_key(record), "arxiv:1234.5678")
        record["ids"] = {}
        self.assertTrue(candidate_key(record).startswith("title:"))
        self.assertIsNone(candidate_key({"ids": {}, "title": "  "}))

    def test_title_key_is_normalization_stable(self):
        a = candidate_key({"title": "Echo,  Cancellation: In ALPHA Systems!"})
        b = candidate_key({"title": "echo cancellation in alpha systems"})
        self.assertEqual(a, b)


class TestPool(unittest.TestCase):
    def test_one_candidate_many_occurrences_and_id_merge(self):
        pool = CandidatePool()
        key_1, new_1 = pool.upsert(
            {"ids": {"doi": "10.9/b"}, "title": "B"}, "run-1", "seed-a", "references", 1
        )
        key_2, new_2 = pool.upsert(
            {"ids": {"doi": "10.9/B", "arxiv": "2201.0001"}}, "run-1", "seed-c", "cited_by", 2
        )
        self.assertEqual(key_1, key_2)
        self.assertTrue(new_1)
        self.assertFalse(new_2)
        entry = pool.get(key_1)
        self.assertEqual(len(entry["occurrences"]), 2)
        self.assertEqual(entry["ids"]["arxiv"], "2201.0001")  # merged
        self.assertEqual(entry["title"], "B")  # kept
        # Idempotent re-discovery (checkpoint resume): no duplicate occurrence.
        pool.upsert({"ids": {"doi": "10.9/b"}}, "run-1", "seed-a", "references", 1)
        self.assertEqual(len(pool.get(key_1)["occurrences"]), 2)

    def test_verified_requires_an_external_id(self):
        pool = CandidatePool()
        key_id, _ = pool.upsert({"ids": {"doi": "10.9/v"}}, "r", "s", "references", 1)
        key_title, _ = pool.upsert({"title": "Only A Title"}, "r", "s", "references", 1)
        self.assertTrue(pool.get(key_id)["verified"])
        self.assertFalse(pool.get(key_title)["verified"])

    def test_decisions_are_scope_bound_never_global(self):
        pool = CandidatePool()
        key, _ = pool.upsert({"ids": {"doi": "10.9/b"}}, "r", "s", "references", 1)
        pool.decide(key, "scope-a", "rejected", "off-topic for A")
        pool.decide(key, "scope-b", "selected", "core for B", exploratory=False)
        self.assertEqual(pool.decision_for(key, "scope-a")["decision"], "rejected")
        self.assertEqual(pool.decision_for(key, "scope-b")["decision"], "selected")
        self.assertIsNone(pool.decision_for(key, "scope-c"))  # untouched scope

    def test_decision_validation(self):
        pool = CandidatePool()
        key, _ = pool.upsert({"ids": {"doi": "10.9/b"}}, "r", "s", "references", 1)
        with self.assertRaises(ValueError):
            pool.decide(key, "scope-a", "blacklisted", "no such verdict")
        with self.assertRaises(ValueError):
            pool.decide("doi:ghost", "scope-a", "selected", "unknown key")

    def test_payload_round_trip(self):
        pool = CandidatePool()
        pool.upsert({"ids": {"doi": "10.9/b"}, "title": "B"}, "r", "s", "references", 1)
        clone = CandidatePool.from_payload(pool.to_payload())
        self.assertEqual(clone.to_payload(), pool.to_payload())


class TestVaultHit(unittest.TestCase):
    def test_hit_by_doi_and_arxiv_from_real_identity_loader(self):
        identity = load_vault_identity(MINI)
        index = build_hit_index(identity)
        self.assertEqual(
            vault_hit({"ids": {"doi": "10.99999/Fixture.Alpha2020"}}, index),
            "alpha-2020-echo",
        )
        self.assertEqual(
            vault_hit({"ids": {"arxiv": "2101.00001"}}, index), "beta-2021-foxtrot"
        )
        self.assertIsNone(vault_hit({"ids": {"doi": "10.9/unknown"}}, index))
        self.assertIsNone(vault_hit({"title": "Bridging Gamma Across Domains"}, index))


if __name__ == "__main__":
    unittest.main()
