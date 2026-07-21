"""Session lifecycle, idempotent checkpoint/resume,
the resume-after-expansion path, explicit mode escalation, deletability."""

import hashlib
import shutil
import tempfile
import unittest
from pathlib import Path

from knowledge_palace.expansion.engine import execute
from knowledge_palace.graph.identity import load_vault_identity
from knowledge_palace.interaction.coverage import new_report, new_subquestion
from knowledge_palace.interaction.proposal import materialize, new_proposal
from knowledge_palace.interaction.session import InteractionSession
from knowledge_palace.tests.test_expansion_engine import StubGraphProvider, rec

MINI = Path(__file__).resolve().parent / "fixtures" / "vault-mini"
ALPHA_DOI = "10.99999/fixture.alpha2020"

COVERED = new_subquestion("echo?", "covered", ["claim:alpha-2020-echo#C1"])
HOLE = new_subquestion("drift?", "hole")


def tree_paths(base):
    return sorted(p.relative_to(base).as_posix() for p in Path(base).rglob("*") if p.is_file())


class SessionCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.state = Path(self._tmp.name) / "state"
        self.state.mkdir()


class TestLifecycle(SessionCase):
    def test_creation_and_validation(self):
        session = InteractionSession("s1", "what about echo?")
        self.assertEqual(session.mode, "vault")
        self.assertEqual(session.history[0]["event"], "created")
        with self.assertRaises(ValueError):
            InteractionSession("", "q")
        with self.assertRaises(ValueError):
            InteractionSession("s2", "q", mode="telepathy")

    def test_coverage_is_validated_on_attach(self):
        session = InteractionSession("s1", "q")
        with self.assertRaises(ValueError):
            session.set_coverage(new_report("sufficient", [HOLE]))
        session.set_coverage(new_report("partial", [COVERED, HOLE]))
        self.assertEqual(session.coverage["verdict"], "partial")

    def test_mode_escalation_is_an_explicit_user_decision(self):
        session = InteractionSession("s1", "q")
        with self.assertRaises(ValueError):
            session.escalate_mode("hybrid")  # no confirmation
        session.escalate_mode("hybrid", user_confirmed=True)
        self.assertEqual(session.mode, "hybrid")
        self.assertFalse(session.external_used)
        with self.assertRaises(ValueError):
            session.escalate_mode("vault", user_confirmed=True)  # no downgrade
        session.escalate_mode("external", user_confirmed=True)
        self.assertTrue(session.external_used)
        events = [h["event"] for h in session.history]
        self.assertEqual(events.count("mode-escalated"), 2)

    def test_proposal_decisions_are_recorded(self):
        session = InteractionSession("s1", "q")
        with self.assertRaises(ValueError):
            session.decide_proposal("accepted")
        prop = new_proposal("p1", "s1", "scope", ["hole"], ["alpha-2020-echo"])
        session.attach_proposal(prop)
        with self.assertRaises(ValueError):
            session.decide_proposal("maybe")
        session.decide_proposal("rejected", "not now")
        self.assertEqual(session.proposal_decision["decision"], "rejected")
        self.assertIn("proposal-rejected", [h["event"] for h in session.history])

    def test_rejection_changes_nothing_outside_the_session(self):
        session = InteractionSession("s1", "q")
        prop = new_proposal("p1", "s1", "scope", ["hole"], ["alpha-2020-echo"])
        session.attach_proposal(prop)
        session.decide_proposal("rejected", "declined")
        session.checkpoint(self.state)
        self.assertEqual(
            tree_paths(self.state), ["interaction/s1/session.json"]
        )  # nothing else was ever written


