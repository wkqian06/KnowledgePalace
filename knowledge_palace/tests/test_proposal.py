"""ExpansionProposal bounds and the expansion handoff;
rejection changes nothing."""

import unittest
from pathlib import Path

from knowledge_palace.expansion.run import ExpansionRun
from knowledge_palace.graph.identity import load_vault_identity
from knowledge_palace.interaction.proposal import (
    materialize,
    new_proposal,
    validate_proposal,
)

MINI = Path(__file__).resolve().parent / "fixtures" / "vault-mini"


def proposal(**overrides):
    base = new_proposal(
        "prop-1",
        "sess-1",
        "scope-echo",
        holes=["foxtrot drift unexplained"],
        seeds=["alpha-2020-echo"],
        depth=2,
        max_new=25,
        rationale="hole needs foreign-domain literature",
    )
    base.update(overrides)
    return base


class TestValidation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.identity = load_vault_identity(MINI)

    def test_valid_proposal_is_confirmable(self):
        self.assertEqual(validate_proposal(proposal(), self.identity), [])

    def test_bounds_and_required_fields(self):
        cases = {
            "depth": ({"depth": 3}, "depth must be"),
            "budget": ({"max_new": 51}, "max_new must be"),
            "holes": ({"holes": []}, "must name the coverage holes"),
            "targets": ({"seeds": [], "queries": []}, "needs seeds and/or queries"),
            "scope": ({"scope": ""}, "missing scope"),
        }
        for name, (overrides, needle) in cases.items():
            errors = validate_proposal(proposal(**overrides))
            self.assertTrue(any(needle in e for e in errors), name)

    def test_seeds_must_be_vault_works(self):
        errors = validate_proposal(proposal(seeds=["ghost-2020"]), self.identity)
        self.assertTrue(any("not a Vault work" in e for e in errors))


class TestMaterialization(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.identity = load_vault_identity(MINI)

    def test_confirmed_proposal_becomes_a_valid_run(self):
        run = materialize(proposal(), "run-from-prop-1", self.identity)
        self.assertIsInstance(run, ExpansionRun)
        self.assertEqual(run.scope, "scope-echo")
        self.assertEqual(run.seeds, ["alpha-2020-echo"])
        self.assertEqual(run.max_new, 25)
        self.assertEqual(run.depth, 2)

    def test_invalid_proposal_raises(self):
        with self.assertRaises(ValueError):
            materialize(proposal(depth=3), "run-x")

    def test_query_only_proposal_needs_seed_resolution_first(self):
        query_only = proposal(seeds=[], queries=["foxtrot drift review"])
        self.assertEqual(validate_proposal(query_only), [])
        with self.assertRaises(ValueError) as ctx:
            materialize(query_only, "run-q")
        self.assertIn("orchestrator territory", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
