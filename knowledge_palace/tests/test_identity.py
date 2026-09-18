"""Deterministic Work/Claim identity;
exact-id collisions and fuzzy titles surface as confirmations, never merges."""

import shutil
import tempfile
import unittest
from pathlib import Path

from knowledge_palace.graph.identity import domain_partition_report, load_vault_identity

MINI = Path(__file__).resolve().parent / "fixtures" / "vault-mini"


def _tmp_vault(test):
    tmp = tempfile.TemporaryDirectory()
    test.addCleanup(tmp.cleanup)
    target = Path(tmp.name) / "vault"
    shutil.copytree(MINI, target)
    return target


class TestCleanFixture(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.identity = load_vault_identity(MINI)

    def test_counts(self):
        self.assertEqual(len(self.identity["works"]), 3)
        self.assertEqual(len(self.identity["claims"]), 4)
        self.assertEqual(len(self.identity["gaps"]), 2)
        self.assertEqual(len(self.identity["transfers"]), 1)
        self.assertEqual(len(self.identity["briefs"]), 1)
        self.assertEqual(len(self.identity["domains"]), 2)

    def test_clean_fixture_has_no_findings(self):
        self.assertEqual(self.identity["parse_errors"], [])
        self.assertEqual(self.identity["confirmations"], [])

    def test_external_ids(self):
        works = self.identity["works"]
        self.assertEqual(
            works["alpha-2020-echo"]["external_ids"], {"doi": "10.99999/fixture.alpha2020"}
        )
        self.assertEqual(works["beta-2021-foxtrot"]["external_ids"], {"arxiv": "2101.00001"})
        self.assertEqual(works["gamma-2022-bridge"]["external_ids"], {})

    def test_claim_refs_are_verbatim_and_anchored(self):
        claim = self.identity["claims"]["alpha-2020-echo#C1"]
        self.assertEqual(claim["work"], "alpha-2020-echo")
        self.assertTrue(claim["quote"].startswith('"Echo cancellation improves'))
        self.assertEqual(claim["anchor"], "§2 [¶1] / p.2")

    def test_multiline_claim_joins_quote_and_finds_anchor(self):
        vault = _tmp_vault(self)
        card = vault / "papers" / "alpha-2020-echo.md"
        card.write_text(
            card.read_text(encoding="utf-8")
            + '\n- C3: "A very long verbatim quote that\n'
            + '  wraps across two continuation lines\n'
            + '  before its anchor." — §7 [¶2] / p.11\n',
            encoding="utf-8",
        )
        identity = load_vault_identity(vault)
        claim = identity["claims"]["alpha-2020-echo#C3"]
        self.assertEqual(claim["anchor"], "§7 [¶2] / p.11")
        self.assertIn("wraps across two continuation lines", claim["quote"])
        self.assertNotIn("\n", claim["quote"])
        self.assertEqual(
            [e for e in identity["parse_errors"] if "C3" in e], []
        )

    def test_retraction_detaches_a_wrong_source_quote(self):
        vault = _tmp_vault(self)
        card = vault / "papers" / "alpha-2020-echo.md"
        card.write_text(
            card.read_text(encoding="utf-8")
            + '\n- Retraction of C2 (2026-09-18): this sentence is not in this\n'
            + '  paper; it belongs to beta-2021-drift.\n',
            encoding="utf-8",
        )
        identity = load_vault_identity(vault)
        retracted = identity["claims"]["alpha-2020-echo#C2"]["retracted"]
        self.assertEqual(retracted["date"], "2026-09-18")
        self.assertIn("belongs to beta-2021-drift", retracted["note"])
        self.assertIsNone(identity["claims"]["alpha-2020-echo#C1"]["retracted"])
        self.assertEqual([e for e in identity["parse_errors"] if "C2" in e], [])

    def test_retraction_without_a_claim_is_reported(self):
        vault = _tmp_vault(self)
        card = vault / "papers" / "alpha-2020-echo.md"
        card.write_text(
            card.read_text(encoding="utf-8")
            + '\n- Retraction of C9 (2026-09-18): no such claim.\n',
            encoding="utf-8",
        )
        identity = load_vault_identity(vault)
        self.assertTrue(
            any("retraction of C9 has no such claim" in e for e in identity["parse_errors"]))

    def test_multi_parent_registry_row(self):
        self.assertEqual(
            self.identity["registry"]["concept-gamma"]["parents"],
            ["alpha-domain", "beta-domain"],
        )

    def test_gap_relations_parsed(self):
        self.assertEqual(
            self.identity["works"]["gamma-2022-bridge"]["gaps"],
            [("gap-gamma-drift", "identifies")],
        )


class TestFindingsSurfaceNeverMerge(unittest.TestCase):
    def test_duplicate_doi_is_a_confirmation_not_a_merge(self):
        vault = _tmp_vault(self)
        clone = (MINI / "papers" / "alpha-2020-echo.md").read_text(encoding="utf-8")
        clone = clone.replace("slug: alpha-2020-echo", "slug: copycat-2020-echo")
        clone = clone.replace(
            "Echo Cancellation in Alpha Systems", "A Completely Different Study"
        )
        (vault / "papers" / "copycat-2020-echo.md").write_text(clone, encoding="utf-8")
        identity = load_vault_identity(vault)
        self.assertIn("copycat-2020-echo", identity["works"])  # both kept
        self.assertIn("alpha-2020-echo", identity["works"])
        kinds = [c["kind"] for c in identity["confirmations"]]
        self.assertIn("duplicate-external-id", kinds)

    def test_fuzzy_title_is_a_confirmation(self):
        vault = _tmp_vault(self)
        clone = (MINI / "papers" / "alpha-2020-echo.md").read_text(encoding="utf-8")
        clone = clone.replace("slug: alpha-2020-echo", "slug: alpha-2021-echo")
        clone = clone.replace('"10.99999/fixture.alpha2020"', '"10.99999/other.id"')
        clone = clone.replace(
            "Echo Cancellation in Alpha Systems", "Echo Cancellation in Alpha System"
        )
        (vault / "papers" / "alpha-2021-echo.md").write_text(clone, encoding="utf-8")
        identity = load_vault_identity(vault)
        fuzzy = [c for c in identity["confirmations"] if c["kind"] == "fuzzy-title"]
        self.assertTrue(fuzzy, identity["confirmations"])
        self.assertIn("alpha-2021-echo", fuzzy[0]["slugs"])

    def test_parse_failures_are_reported_not_raised(self):
        vault = _tmp_vault(self)
        (vault / "papers" / "broken-card.md").write_text(
            "no frontmatter here\n", encoding="utf-8"
        )
        identity = load_vault_identity(vault)
        self.assertTrue(
            any("broken-card" in error for error in identity["parse_errors"])
        )

    def test_slug_field_mismatch_reported(self):
        vault = _tmp_vault(self)
        text = (vault / "papers" / "beta-2021-foxtrot.md").read_text(encoding="utf-8")
        (vault / "papers" / "beta-2021-foxtrot.md").write_text(
            text.replace("slug: beta-2021-foxtrot", "slug: wrong-slug"), encoding="utf-8"
        )
        identity = load_vault_identity(vault)
        self.assertTrue(
            any("wrong-slug" in error for error in identity["parse_errors"])
        )

    def test_scalar_list_field_is_one_problem_not_characters(self):
        vault = _tmp_vault(self)
        text = (vault / "papers" / "alpha-2020-echo.md").read_text(encoding="utf-8")
        (vault / "papers" / "alpha-2020-echo.md").write_text(
            text.replace("task: [concept-echo]", "task: concept-echo"), encoding="utf-8"
        )
        identity = load_vault_identity(vault)
        self.assertEqual(identity["works"]["alpha-2020-echo"]["axes"]["task"], [])
        matches = [e for e in identity["parse_errors"] if "task expected a [list]" in e]
        self.assertEqual(len(matches), 1, identity["parse_errors"])

    def test_bad_gap_relation_reported(self):
        vault = _tmp_vault(self)
        text = (vault / "papers" / "alpha-2020-echo.md").read_text(encoding="utf-8")
        (vault / "papers" / "alpha-2020-echo.md").write_text(
            text.replace('"gap-echo-noise:supports"', '"gap-echo-noise:funds"'),
            encoding="utf-8",
        )
        identity = load_vault_identity(vault)
        self.assertTrue(
            any("bad gap entry" in error for error in identity["parse_errors"])
        )



class TestDomainPartitionReport(unittest.TestCase):
    def test_counts_roots_and_flags_unregistered_ones(self):
        identity = load_vault_identity(MINI)
        report = domain_partition_report(identity)
        self.assertEqual(report["cards_without_root"], [])
        self.assertEqual(report["roots"]["alpha-domain"]["cards"], 2)
        self.assertTrue(report["roots"]["alpha-domain"]["registered"])
        self.assertEqual(report["roots"]["alpha-domain"]["tasks"][0][0], "concept-echo")
        self.assertEqual(report["root_pairs"], {("alpha-domain", "beta-domain"): 1})  # gamma-2022-bridge
        hub = [h for h in report["shared_hubs"] if h["concept"] == "concept-shared-pattern"]
        self.assertEqual(hub[0]["domains"], {"alpha-domain": 1, "beta-domain": 1})
        self.assertEqual(domain_partition_report(identity, stopwords=("concept-shared-pattern",))["shared_hubs"], [])
        identity["works"]["alpha-2020-echo"]["axes"]["domain"].append("beta-domain")
        self.assertEqual(domain_partition_report(identity)["root_pairs"], {("alpha-domain", "beta-domain"): 2})
        identity["domains"].pop("beta-domain")
        self.assertEqual(domain_partition_report(identity)["unregistered_roots"], ["beta-domain"])


if __name__ == "__main__":
    unittest.main()
