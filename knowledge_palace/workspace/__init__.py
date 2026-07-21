"""Research Workspace: user territory, append-only revisions.

The Workspace is a private root like every other: Palace never runs Git
there, and only user-confirmed content enters it. The deterministic
pieces live here: the project skeleton (project), ProjectMaterial records
that can feed writing but never Vault Claims (material), the frozen
fingerprinted Project Brief that bounds every writer package (brief), the
two-round section review loop with the no-fabricated-Results guard
(writing), and the rNNN append-only revision store (revision). The
writing JUDGMENT belongs to palace-writer/palace-reviewer; auto drafts
and interim reviews live only in Derived State.
"""
