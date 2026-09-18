"""Research Workspace: user territory, append-only revisions.

The Workspace is a private root like every other: Palace never runs Git
there, and only user-confirmed content enters it. The deterministic pieces
live here: the project skeleton (project), ProjectMaterial records that can
feed writing but never Vault Claims (material), the Project Brief that names
the evidence a section is written from (brief), manuscript inputs and precise
passage replacement (writing), the rNNN append-only revision store (revision)
and the project research context (research_helpers). Writing judgment belongs
to the agent and the writing workflow.
"""
