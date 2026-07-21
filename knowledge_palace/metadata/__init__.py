"""Metadata providers, bibliographic cache, contextual impact, refresh flow.

The ONLY network entry in the shared core is ``refresh --live`` (gated by
explicit network authorization); everything else runs on injected stub transports or the
on-disk Bibliographic Cache. Snapshots and bands are Derived State — dated
observations, deletable, rebuildable by a future refresh.
"""
