"""Project Source Vault-Hit dedup and the recorded
external-novelty opt-in."""

import unittest
from pathlib import Path

from knowledge_palace.graph.identity import load_vault_identity
from knowledge_palace.interaction.project_source import (
    EXTERNAL_MAX_CANDIDATES,
    new_request,
    resolve,
    validate_request,
    validate_source,
)

MINI = Path(__file__).resolve().parent / "fixtures" / "vault-mini"


class TestResolve(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.identity = load_vault_identity(MINI)

    def test_doi_vault_hit_reuses_existing_work(self):
        result = resolve(
            {"ids": {"doi": "10.99999/fixture.alpha2020"}, "title": "Some retitled copy"},
            self.identity,
        )
        self.assertEqual(result, {"kind": "vault-hit", "work": "work:alpha-2020-echo"})

    def test_miss_becomes_quarantined_project_source(self):
        result = resolve(
            {"ids": {"doi": "10.55555/elsewhere"}, "title": "Foreign paper", "year": 2025},
            self.identity,
        )
        self.assertEqual(result["kind"], "project-source")
        self.assertEqual(result["ref"], "project-source:doi:10.55555/elsewhere")
        self.assertTrue(result["verified"])
        self.assertIs(result["project_local"], True)
        self.assertIs(result["auto_ingest"], False)
        self.assertEqual(validate_source(result), [])

    def test_title_only_miss_is_recorded_but_not_assessment_usable(self):
        result = resolve({"title": "An unidentifiable manuscript"}, self.identity)
        self.assertFalse(result["verified"])
        errors = validate_source(result)
        self.assertTrue(any("verified identity" in e for e in errors))

    def test_unidentifiable_reference_raises(self):
        with self.assertRaises(ValueError):
            resolve({"ids": {}, "title": ""}, self.identity)

    def test_tampered_flags_are_validation_errors(self):
        result = resolve({"ids": {"doi": "10.55555/elsewhere"}}, self.identity)
        for key, value in (("project_local", False), ("auto_ingest", True)):
            tampered = dict(result)
            tampered[key] = value
            self.assertTrue(validate_source(tampered), key)


class TestExternalNoveltyRequest(unittest.TestCase):
    def test_refuses_without_user_confirmation(self):
        with self.assertRaises(ValueError):
            new_request("s-1", "openalex", "2026-07-14")

    def test_confirmed_request_records_bounds(self):
        request = new_request("s-1", "openalex", "2026-07-14", user_confirmed=True,
                              max_candidates=99)
        self.assertEqual(request["hops"], 1)
        self.assertEqual(request["max_candidates"], EXTERNAL_MAX_CANDIDATES)  # clamped
        self.assertIs(request["user_confirmed"], True)
        self.assertEqual(validate_request(request), [])

    def test_validator_pins_hops_bounds_and_confirmation(self):
        good = new_request("s-1", "openalex", "2026-07-14", user_confirmed=True)
        for key, value in (
            ("hops", 2),
            ("max_candidates", 21),
            ("max_candidates", 0),
            ("user_confirmed", False),
            ("scope", ""),
            ("date", None),
        ):
            broken = dict(good)
            broken[key] = value
            self.assertTrue(validate_request(broken), key)


if __name__ == "__main__":
    unittest.main()
