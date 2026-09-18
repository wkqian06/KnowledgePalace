"""The 10/15/30 coarse-to-fine pipeline and the
IdeaAssessment schema semantics."""

import unittest
from pathlib import Path

from knowledge_palace.graph.builder import build_payload
from knowledge_palace.interaction.novelty import (
    CLAIM_CAP,
    CORRIDOR_CAP,
    NOVELTY_DIMENSIONS,
    WORK_CAP,
    new_assessment,
    new_profile,
    novelty_pipeline,
    validate_assessment,
    validate_profile,
)
from knowledge_palace.tests.test_semantic_corridors import synthetic_dense_payload

MINI = Path(__file__).resolve().parent / "fixtures" / "vault-mini"


def dense_payload_with_claims(claims_per_work=3):
    payload = synthetic_dense_payload(concepts=30)
    for work_id in [n for n, node in payload["nodes"].items() if node["kind"] == "work"]:
        for index in range(claims_per_work):
            claim_id = "claim:%s#C%d" % (work_id.split(":", 1)[1], index + 1)
            payload["nodes"][claim_id] = {
                "id": claim_id, "kind": "claim", "label": claim_id,
            }
            payload["parents"][claim_id] = [work_id]
            payload["edges"].append(
                {"id": "%s|claims|%s" % (work_id, claim_id),
                 "kind": "claims", "from": work_id, "to": claim_id}
            )
    return payload


class TestProfile(unittest.TestCase):
    def test_valid_subset(self):
        profile = new_profile("proj-x", ["mechanism", "application-transfer"])
        self.assertEqual(validate_profile(profile), [])

    def test_empty_unknown_and_duplicate_dimensions_rejected(self):
        self.assertTrue(validate_profile(new_profile("p", [])))
        self.assertTrue(validate_profile(new_profile("p", ["astrology"])))
        self.assertTrue(validate_profile(new_profile("p", ["theory", "theory"])))
        self.assertTrue(validate_profile(new_profile("", ["theory"])))

    def test_all_nine_dimensions_selectable(self):
        self.assertEqual(len(NOVELTY_DIMENSIONS), 9)
        self.assertEqual(
            validate_profile(new_profile("p", list(NOVELTY_DIMENSIONS))), []
        )


