"""Palace Viewer: a deterministic static export, not a server.

`export.build_bundle` walks the frozen GraphQueryPort exclusively —
never Source Cache, never a raw Vault scan — and emits one self-contained
HTML file a user opens via file://. No server process, no open network
port, no outbound network call from the emitted page, no new
dependency. `cli.py` is the `/palace viewer export` write path: the
export's own output file is the only write this package ever performs.
"""
