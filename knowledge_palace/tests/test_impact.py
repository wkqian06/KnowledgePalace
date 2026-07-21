"""Contextual classifier — P90/P50 boundaries, JCR
coarse fallback, side-by-side multi-category, unknown stays unknown, medium
floor, preprint citations-only, and the recorded Evaluation Context."""

import unittest

from knowledge_palace.metadata.impact import build_snapshot, classify, classify_all


def snap(**overrides):
    record = {
        "provider": "openalex",
        "fetched_at": "2026-07-13T00:00:00+00:00",
        "title": "T",
        "year": 2020,
        "venue": "Fixture Letters",
        "citations": 42,
        "citation_percentile": None,
        "categories": ["Echo Processing"],
        "is_preprint": False,
        "peer_reviewed": None,
    }
    jcr = overrides.pop("jcr", None)
    record.update(overrides)
    return build_snapshot(record, work_slug="w", jcr_quartiles=jcr)


class TestPercentileBands(unittest.TestCase):
    def test_boundaries(self):
        cases = {95.0: "high", 90.0: "high", 89.9: "medium", 50.0: "medium", 49.9: "low", 0.0: "low"}
        for percentile, expected in cases.items():
            verdict = classify(snap(citation_percentile=percentile), "Echo Processing", 2026)
            self.assertEqual(verdict["band"], expected, percentile)
            self.assertEqual(verdict["channel"], "citations")
            self.assertFalse(verdict["coarse_fallback"])

    def test_context_is_always_recorded(self):
        verdict = classify(snap(citation_percentile=95.0), "Echo Processing", 2026)
        self.assertEqual(
            verdict["context"], {"category": "Echo Processing", "evaluation_year": 2026}
        )

    def test_same_work_different_context_different_band(self):
        snapshot = snap(
            categories=["Echo Processing", "Acoustics"],
            jcr={"Echo Processing": "Q1", "Acoustics": "Q4"},
        )
        echo = classify(snapshot, "Echo Processing", 2026)
        acoustics = classify(snapshot, "Acoustics", 2026)
        self.assertEqual(echo["band"], "high")
        self.assertEqual(acoustics["band"], "low")
        self.assertNotEqual(echo["context"], acoustics["context"])


class TestJcrFallbackAndChannels(unittest.TestCase):
    def test_quartiles_map_coarse_and_flagged(self):
        for quartile, expected in (("Q1", "high"), ("Q2", "medium"), ("Q3", "low"), ("Q4", "low")):
            verdict = classify(snap(jcr={"Echo Processing": quartile}), "Echo Processing", 2026)
            self.assertEqual(verdict["band"], expected, quartile)
            self.assertTrue(verdict["coarse_fallback"], quartile)
            self.assertIn("coarse", verdict["basis"])

    def test_higher_known_channel_wins(self):
        verdict = classify(
            snap(citation_percentile=95.0, jcr={"Echo Processing": "Q2"}),
            "Echo Processing",
            2026,
        )
        self.assertEqual(verdict["band"], "high")
        self.assertEqual(verdict["channel"], "citations")
        self.assertFalse(verdict["coarse_fallback"])

    def test_band_tie_between_channels_is_not_marked_coarse(self):
        verdict = classify(
            snap(citation_percentile=60.0, jcr={"Echo Processing": "Q2"}),
            "Echo Processing",
            2026,
        )
        self.assertEqual(verdict["band"], "medium")
        self.assertEqual(verdict["channel"], "citations")
        self.assertFalse(verdict["coarse_fallback"])

    def test_unknown_stays_unknown_despite_citation_count(self):
        verdict = classify(snap(citations=9999), "Echo Processing", 2026)
        self.assertEqual(verdict["band"], "unknown")
        self.assertEqual(verdict["channel"], "none")


class TestPreprintAndFloor(unittest.TestCase):
    def test_preprint_excludes_venue_channel(self):
        verdict = classify(
            snap(is_preprint=True, jcr={"Echo Processing": "Q1"}, citation_percentile=60.0),
            "Echo Processing",
            2026,
        )
        self.assertEqual(verdict["band"], "medium")
        self.assertIn("excluded(preprint)", verdict["basis"])

    def test_preprint_with_no_percentile_is_unknown(self):
        verdict = classify(
            snap(is_preprint=True, jcr={"Echo Processing": "Q1"}), "Echo Processing", 2026
        )
        self.assertEqual(verdict["band"], "unknown")

    def test_recent_peer_reviewed_medium_floor(self):
        verdict = classify(
            snap(peer_reviewed=True, year=2025, citation_percentile=30.0),
            "Echo Processing",
            2026,
        )
        self.assertEqual(verdict["band"], "medium")
        self.assertEqual(verdict["channel"], "floor")

    def test_floor_not_applied_when_old_or_preprint(self):
        old = classify(
            snap(peer_reviewed=True, year=2020, citation_percentile=30.0),
            "Echo Processing",
            2026,
        )
        self.assertEqual(old["band"], "low")
        preprint = classify(
            snap(is_preprint=True, peer_reviewed=True, year=2025), "Echo Processing", 2026
        )
        self.assertEqual(preprint["band"], "unknown")


class TestSideBySide(unittest.TestCase):
    def test_multi_category_never_max_picked(self):
        snapshot = snap(
            categories=["Echo Processing", "Acoustics"],
            jcr={"Echo Processing": "Q1"},
        )
        verdicts = classify_all(snapshot, 2026)
        self.assertEqual(sorted(verdicts), ["Acoustics", "Echo Processing"])
        self.assertEqual(verdicts["Echo Processing"]["band"], "high")
        self.assertEqual(verdicts["Acoustics"]["band"], "unknown")
        self.assertNotIn("band", snapshot)  # snapshot itself stores NO global band

    def test_uncategorized_bucket(self):
        verdicts = classify_all(snap(categories=[]), 2026)
        self.assertEqual(list(verdicts), ["(uncategorized)"])


if __name__ == "__main__":
    unittest.main()
