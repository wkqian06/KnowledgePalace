"""Semantic layer: claim→concept bindings for NEW ingests,
StudyProfile role views, and the typed-corridor prefilter.

Everything here is additive and read-only: historical claims (no bracket
group) stay valid untouched, profiles are views over anchored Claims (never
a second store of facts), and corridors traverse only the Graph Index
payload — the whole Vault never enters a prompt, and the frozen
GraphQueryPort contract gains no new operation.
"""