class TestCheckpointResume(SessionCase):
    def test_round_trip_preserves_everything(self):
        session = InteractionSession("s1", "what about echo?")
        session.set_candidates([{"node_id": "work:alpha-2020-echo", "why": ["term:echo"]}])
        session.set_coverage(new_report("partial", [COVERED, HOLE]))
        session.escalate_mode("hybrid", user_confirmed=True)
        path = session.checkpoint(self.state)
        resumed = InteractionSession.resume(self.state, "s1")
        self.assertEqual(resumed.question, "what about echo?")
        self.assertEqual(resumed.mode, "hybrid")
        self.assertEqual(resumed.coverage["verdict"], "partial")
        self.assertEqual(resumed.candidates[0]["node_id"], "work:alpha-2020-echo")
        self.assertEqual(len(resumed.history), len(session.history))
        # Idempotent: checkpointing the resumed session is byte-identical.
        before = path.read_bytes()
        InteractionSession.resume(self.state, "s1").checkpoint(self.state)
        self.assertEqual(path.read_bytes(), before)
        # external_used survives the round trip.
        session.escalate_mode("external", user_confirmed=True)
        session.checkpoint(self.state)
        self.assertTrue(InteractionSession.resume(self.state, "s1").external_used)

    def test_resume_after_expansion_recomputes_coverage(self):
        identity = load_vault_identity(MINI)
        session = InteractionSession("s2", "what drives foxtrot drift?")
        session.set_coverage(
            new_report("insufficient", [HOLE], proposal_ref="p2")
        )
        prop = new_proposal(
            "p2", "s2", "scope-drift", ["drift?"], ["alpha-2020-echo"], max_new=10
        )
        session.attach_proposal(prop, identity)
        session.decide_proposal("accepted", "expand first")
        session.checkpoint(self.state)

        run = materialize(session.proposal, "run-p2", identity)
        graph = {ALPHA_DOI: {"references": [rec("10.9/drift-src")], "cited_by": []}}
        reason = execute(run, StubGraphProvider(graph), identity, state_dir=self.state)
        self.assertEqual(reason, "frontier_exhausted")

        resumed = InteractionSession.resume(self.state, "s2")
        resumed.record("expansion-complete", "run-p2: 1 candidate")
        resumed.set_coverage(
            new_report(
                "partial",
                [new_subquestion("drift?", "covered", ["work:alpha-2020-echo"]), HOLE],
            )
        )
        resumed.checkpoint(self.state)
        final = InteractionSession.resume(self.state, "s2")
        events = [h["event"] for h in final.history]
        for expected in ("created", "coverage", "proposal", "proposal-accepted",
                         "expansion-complete"):
            self.assertIn(expected, events)
        self.assertEqual(final.coverage["verdict"], "partial")

    def test_sessions_are_deletable_derived_state(self):
        session = InteractionSession("s3", "q")
        session.checkpoint(self.state)
        shutil.rmtree(self.state / "interaction")
        fresh = InteractionSession("s3", "q")  # nothing depends on the old one
        fresh.checkpoint(self.state)
        self.assertTrue((self.state / "interaction" / "s3" / "session.json").is_file())


class TestIdeaAssessmentAttach(SessionCase):
    """Idea sessions reuse the ask-session machinery."""

    def _assessment(self):
        from knowledge_palace.interaction.novelty import new_assessment, new_profile

        return new_assessment(
            profile=new_profile("proj-x", ["mechanism"]),
            minimal_experiment="ablate on fixture data",
            falsifiers=["no gain kills it"],
            supporting=["claim:alpha-2020-echo#C1"],
        )

    def test_assessment_is_validated_attached_and_round_trips(self):
        session = InteractionSession("idea-1", "is my idea new?")
        with self.assertRaises(ValueError):
            session.set_assessment({"profile": {}})
        assessment = self._assessment()
        session.set_assessment(assessment)
        self.assertEqual(session.history[-1], {"event": "assessment", "detail": "proj-x"})
        session.checkpoint(self.state)
        resumed = InteractionSession.resume(self.state, "idea-1")
        self.assertEqual(resumed.assessment, assessment)

    def test_resume_tolerates_pre_kp08b_checkpoints(self):
        import json

        session = InteractionSession("old-1", "q")
        target = session.checkpoint(self.state)
        data = json.loads(target.read_text(encoding="utf-8"))
        del data["assessment"]
        target.write_text(json.dumps(data), encoding="utf-8")
        resumed = InteractionSession.resume(self.state, "old-1")
        self.assertIsNone(resumed.assessment)


if __name__ == "__main__":
    unittest.main()
