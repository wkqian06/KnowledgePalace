"""Bounded expansion engine over an injected LiteratureProvider.

Frontier eligibility: only ingested Works (seeds), explicit
user roots, and Vault Hits expand further — metadata-only Candidates never
join the frontier, killing exponential low-quality growth. Depth is capped
at the run's depth (≤2): a C found at the boundary is recorded, never
expanded in the same Run. Partial provider failure becomes a run warning,
never a crash or a half-updated pool.
"""

from ..metadata.providers import ProviderError
from .candidates import build_hit_index, vault_hit

EXPLORATORY_CAP = 2
NEIGHBOR_LIMIT = 50


def _seed_ids(slug, vault_identity):
    work = vault_identity["works"].get(slug)
    return dict(work["external_ids"]) if work else {}


def _neighbors(provider, ids, run):
    """[(record, direction)] from references + cited_by; failures → warnings."""
    found = []
    for direction, call in (
        ("references", lambda: provider.references(ids)),
        ("cited_by", lambda: provider.cited_by(ids, limit=NEIGHBOR_LIMIT)),
    ):
        try:
            result = call()
        except ProviderError as err:
            run.warnings.append("%s %s: %s" % (direction, ids, err.detail))
            continue
        for item in result.get("items") or []:
            found.append((item, direction))
    return found


def expand_next(run, provider, vault_identity, hit_index=None):
    """Expand one frontier node. Returns False when the run has stopped."""
    if run.stop_reason:
        return False
    if not run.frontier:
        run.stop("frontier_exhausted")
        return False
    hit_index = hit_index if hit_index is not None else build_hit_index(vault_identity)
    node = run.frontier.pop(0)
    slug, node_depth = node["slug"], node["depth"]
    ids = node.get("ids") or _seed_ids(slug, vault_identity)
    if not ids:
        run.warnings.append("seed %s has no external ids; skipped" % slug)
        return True
    next_depth = node_depth + 1
    for record, direction in _neighbors(provider, ids, run):
        hit_slug = vault_hit(record, hit_index)
        if hit_slug:
            # Vault Hit: verify/record the edge, never re-ingest; hits may
            # expand further while depth remains.
            run.add_vault_hit(hit_slug, slug, direction, next_depth)
            already_queued = any(f["slug"] == hit_slug for f in run.frontier)
            if (
                next_depth < run.depth
                and hit_slug not in run.expanded
                and hit_slug not in run.seeds
                and not already_queued
            ):
                run.frontier.append(
                    {
                        "slug": hit_slug,
                        "depth": next_depth,
                        "ids": dict(
                            vault_identity["works"][hit_slug]["external_ids"]
                        ),
                    }
                )
            continue
        key, is_new = run.pool.upsert(record, run.run_id, slug, direction, next_depth)
        if key is None:
            run.warnings.append("unidentifiable neighbor of %s dropped" % slug)
            continue
        entry = run.pool.get(key)
        if is_new and entry["verified"]:
            run.count_new(key)  # sets budget_reached exactly at max_new
            if run.stop_reason:
                return False
        # Candidates never join the frontier (metadata-only rule).
    run.expanded.append(slug)
    return True


def execute(run, provider, vault_identity, state_dir=None):
    """Run to a stop reason; checkpoint after every node when state_dir given."""
    hit_index = build_hit_index(vault_identity)
    while expand_next(run, provider, vault_identity, hit_index):
        if state_dir is not None:
            run.checkpoint(state_dir)
    if state_dir is not None:
        run.checkpoint(state_dir)
    return run.stop_reason


def review_batch(run):
    """The normalized candidate package for palace-expansion-reviewer."""
    candidates = []
    for key in run.new_keys:
        entry = run.pool.get(key)
        candidates.append(
            {
                "key": key,
                "ids": entry["ids"],
                "title": entry["title"],
                "year": entry["year"],
                "occurrences": entry["occurrences"],
                "decision": run.pool.decision_for(key, run.scope),
            }
        )
    return {
        "schema_version": "1.0",
        "package_kind": "expansion-review-batch",
        "run": run.run_id,
        "scope": run.scope,
        "budget": {
            "max_new": run.max_new,
            "used": run.budget_used(),
            "stop_reason": run.stop_reason,
        },
        "exploratory_cap": EXPLORATORY_CAP,
        "candidates": candidates,
        "vault_hits": run.vault_hits,
    }


def apply_decisions(run, decisions, decided_via="auto"):
    """Record the reviewer's Scope-bound decisions.

    Decisions are confined to the reviewed batch (``run.new_keys``), and the
    exploratory cap counts SELECTED exploratory picks for this Run's scope in
    total — repeated calls cannot stack past it (re-decided keys count under
    their newest verdict).
    """
    for item in decisions:
        if item["key"] not in run.new_keys:
            raise ValueError(
                "decision for %r is outside the reviewed batch" % item["key"]
            )
    redecided = {item["key"] for item in decisions}
    existing = 0
    for key in run.new_keys:
        if key in redecided:
            continue
        verdict = run.pool.decision_for(key, run.scope) or {}
        if verdict.get("exploratory") and verdict.get("decision") == "selected":
            existing += 1
    proposed = sum(
        1
        for item in decisions
        if item.get("exploratory") and item["decision"] == "selected"
    )
    if existing + proposed > EXPLORATORY_CAP:
        raise ValueError(
            "%d exploratory selections would exceed the cap of %d for scope %r"
            % (existing + proposed, EXPLORATORY_CAP, run.scope)
        )
    for item in decisions:
        run.pool.decide(
            item["key"],
            run.scope,
            item["decision"],
            item.get("reason", ""),
            exploratory=item.get("exploratory", False),
            decided_via=decided_via,
        )
