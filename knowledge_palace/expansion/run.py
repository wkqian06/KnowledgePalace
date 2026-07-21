"""ExpansionRun state machine with canonical-JSON checkpoints.

Derived State layout: the globally deduplicated pool lives at
``<state_dir>/expansion/candidates.json`` (shared across runs); each run's
frontier/progress lives at ``<state_dir>/expansion/<run_id>/checkpoint.json``.
Both are deletable: confirmed knowledge never depends on them.
"""

import json
from pathlib import Path

from .candidates import CandidatePool

EXPANSION_DIRNAME = "expansion"
POOL_FILENAME = "candidates.json"
STOP_REASONS = ("budget_reached", "frontier_exhausted", "user_stop")
MAX_DEPTH = 2
MAX_NEW_CAP = 50


class ExpansionRun:
    def __init__(self, run_id, scope, seeds, depth=2, max_new=50, pool=None):
        if not run_id or not scope:
            raise ValueError("run_id and scope are required")
        if not seeds:
            raise ValueError("at least one seed work is required")
        if not 1 <= int(depth) <= MAX_DEPTH:
            raise ValueError("depth must be 1..%d" % MAX_DEPTH)
        if not 1 <= int(max_new) <= MAX_NEW_CAP:
            raise ValueError("max_new must be 1..%d" % MAX_NEW_CAP)
        self.run_id = run_id
        self.scope = scope
        self.seeds = list(seeds)
        self.depth = int(depth)
        self.max_new = int(max_new)
        self.frontier = [{"slug": seed, "depth": 0} for seed in self.seeds]
        self.expanded = []
        self.new_keys = []  # unique verified non-Vault candidates THIS run
        self.vault_hits = []
        self.warnings = []
        self.stop_reason = None
        self.pool = pool if pool is not None else CandidatePool()

    # -- budget -------------------------------------------------------------

    def budget_used(self):
        return len(self.new_keys)

    def budget_reached(self):
        return self.budget_used() >= self.max_new

    def count_new(self, key):
        if key not in self.new_keys:
            self.new_keys.append(key)
        if self.budget_reached():
            self.stop_reason = "budget_reached"

    def add_vault_hit(self, slug, via, direction, depth):
        hit = {"slug": slug, "via": via, "direction": direction, "depth": depth}
        if hit not in self.vault_hits:
            self.vault_hits.append(hit)

    def stop(self, reason):
        if reason not in STOP_REASONS:
            raise ValueError("stop reason %r not in %s" % (reason, list(STOP_REASONS)))
        self.stop_reason = reason

    # -- checkpointing (Derived State) ---------------------------------------

    def _to_dict(self):
        return {
            "run_id": self.run_id,
            "scope": self.scope,
            "seeds": self.seeds,
            "depth": self.depth,
            "max_new": self.max_new,
            "frontier": self.frontier,
            "expanded": self.expanded,
            "new_keys": self.new_keys,
            "vault_hits": self.vault_hits,
            "warnings": self.warnings,
            "stop_reason": self.stop_reason,
        }

    def checkpoint(self, state_dir):
        base = Path(state_dir) / EXPANSION_DIRNAME
        base.mkdir(parents=True, exist_ok=True)
        pool_file = base / POOL_FILENAME
        # Merge the run-local pool over the shared file (run entries are newer).
        payload = (
            json.loads(pool_file.read_text(encoding="utf-8"))
            if pool_file.is_file()
            else {}
        )
        payload.update(self.pool.to_payload())
        pool_file.write_text(
            json.dumps(payload, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        run_dir = base / self.run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        (run_dir / "checkpoint.json").write_text(
            json.dumps(self._to_dict(), ensure_ascii=False, indent=1, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return run_dir / "checkpoint.json"

    @classmethod
    def resume(cls, state_dir, run_id):
        base = Path(state_dir) / EXPANSION_DIRNAME
        data = json.loads((base / run_id / "checkpoint.json").read_text(encoding="utf-8"))
        pool_file = base / POOL_FILENAME
        pool = CandidatePool.from_payload(
            json.loads(pool_file.read_text(encoding="utf-8")) if pool_file.is_file() else {}
        )
        run = cls(
            data["run_id"], data["scope"], data["seeds"],
            depth=data["depth"], max_new=data["max_new"], pool=pool,
        )
        run.frontier = data["frontier"]
        run.expanded = data["expanded"]
        run.new_keys = data["new_keys"]
        run.vault_hits = data["vault_hits"]
        run.warnings = data["warnings"]
        run.stop_reason = data["stop_reason"]
        return run
