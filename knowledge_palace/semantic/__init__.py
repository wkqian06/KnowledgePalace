"""Semantic layer: claim→concept bindings for new Claims, card evidence
tables, synthesis update tracking, and the typed-corridor prefilter.

Everything here is additive and read-only over parsed cards and the Graph
Index payload: historical claims (no bracket group) stay valid untouched and
the GraphQueryPort contract gains no new operation.
"""
