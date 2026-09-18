"""The bounded engine over a synthetic citation
graph — A→B→C with C frozen, Vault-Hit edges, exact budget stops, frontier
rules, reviewer batch flow."""

import unittest
from pathlib import Path

from knowledge_palace.expansion.engine import (
    EXPLORATORY_CAP,
    apply_decisions,
    execute,
    expand_next,
    review_batch,
)
from knowledge_palace.expansion.run import ExpansionRun
from knowledge_palace.graph.identity import load_vault_identity
from knowledge_palace.metadata.providers import ProviderError

MINI = Path(__file__).resolve().parent / "fixtures" / "vault-mini"
ALPHA_DOI = "10.99999/fixture.alpha2020"
BETA_ARXIV = "2101.00001"


class StubGraphProvider:
    """references/cited_by served from a synthetic citation graph."""

    def __init__(self, graph, fail_references=(), resolve_map=None):
        self.graph = graph  # key → {"references": [record...], "cited_by": [...]}
        self.fail_references = set(fail_references)
        self.calls = []
        if resolve_map is not None:
            self.resolve_map = resolve_map
            self.resolve = self._resolve

    def _resolve(self, ref):
        self.calls.append(("resolve", ref.get("openalex")))
        record = self.resolve_map.get(ref.get("openalex"))
        if record is None:
            raise ProviderError("stub", "resolve", "unknown %r" % ref)
        return record

    def _key(self, ids):
        return ids.get("doi") or ids.get("arxiv")

    def references(self, ids, **_):
        key = self._key(ids)
        self.calls.append(("references", key))
        if key in self.fail_references:
            raise ProviderError("stub", "references", "synthetic outage")
        items = self.graph.get(key, {}).get("references", [])
        return {"count": len(items), "items": items}

    def cited_by(self, ids, limit=50):
        key = self._key(ids)
        self.calls.append(("cited_by", key))
        items = self.graph.get(key, {}).get("cited_by", [])
        return {"count": len(items), "items": items}


def rec(doi=None, arxiv=None, title=None):
    ids = {}
    if doi:
        ids["doi"] = doi
    if arxiv:
        ids["arxiv"] = arxiv
    return {"ids": ids, "title": title or (doi or arxiv or "untitled"), "year": 2024}


class EngineCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.identity = load_vault_identity(MINI)

    def make_run(self, seeds=("alpha-2020-echo",), depth=2, max_new=50, run_id="run-t"):
        return ExpansionRun(run_id, "scope-test", list(seeds), depth=depth, max_new=max_new)


