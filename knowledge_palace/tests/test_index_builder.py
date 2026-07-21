"""Idempotent rebuild, Derived-State-only
writes, zero Vault rewrites, correct graph shape."""

import hashlib
import shutil
import tempfile
import unittest
from pathlib import Path

from knowledge_palace.graph.builder import (
    build_payload,
    canonical_bytes,
    check,
    payload_fingerprint,
    vault_fingerprint,
    write_index,
)

MINI = Path(__file__).resolve().parent / "fixtures" / "vault-mini"


def tree_digest(base):
    return [
        (path.relative_to(base).as_posix(), hashlib.sha256(path.read_bytes()).hexdigest())
        for path in sorted(base.rglob("*"))
        if path.is_file()
    ]


class TestFingerprint(unittest.TestCase):
    def test_stable_and_content_sensitive(self):
        first = vault_fingerprint(MINI)
        self.assertEqual(first, vault_fingerprint(MINI))
        with tempfile.TemporaryDirectory() as td:
            copy = Path(td) / "vault"
            shutil.copytree(MINI, copy)
            self.assertEqual(vault_fingerprint(copy), first)  # path-independent
            with (copy / "papers" / "alpha-2020-echo.md").open("a", encoding="utf-8") as fh:
                fh.write("\n")
            self.assertNotEqual(vault_fingerprint(copy), first)


class TestBuild(unittest.TestCase):
    def test_payload_build_is_idempotent(self):
        one, two = build_payload(MINI), build_payload(MINI)
        self.assertEqual(canonical_bytes(one), canonical_bytes(two))
        self.assertEqual(payload_fingerprint(one), payload_fingerprint(two))

    def test_delete_and_rebuild_yields_identical_fingerprints(self):
        with tempfile.TemporaryDirectory() as td:
            state = Path(td) / "state"
            _, first = write_index(MINI, state)
            shutil.rmtree(state / "graph-index")
            _, second = write_index(MINI, state)
            self.assertEqual(first["payload_fingerprint"], second["payload_fingerprint"])
            self.assertEqual(first["snapshot"]["snapshot_id"], second["snapshot"]["snapshot_id"])
            self.assertEqual(
                canonical_bytes(first["payload"]), canonical_bytes(second["payload"])
            )

    def test_zero_vault_writes_and_state_confinement(self):
        before = tree_digest(MINI)
        with tempfile.TemporaryDirectory() as td:
            state = Path(td) / "state"
            write_index(MINI, state)
            written = [p.relative_to(state).as_posix() for p in state.rglob("*") if p.is_file()]
            self.assertEqual(written, ["graph-index/index.json"])
        self.assertEqual(tree_digest(MINI), before)

    def test_graph_shape(self):
        payload = build_payload(MINI)
        nodes, parents = payload["nodes"], payload["parents"]
        edge_ids = {edge["id"] for edge in payload["edges"]}
        self.assertEqual(
            parents["concept:concept-gamma"], ["domain:alpha-domain", "domain:beta-domain"]
        )
        self.assertIn("work:alpha-2020-echo|supports|gap:gap-echo-noise", edge_ids)
        self.assertIn("work:gamma-2022-bridge|identifies|gap:gap-gamma-drift", edge_ids)
        self.assertIn(
            "transfer:transfer-echo-to-gamma|transfer-from|concept:concept-echo", edge_ids
        )
        self.assertIn(
            "transfer:transfer-echo-to-gamma|transfer-to|gap:gap-gamma-drift", edge_ids
        )
        claim_nodes = [nid for nid, view in nodes.items() if view["kind"] == "claim"]
        self.assertEqual(len(claim_nodes), 4)
        self.assertEqual(parents["claim:alpha-2020-echo#C1"], ["work:alpha-2020-echo"])
        brief = nodes["brief:2026-07-13-gaps"]
        self.assertEqual(brief["attrs"], {"role": "view", "evidence_capable": False})
        self.assertFalse(
            [e for e in payload["edges"] if e["from"].startswith("brief:")],
            "briefs must emit zero edges",
        )
        report = payload["identity_report"]
        self.assertEqual(report["works"], 3)
        self.assertEqual(report["claims"], 4)
        self.assertEqual(report["unresolved_refs"], [])
        self.assertEqual(report["parse_errors"], [])

    def test_dangling_transfer_refs_are_reported(self):
        with tempfile.TemporaryDirectory() as td:
            vault = Path(td) / "vault"
            shutil.copytree(MINI, vault)
            transfer = vault / "transfers" / "transfer-echo-to-gamma.md"
            text = transfer.read_text(encoding="utf-8")
            text = text.replace("papers: [alpha-2020-echo]", "papers: [ghost-paper]")
            text = text.replace("gaps: [gap-gamma-drift]", "gaps: [gap-ghost]")
            transfer.write_text(text, encoding="utf-8")
            unresolved = build_payload(vault)["identity_report"]["unresolved_refs"]
            self.assertTrue(any("'ghost-paper'" in item for item in unresolved), unresolved)
            self.assertTrue(any("'gap-ghost'" in item for item in unresolved), unresolved)

    def test_check_absent_fresh_stale(self):
        with tempfile.TemporaryDirectory() as td:
            vault = Path(td) / "vault"
            state = Path(td) / "state"
            shutil.copytree(MINI, vault)
            self.assertEqual(check(vault, state)[0], "absent")
            write_index(vault, state)
            self.assertEqual(check(vault, state)[0], "fresh")
            with (vault / "papers" / "alpha-2020-echo.md").open("a", encoding="utf-8") as fh:
                fh.write("\n")
            status, detail = check(vault, state)
            self.assertEqual(status, "stale")
            self.assertIn("rebuild", detail)


if __name__ == "__main__":
    unittest.main()
