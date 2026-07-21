"""ExpansionProposal — the Ask→Expansion bridge (pure schema + one handoff).

An insufficient (or user-accepted partial) coverage verdict turns holes
into a bounded, user-confirmable proposal. Accepting it materializes a
bounded ExpansionRun (whose own gates govern any live traffic or Vault
write); rejecting it changes nothing anywhere.
"""

from ..expansion.run import MAX_DEPTH, MAX_NEW_CAP, ExpansionRun

DECISIONS = ("accepted", "rejected")


def new_proposal(
    proposal_id,
    session_id,
    scope,
    holes,
    seeds,
    queries=(),
    depth=2,
    max_new=50,
    rationale="",
):
    return {
        "proposal_id": proposal_id,
        "session_id": session_id,
        "scope": scope,
        "holes": list(holes),
        "seeds": list(seeds),
        "queries": list(queries),
        "depth": int(depth),
        "max_new": int(max_new),
        "rationale": rationale,
    }


def validate_proposal(proposal, vault_identity=None):
    """Return violations; empty means the proposal is confirmable."""
    errors = []
    for key in ("proposal_id", "session_id", "scope"):
        if not proposal.get(key):
            errors.append("missing %s" % key)
    if not proposal.get("holes"):
        errors.append("a proposal must name the coverage holes it addresses")
    if not proposal.get("seeds") and not proposal.get("queries"):
        errors.append("a proposal needs seeds and/or queries")
    if not 1 <= int(proposal.get("depth", 0)) <= MAX_DEPTH:
        errors.append("depth must be 1..%d" % MAX_DEPTH)
    if not 1 <= int(proposal.get("max_new", 0)) <= MAX_NEW_CAP:
        errors.append("max_new must be 1..%d" % MAX_NEW_CAP)
    if vault_identity is not None:
        for seed in proposal.get("seeds") or []:
            if seed not in vault_identity["works"]:
                errors.append("seed %r is not a Vault work" % seed)
    return errors


def materialize(proposal, run_id, vault_identity=None):
    """A CONFIRMED proposal becomes a valid ExpansionRun; invalid raises."""
    errors = validate_proposal(proposal, vault_identity)
    if errors:
        raise ValueError("proposal not confirmable: %s" % errors)
    if not proposal["seeds"]:
        raise ValueError(
            "query-only proposals need seed resolution first (search via the "
            "metadata providers is orchestrator territory)"
        )
    return ExpansionRun(
        run_id,
        proposal["scope"],
        proposal["seeds"],
        depth=proposal["depth"],
        max_new=proposal["max_new"],
    )