class TestTraversal(EngineCase):
    def test_a_to_hit_to_c_with_boundary_frozen(self):
        graph = {
            ALPHA_DOI: {
                "references": [rec("10.9/b"), rec("10.9/d"), rec(arxiv=BETA_ARXIV)],
                "cited_by": [rec("10.9/c1")],
            },
            BETA_ARXIV: {"references": [rec("10.9/c2")], "cited_by": []},
        }
        provider = StubGraphProvider(graph)
        run = self.make_run()
        reason = execute(run, provider, self.identity)
        self.assertEqual(reason, "frontier_exhausted")
        self.assertEqual(
            sorted(run.new_keys),
            ["doi:10.9/b", "doi:10.9/c1", "doi:10.9/c2", "doi:10.9/d"],
        )
        # beta was a Vault Hit found at depth 1 and expanded (depth < 2)…
        self.assertIn(
            {"slug": "beta-2021-foxtrot", "via": "alpha-2020-echo",
             "direction": "references", "depth": 1},
            run.vault_hits,
        )
        self.assertIn("beta-2021-foxtrot", run.expanded)
        # …its C (depth 2) is recorded but frozen: nothing expanded at depth 2.
        c2 = run.pool.get("doi:10.9/c2")
        self.assertEqual(c2["occurrences"][0]["depth"], 2)
        self.assertEqual(sorted(run.expanded), ["alpha-2020-echo", "beta-2021-foxtrot"])

    def test_shared_discovery_is_one_candidate_two_occurrences(self):
        graph = {
            ALPHA_DOI: {"references": [rec("10.9/b")], "cited_by": []},
            BETA_ARXIV: {"references": [rec("10.9/b")], "cited_by": []},
        }
        run = self.make_run(seeds=("alpha-2020-echo", "beta-2021-foxtrot"))
        execute(run, StubGraphProvider(graph), self.identity)
        self.assertEqual(run.new_keys, ["doi:10.9/b"])  # counted once
        entry = run.pool.get("doi:10.9/b")
        self.assertEqual(len(entry["occurrences"]), 2)
        self.assertEqual(
            sorted(o["via"] for o in entry["occurrences"]),
            ["alpha-2020-echo", "beta-2021-foxtrot"],
        )

    def test_vault_hit_records_edge_without_reingest(self):
        # Mutual citation: the hit may expand (rule 5), but a hit pointing
        # back at a seed/expanded work is never requeued, and neither side
        # ever becomes a candidate.
        graph = {
            BETA_ARXIV: {"references": [rec(doi=ALPHA_DOI)], "cited_by": []},
            ALPHA_DOI: {"references": [rec(arxiv=BETA_ARXIV)], "cited_by": []},
        }
        run = self.make_run(seeds=("beta-2021-foxtrot",))
        execute(run, StubGraphProvider(graph), self.identity)
        self.assertEqual(run.new_keys, [])  # hits are never candidates
        slugs = {hit["slug"] for hit in run.vault_hits}
        self.assertEqual(slugs, {"alpha-2020-echo", "beta-2021-foxtrot"})
        self.assertEqual(  # each work expanded exactly once — no requeue loop
            sorted(run.expanded), ["alpha-2020-echo", "beta-2021-foxtrot"]
        )


    def test_provider_id_only_references_resolve_before_hit_matching(self):
        # OpenAlex reference lists carry only openalex ids; vault cards carry
        # DOIs/arXiv ids. Without resolution a library paper looks new.
        graph = {ALPHA_DOI: {"references": [{"ids": {"openalex": "W-beta"}},
                                            {"ids": {"openalex": "W-new"}},
                                            {"ids": {"openalex": "W-gone"}}],
                             "cited_by": []}}
        provider = StubGraphProvider(graph, resolve_map={
            "W-beta": rec(arxiv=BETA_ARXIV, title="Beta"),
            "W-new": rec(doi="10.9/new", title="A titled candidate"),
        })
        run = self.make_run(depth=1)
        execute(run, provider, self.identity)
        self.assertEqual({hit["slug"] for hit in run.vault_hits}, {"beta-2021-foxtrot"})
        # An unresolvable id stays a provider-id-only candidate, with a warning.
        self.assertEqual(run.new_keys, ["doi:10.9/new", "openalex:w-gone"])
        self.assertEqual(run.pool.get("doi:10.9/new")["title"], "A titled candidate")
        self.assertTrue(any("W-gone" in warning for warning in run.warnings))


class TestBudgetAndFrontier(EngineCase):
    def test_budget_stops_exactly_at_cap(self):
        many = [rec("10.9/n%02d" % i) for i in range(10)]
        graph = {ALPHA_DOI: {"references": many, "cited_by": []}}
        run = self.make_run(max_new=3)
        reason = execute(run, StubGraphProvider(graph), self.identity)
        self.assertEqual(reason, "budget_reached")
        self.assertEqual(run.budget_used(), 3)

    def test_frontier_exhaustion_below_cap(self):
        graph = {ALPHA_DOI: {"references": [rec("10.9/only")], "cited_by": []}}
        run = self.make_run(max_new=50)
        reason = execute(run, StubGraphProvider(graph), self.identity)
        self.assertEqual(reason, "frontier_exhausted")
        self.assertEqual(run.budget_used(), 1)

    def test_metadata_only_candidates_never_join_the_frontier(self):
        graph = {
            ALPHA_DOI: {"references": [rec("10.9/b"), rec("10.9/c")], "cited_by": []}
        }
        run = self.make_run()
        execute(run, StubGraphProvider(graph), self.identity)
        vault_slugs = set(self.identity["works"])
        self.assertTrue(set(run.expanded) <= vault_slugs | set(run.seeds))

    def test_title_only_neighbor_is_unverified_and_unbudgeted(self):
        graph = {
            ALPHA_DOI: {
                "references": [{"ids": {}, "title": "Mystery Preprint", "year": None}],
                "cited_by": [],
            }
        }
        run = self.make_run()
        execute(run, StubGraphProvider(graph), self.identity)
        self.assertEqual(run.budget_used(), 0)
        title_keys = [k for k in run.pool.keys() if k.startswith("title:")]
        self.assertEqual(len(title_keys), 1)
        self.assertFalse(run.pool.get(title_keys[0])["verified"])

    def test_partial_provider_failure_becomes_a_warning(self):
        graph = {ALPHA_DOI: {"references": [], "cited_by": [rec("10.9/c1")]}}
        provider = StubGraphProvider(graph, fail_references={ALPHA_DOI})
        run = self.make_run()
        reason = execute(run, provider, self.identity)
        self.assertEqual(reason, "frontier_exhausted")
        self.assertEqual(run.new_keys, ["doi:10.9/c1"])  # cited_by still worked
        self.assertTrue(any("synthetic outage" in w for w in run.warnings))


