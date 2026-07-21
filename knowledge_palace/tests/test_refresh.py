"""Refresh is explicit and cache-first,
snapshots never change without it, dry-run writes reports only — zero Vault
writes, zero network without --live."""

import hashlib
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from knowledge_palace.metadata.cache import BibliographicCache
from knowledge_palace.metadata.refresh import (
    citations_proposal,
    load_snapshots,
    read_jcr_snapshot,
    refresh_snapshots,
    scope_cards,
    weight_dryrun,
)

MINI = Path(__file__).resolve().parent / "fixtures" / "vault-mini"
OPENALEX_FIXTURE = (
    Path(__file__).resolve().parent / "fixtures" / "providers" / "openalex-work.json"
)
ALPHA_URL = "https://api.openalex.org/works/doi:10.99999/fixture.alpha2020"


def tree_digest(base):
    return [
        (p.relative_to(base).as_posix(), hashlib.sha256(p.read_bytes()).hexdigest())
        for p in sorted(base.rglob("*"))
        if p.is_file()
    ]


class RefreshCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        base = Path(self._tmp.name)
        self.vault = base / "vault"
        self.state = base / "state"
        shutil.copytree(MINI, self.vault)
        # Seed the Bibliographic Cache so a cache-only run has data for alpha.
        cache = BibliographicCache(self.state, now=lambda: "2026-07-01T00:00:00+00:00")
        cache.put(
            "openalex", ALPHA_URL, json.loads(OPENALEX_FIXTURE.read_text(encoding="utf-8"))
        )


class TestScope(RefreshCase):
    def test_scopes(self):
        self.assertEqual(len(scope_cards(self.vault, "all")), 3)
        self.assertEqual(
            [p.stem for p in scope_cards(self.vault, "alpha-2020-echo")],
            ["alpha-2020-echo"],
        )
        self.assertEqual(
            sorted(p.stem for p in scope_cards(self.vault, "domain:beta-domain")),
            ["beta-2021-foxtrot", "gamma-2022-bridge"],
        )


class TestCacheOnlyRefresh(RefreshCase):
    def test_cache_only_run_updates_hits_and_reports_misses(self):
        result = refresh_snapshots(self.vault, self.state, live=False)
        self.assertEqual(result["updated"], ["alpha-2020-echo"])
        reasons = dict(result["no_data"])
        self.assertIn("beta-2021-foxtrot", reasons)  # cache miss, not fetched
        self.assertIn("cache", reasons["beta-2021-foxtrot"])
        self.assertIn("gamma-2022-bridge", reasons)  # no DOI/arXiv id
        self.assertIn("no DOI/arXiv", reasons["gamma-2022-bridge"])
        self.assertEqual(result["errors"], [])
        snapshots = load_snapshots(self.state)
        alpha = snapshots["alpha-2020-echo"]
        self.assertAlmostEqual(alpha["citation_percentile"], 93.0)
        self.assertEqual(alpha["venue_metric_text"], "5.0 (fixture)")
        self.assertEqual(alpha["fetched_at"], "2026-07-01T00:00:00+00:00")

    def test_jcr_snapshot_attaches_by_venue(self):
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
            json.dump({"Fixture Letters": {"Echo Processing": "Q1"}}, fh)
            jcr_path = fh.name
        self.addCleanup(Path(jcr_path).unlink)
        jcr = read_jcr_snapshot(jcr_path)
        refresh_snapshots(self.vault, self.state, live=False, jcr=jcr)
        alpha = load_snapshots(self.state)["alpha-2020-echo"]
        self.assertEqual(alpha["jcr_quartiles"], {"Echo Processing": "Q1"})

    def test_snapshots_only_change_on_refresh(self):
        refresh_snapshots(self.vault, self.state, live=False)
        snapshot_file = self.state / "impact" / "snapshots.json"
        before = snapshot_file.read_bytes()
        citations_proposal(self.vault, self.state)
        weight_dryrun(self.vault, self.state, 2026)
        self.assertEqual(snapshot_file.read_bytes(), before)
        refresh_snapshots(self.vault, self.state, live=False)  # same cache, same data
        self.assertEqual(snapshot_file.read_bytes(), before)


class TestReportsAreDerivedStateOnly(RefreshCase):
    def test_citations_proposal_content(self):
        refresh_snapshots(self.vault, self.state, live=False)
        report = citations_proposal(self.vault, self.state)
        text = report.read_text(encoding="utf-8")
        self.assertIn("| alpha-2020-echo | 42 (2026-07) | 42 (2026-07-01", text)
        self.assertIn("| 0 |", text)
        self.assertIn("packaged confirmation", text)

    def test_weight_dryrun_zero_vault_writes(self):
        refresh_snapshots(self.vault, self.state, live=False)
        before = tree_digest(self.vault)
        report, covered, agreements = weight_dryrun(self.vault, self.state, 2026)
        self.assertEqual(tree_digest(self.vault), before)
        self.assertEqual(covered, 1)  # only alpha has a snapshot
        text = report.read_text(encoding="utf-8")
        self.assertIn("| alpha-2020-echo | medium |", text)
        self.assertIn("Echo Processing: high", text)  # percentile 93 → high
        self.assertIn("(no snapshot — run refresh)", text)  # beta/gamma rows
        self.assertIn("the weight-migration gate", text)

    def test_everything_lands_under_state(self):
        refresh_snapshots(self.vault, self.state, live=False)
        citations_proposal(self.vault, self.state)
        weight_dryrun(self.vault, self.state, 2026)
        written = {p.relative_to(self.state).parts[0] for p in self.state.rglob("*") if p.is_file()}
        self.assertEqual(written, {"bibliographic-cache", "impact"})


if __name__ == "__main__":
    unittest.main()
