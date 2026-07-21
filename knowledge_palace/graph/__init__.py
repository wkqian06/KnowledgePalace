"""Identity, rebuildable Graph Index, and the production GraphQueryPort.

Data flow: Vault (read-only) -> builder -> Derived State
index snapshot -> port. Nothing here ever writes to the Vault.
"""