class TestReviewerFlow(EngineCase):
    def make_reviewed_run(self):
        graph = {
            ALPHA_DOI: {
                "references": [rec("10.9/b"), rec("10.9/d"), rec("10.9/e")],
                "cited_by": [],
            }
        }
        run = self.make_run()
        execute(run, StubGraphProvider(graph), self.identity)
        return run

    def test_batch_payload_shape(self):
        run = self.make_reviewed_run()
        batch = review_batch(run)
        self.assertEqual(batch["package_kind"], "expansion-review-batch")
        self.assertEqual(batch["scope"], "scope-test")
        self.assertEqual(batch["budget"]["used"], 3)
        self.assertEqual(batch["exploratory_cap"], EXPLORATORY_CAP)
        self.assertEqual(len(batch["candidates"]), 3)
        for candidate in batch["candidates"]:
            self.assertIsNone(candidate["decision"])  # undecided before review
            self.assertIn("occurrences", candidate)

    def test_decisions_confined_to_the_reviewed_batch(self):
        run = self.make_reviewed_run()
        run.pool.upsert({"ids": {"doi": "10.9/outsider"}}, "other-run", "x", "references", 1)
        with self.assertRaises(ValueError) as ctx:
            apply_decisions(
                run, [{"key": "doi:10.9/outsider", "decision": "selected", "reason": "r"}]
            )
        self.assertIn("outside the reviewed batch", str(ctx.exception))

    def test_exploratory_cap_cannot_stack_across_calls(self):
        run = self.make_reviewed_run()
        keys = run.new_keys
        apply_decisions(
            run,
            [
                {"key": keys[0], "decision": "selected", "reason": "r", "exploratory": True},
                {"key": keys[1], "decision": "selected", "reason": "r", "exploratory": True},
            ],
        )
        with self.assertRaises(ValueError) as ctx:
            apply_decisions(
                run,
                [{"key": keys[2], "decision": "selected", "reason": "r", "exploratory": True}],
            )
        self.assertIn("exceed the cap", str(ctx.exception))
        # Deferred-exploratory does not consume the cap; re-deciding a key
        # counts under its newest verdict.
        apply_decisions(
            run,
            [{"key": keys[2], "decision": "deferred", "reason": "r", "exploratory": True}],
        )
        apply_decisions(
            run,
            [{"key": keys[0], "decision": "rejected", "reason": "changed", "exploratory": False}],
        )
        apply_decisions(
            run,
            [{"key": keys[2], "decision": "selected", "reason": "r", "exploratory": True}],
        )

    def test_apply_decisions_enforces_exploratory_cap_and_records_scope(self):
        run = self.make_reviewed_run()
        too_many = [
            {"key": key, "decision": "selected", "reason": "r", "exploratory": True}
            for key in run.new_keys
        ]
        with self.assertRaises(ValueError):
            apply_decisions(run, too_many)
        decisions = [
            {"key": run.new_keys[0], "decision": "selected", "reason": "core"},
            {"key": run.new_keys[1], "decision": "deferred", "reason": "later"},
            {"key": run.new_keys[2], "decision": "rejected", "reason": "off-scope",
             "exploratory": False},
        ]
        apply_decisions(run, decisions)
        batch = review_batch(run)
        verdicts = {c["key"]: c["decision"]["decision"] for c in batch["candidates"]}
        self.assertEqual(
            sorted(verdicts.values()), ["deferred", "rejected", "selected"]
        )
        self.assertEqual(
            run.pool.decision_for(run.new_keys[0], "another-scope"), None
        )


if __name__ == "__main__":
    unittest.main()
