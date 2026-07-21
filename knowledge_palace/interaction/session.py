"""InteractionSession — resumable Q&A state in Derived State.

Sessions checkpoint under ``<state_dir>/interaction/<session_id>/`` as
canonical JSON and are deletable without knowledge loss (a
session is never the only home of a decision — confirmed knowledge lives
in the Vault, session history is convenience). Mode escalation
(vault → hybrid/external) is an explicit, recorded user decision.
"""

import json
from pathlib import Path

from .coverage import validate_report
from .novelty import validate_assessment
from .proposal import DECISIONS, validate_proposal

INTERACTION_DIRNAME = "interaction"
MODES = ("vault", "hybrid", "external")


class InteractionSession:
    def __init__(self, session_id, question, mode="vault"):
        if not session_id or not question:
            raise ValueError("session_id and question are required")
        if mode not in MODES:
            raise ValueError("mode %r not in %s" % (mode, list(MODES)))
        self.session_id = session_id
        self.question = question
        self.mode = mode
        self.subquestions = []
        self.candidates = []
        self.coverage = None
        self.assessment = None
        self.proposal = None
        self.proposal_decision = None
        self.external_used = False
        self.history = []
        self.record("created", "mode=%s" % mode)

    def record(self, event, detail=""):
        self.history.append({"event": event, "detail": detail})

    # -- retrieval ------------------------------------------------------------

    def set_candidates(self, candidates):
        self.candidates = list(candidates)
        self.record("prefilter", "%d candidates" % len(self.candidates))

    # -- coverage -------------------------------------------------------------

    def set_coverage(self, report, payload=None):
        errors = validate_report(report, payload)
        if errors:
            raise ValueError("invalid coverage report: %s" % errors)
        self.coverage = report
        self.record("coverage", report["verdict"])

    def set_assessment(self, assessment, payload=None):
        errors = validate_assessment(assessment, payload)
        if errors:
            raise ValueError("invalid idea assessment: %s" % errors)
        self.assessment = assessment
        self.record("assessment", assessment["profile"]["project_id"])

    # -- mode escalation (explicit user decision) ------------------------------

    def escalate_mode(self, new_mode, user_confirmed=False):
        if new_mode not in MODES:
            raise ValueError("mode %r not in %s" % (new_mode, list(MODES)))
        if MODES.index(new_mode) <= MODES.index(self.mode):
            raise ValueError("mode can only escalate (%s -> %s)" % (self.mode, new_mode))
        if not user_confirmed:
            raise ValueError(
                "hybrid/external are user opt-ins: escalation requires an "
                "explicit user confirmation"
            )
        self.mode = new_mode
        if new_mode == "external":
            self.external_used = True
        self.record("mode-escalated", "%s (user confirmed)" % new_mode)

    # -- proposal bridge --------------------------------------------------------

    def attach_proposal(self, proposal, vault_identity=None):
        errors = validate_proposal(proposal, vault_identity)
        if errors:
            raise ValueError("invalid proposal: %s" % errors)
        self.proposal = proposal
        self.proposal_decision = None
        self.record("proposal", proposal["proposal_id"])

    def decide_proposal(self, decision, why=""):
        if self.proposal is None:
            raise ValueError("no proposal attached")
        if decision not in DECISIONS:
            raise ValueError("decision %r not in %s" % (decision, list(DECISIONS)))
        self.proposal_decision = {"decision": decision, "why": why}
        self.record("proposal-" + decision, why)

    # -- checkpointing (Derived State) -------------------------------------------

    def _to_dict(self):
        return {
            "session_id": self.session_id,
            "question": self.question,
            "mode": self.mode,
            "subquestions": self.subquestions,
            "candidates": self.candidates,
            "coverage": self.coverage,
            "assessment": self.assessment,
            "proposal": self.proposal,
            "proposal_decision": self.proposal_decision,
            "external_used": self.external_used,
            "history": self.history,
        }

    def checkpoint(self, state_dir):
        target = (
            Path(state_dir) / INTERACTION_DIRNAME / self.session_id / "session.json"
        )
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(self._to_dict(), ensure_ascii=False, indent=1, sort_keys=True)
            + "\n",
            encoding="utf-8",
        )
        return target

    @classmethod
    def resume(cls, state_dir, session_id):
        target = Path(state_dir) / INTERACTION_DIRNAME / session_id / "session.json"
        data = json.loads(target.read_text(encoding="utf-8"))
        data.setdefault("assessment", None)  # older checkpoints predate this field
        session = cls.__new__(cls)
        for key, value in data.items():
            setattr(session, key, value)
        return session