class TestPipelineVaultMini(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.payload = build_payload(MINI)
        cls.result = novelty_pipeline(cls.payload, "echo cancellation shared pattern")

    def test_deterministic(self):
        again = novelty_pipeline(self.payload, "echo cancellation shared pattern")
        self.assertEqual(self.result, again)

    def test_id_only_output(self):
        for work in self.result["works"]["returned"]:
            self.assertEqual(sorted(work), ["canonical_ref", "node_id", "why"])
        for claim_id in self.result["claims"]["returned"]:
            self.assertTrue(claim_id.startswith("claim:"))
        self.assertNotIn("Fixture paper", str(self.result))  # no card text

    def test_drills_from_works_to_their_claims(self):
        work_ids = {w["node_id"] for w in self.result["works"]["returned"]}
        self.assertIn("work:alpha-2020-echo", work_ids)
        self.assertTrue(
            any(c.startswith("claim:alpha-2020-echo#")
                for c in self.result["claims"]["returned"])
        )

    def test_honest_counts_when_nothing_truncates(self):
        for stage in ("corridors", "works", "claims"):
            block = self.result[stage]
            self.assertEqual(block["total"], len(block["returned"]))
            self.assertFalse(block["truncated"])


class TestPipelineCaps(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Terms hit both domains (w-a-00 / w-b-00) so corridors engage;
        # a single-domain idea correctly yields zero corridors.
        cls.result = novelty_pipeline(dense_payload_with_claims(), "shared w-a-00 w-b-00")

    def test_corridor_cap_10(self):
        block = self.result["corridors"]
        self.assertEqual(len(block["returned"]), CORRIDOR_CAP)
        self.assertTrue(block["truncated"])
        self.assertGreater(block["total"], CORRIDOR_CAP)

    def test_work_cap_15(self):
        block = self.result["works"]
        self.assertEqual(len(block["returned"]), WORK_CAP)
        self.assertTrue(block["truncated"])
        self.assertGreater(block["total"], WORK_CAP)

    def test_claim_cap_30(self):
        block = self.result["claims"]
        self.assertEqual(len(block["returned"]), CLAIM_CAP)
        self.assertTrue(block["truncated"])
        self.assertGreater(block["total"], CLAIM_CAP)


def tri_domain_payload():
    """Three domains, one transfer touching all three (the dedup case)."""
    nodes, parents, edges = {}, {}, []
    for side in ("a", "b", "c"):
        domain_id = "domain:d-" + side
        work_id = "work:w-tri-" + side
        nodes[domain_id] = {"id": domain_id, "kind": "domain", "label": side}
        nodes[work_id] = {"id": work_id, "kind": "work", "label": "tri work " + side}
        parents[domain_id] = []
        parents[work_id] = [domain_id]
        edges.append(
            {"id": "transfer:t-all|targets|%s" % work_id,
             "kind": "targets", "from": "transfer:t-all", "to": work_id}
        )
    nodes["transfer:t-all"] = {
        "id": "transfer:t-all", "kind": "transfer", "label": "t-all",
    }
    parents["transfer:t-all"] = []
    return {"nodes": nodes, "parents": parents, "edges": edges,
            "hierarchies": [{"id": "h", "label": "h", "levels": []}]}


class TestCorridorDedup(unittest.TestCase):
    def test_transfer_spanning_three_domains_counts_once(self):
        result = novelty_pipeline(tri_domain_payload(), "tri")
        block = result["corridors"]
        self.assertEqual(block["total"], 1)  # not 3 (one per domain pair)
        self.assertEqual(len(block["returned"]), 1)
        self.assertFalse(block["truncated"])
        self.assertEqual(block["returned"][0]["via"], "transfer:t-all")


class TestAssessment(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.payload = build_payload(MINI)

    def _valid(self, **overrides):
        base = dict(
            profile=new_profile("proj-x", ["mechanism", "method"]),
            minimal_experiment="ablate the echo canceller on fixture data",
            falsifiers=["no gain over the alpha-2020 baseline kills it"],
            supporting=["claim:alpha-2020-echo#C1"],
            opposing=["claim:beta-2021-foxtrot#C1"],
            unknown=["long-horizon drift behaviour"],
            closest_prior_work=["work:alpha-2020-echo", "project-source:doi:10.99999/x"],
            alternative_hypotheses=["the gain is a data artefact"],
            novelty={"mechanism": "no Vault work couples echo and foxtrot this way"},
            possible_novelty=["graph synthesis: gap-echo-noise x transfer-echo-to-gamma"],
        )
        base.update(overrides)
        return new_assessment(**base)

    def test_valid_assessment_passes_with_payload_resolution(self):
        self.assertEqual(validate_assessment(self._valid(), self.payload), [])

    def test_falsifiers_and_minimal_experiment_required(self):
        self.assertTrue(validate_assessment(self._valid(falsifiers=[]), self.payload))
        self.assertTrue(
            validate_assessment(self._valid(minimal_experiment=""), self.payload)
        )

    def test_refs_must_be_id_shaped_and_resolve(self):
        errors = validate_assessment(
            self._valid(supporting=["the alpha paper says so"]), self.payload
        )
        self.assertTrue(any("not an index id" in e for e in errors))
        errors = validate_assessment(
            self._valid(supporting=["claim:no-such-work#C9"]), self.payload
        )
        self.assertTrue(any("not in the index" in e for e in errors))

    def test_novelty_only_on_profile_selected_dimensions(self):
        errors = validate_assessment(
            self._valid(novelty={"theory": "brand new theory"}), self.payload
        )
        self.assertTrue(any("did not select" in e for e in errors))

    def test_external_statements_require_confirmed_optin(self):
        external = {"statements": ["not found anywhere, globally novel"]}
        errors = validate_assessment(self._valid(external=external), self.payload)
        self.assertTrue(any("confirmed opt-in" in e for e in errors))
        unconfirmed = {
            "request": {"session_id": "s", "scope": "openalex",
                        "date": "2026-07-14", "hops": 1,
                        "max_candidates": 20, "user_confirmed": False},
            "statements": [],
        }
        errors = validate_assessment(self._valid(external=unconfirmed), self.payload)
        self.assertTrue(any("confirmed opt-in" in e for e in errors))


if __name__ == "__main__":
    unittest.main()
