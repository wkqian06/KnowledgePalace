"""Interaction layer: coverage-driven grounded Q&A machinery.

Coverage — not Domain — gates answering. The deterministic pieces live
here: bounded id-only retrieval (prefilter), the CoverageReport schema that
controls what each verdict may imply, the ExpansionProposal bridge into
bounded expansion runs, and resumable InteractionSessions in Derived State. The
coverage JUDGMENT itself belongs to palace-analyst; external material is
session-local by schema and can never become Vault-eligible.

Idea refinement rides the same sessions: profile-relative
novelty over a 10/15/30 coarse-to-fine pipeline (novelty), plus
Vault-first author references and the recorded external-novelty opt-in
(project_source).
"""
