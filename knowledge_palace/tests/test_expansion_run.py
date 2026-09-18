"""Idempotent checkpoint/resume, Derived-State-only
writes, deletability, and the template-conforming compact record."""

import shutil
import tempfile
import unittest
from pathlib import Path

from knowledge_palace.expansion.engine import apply_decisions, execute, expand_next
from knowledge_palace.expansion.record import build_record
from knowledge_palace.expansion.run import ExpansionRun
from knowledge_palace.graph.builder import vault_fingerprint
from knowledge_palace.graph.identity import load_vault_identity
from knowledge_palace.tests.test_expansion_engine import StubGraphProvider, rec

MINI = Path(__file__).resolve().parent / "fixtures" / "vault-mini"
ALPHA_DOI = "10.99999/fixture.alpha2020"
BETA_ARXIV = "2101.00001"


GRAPH = {
    ALPHA_DOI: {
        "references": [rec("10.9/b"), rec(arxiv=BETA_ARXIV)],
        "cited_by": [rec("10.9/c1")],
    },
    BETA_ARXIV: {"references": [rec("10.9/c2")], "cited_by": []},
}


class RunCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.identity = load_vault_identity(MINI)

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.state = Path(self._tmp.name) / "state"
        self.state.mkdir()


class TestValidation(RunCase):
    def test_constructor_bounds(self):
        for bad in (
            dict(depth=3),
            dict(depth=0),
            dict(max_new=51),
            dict(max_new=0),
        ):
            with self.assertRaises(ValueError):
                ExpansionRun("r", "s", ["seed"], **bad)
        with self.assertRaises(ValueError):
            ExpansionRun("r", "s", [])
        with self.assertRaises(ValueError):
            ExpansionRun("r", "s", ["seed"]).stop("bored")


class TestCheckpointResume(RunCase):
    def test_interrupt_resume_no_duplicates_no_losses(self):
        provider = StubGraphProvider(GRAPH)
        run = ExpansionRun("run-ckpt", "scope-test", ["alpha-2020-echo"])
        expand_next(run, provider, self.identity)  # expand alpha only
        apply_decisions(run, [{"key": "doi:10.9/b", "decision": "selected", "reason": "core"}])
        run.checkpoint(self.state)

        resumed = ExpansionRun.resume(self.state, "run-ckpt")
        self.assertEqual(resumed.new_keys, run.new_keys)
        self.assertEqual(
            resumed.pool.decision_for("doi:10.9/b", "scope-test")["decision"], "selected"
        )
        reason = execute(resumed, provider, self.identity, state_dir=self.state)
        self.assertEqual(reason, "frontier_exhausted")

        final = ExpansionRun.resume(self.state, "run-ckpt")
        entry = final.pool.get("doi:10.9/b")
        self.assertEqual(len(entry["occurrences"]), 1)  # no duplicate on resume
        self.assertEqual(
            sorted(final.new_keys), ["doi:10.9/b", "doi:10.9/c1", "doi:10.9/c2"]
        )
        self.assertEqual(
            final.pool.decision_for("doi:10.9/b", "scope-test")["decision"], "selected"
        )

    def test_writes_confined_to_state_expansion(self):
        run = ExpansionRun("run-w", "scope-test", ["alpha-2020-echo"])
        execute(run, StubGraphProvider(GRAPH), self.identity, state_dir=self.state)
        top_level = {p.relative_to(self.state).parts[0] for p in self.state.rglob("*")}
        self.assertEqual(top_level, {"expansion"})

    def test_checkpoints_are_deletable_derived_state(self):
        run = ExpansionRun("run-d", "scope-test", ["alpha-2020-echo"])
        execute(run, StubGraphProvider(GRAPH), self.identity, state_dir=self.state)
        shutil.rmtree(self.state / "expansion")
        fresh = ExpansionRun("run-d2", "scope-test", ["alpha-2020-echo"])
        reason = execute(fresh, StubGraphProvider(GRAPH), self.identity)
        self.assertEqual(reason, "frontier_exhausted")  # nothing depended on them

    def test_vault_untouched_by_a_full_run(self):
        with tempfile.TemporaryDirectory() as td:
            vault = Path(td) / "vault"
            shutil.copytree(MINI, vault)
            identity = load_vault_identity(vault)
            before = vault_fingerprint(vault)
            run = ExpansionRun("run-v", "scope-test", ["alpha-2020-echo"])
            execute(run, StubGraphProvider(GRAPH), identity, state_dir=self.state)
            build_record(run, started="2026-07-14")
            self.assertEqual(vault_fingerprint(vault), before)


class TestRecord(RunCase):
    def test_record_conforms_to_template_shape(self):
        run = ExpansionRun("run-rec", "scope-test", ["alpha-2020-echo"])
        execute(run, StubGraphProvider(GRAPH), self.identity)
        apply_decisions(
            run,
            [{"key": "doi:10.9/b", "decision": "selected", "reason": "core",
              "exploratory": True}],
        )
        text = build_record(run, started="2026-07-14")
        for needle in (
            "run: run-rec",
            "scope: scope-test",
            "seeds: [alpha-2020-echo]",
            "depth: 2",
            "max_new: 50",
            "stop_reason: frontier_exhausted",
            "## Candidates (stable identities)",
            "## Discovery occurrences",
            "## Vault hits",
            "| doi:10.9/b |",
            "selected (exploratory)",
            "| beta-2021-foxtrot | alpha-2020-echo | references | 1 |",
        ):
            self.assertIn(needle, text)
        self.assertIn("| doi:10.9/c1 | alpha-2020-echo | cited_by | 1 |", text)
        self.assertNotIn("abstract", text.lower())  # compact by contract

    def test_record_escapes_pipes_and_newlines_in_free_text(self):
        run = ExpansionRun("run-esc", "scope-test", ["alpha-2020-echo"])
        graph = {
            ALPHA_DOI: {
                "references": [
                    {"ids": {"doi": "10.9/pipe"}, "title": "Tables | And\nNewlines", "year": 2024}
                ],
                "cited_by": [],
            }
        }
        execute(run, StubGraphProvider(graph), self.identity)
        apply_decisions(
            run,
            [{"key": "doi:10.9/pipe", "decision": "rejected", "reason": "bad | reason\nhere"}],
        )
        text = build_record(run, started="2026-07-14")
        row = next(line for line in text.splitlines() if "10.9/pipe" in line)
        self.assertEqual(row.count(" | "), 5)  # still one well-formed 6-cell row
        self.assertIn("Tables \\| And Newlines", row)
        self.assertIn("bad \\| reason here", row)


if __name__ == "__main__":
    unittest.main()
