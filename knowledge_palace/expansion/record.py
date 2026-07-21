"""Compact expansion-run record builder — RETURNS text only.

Writing the record into the Vault is orchestrator territory: packaged
confirmation plus the vault-write gate. This module never touches any
root. Conforms to ``knowledge_palace/templates/expansion-run.md``.
"""


def _cell(value):
    """Free-form text (titles, reviewer reasons) must not break table rows."""
    return str(value).replace("|", "\\|").replace("\n", " ")


def build_record(run, started, provider_name="openalex"):
    """Render the compact run record (decisions and identities,
    never full candidate metadata or provider dumps)."""
    lines = [
        "---",
        "run: %s" % run.run_id,
        "scope: %s" % run.scope,
        "seeds: [%s]" % ", ".join(run.seeds),
        "depth: %d" % run.depth,
        "max_new: %d" % run.max_new,
        "provider: %s" % provider_name,
        "started: %s" % started,
        "stop_reason: %s" % (run.stop_reason or "user_stop"),
        "---",
        "",
        "# expansion-run %s" % run.run_id,
        "",
        "## Candidates (stable identities)",
        "",
        "| Key | Title | Year | Verified | Decision (%s) | Reason |" % run.scope,
        "|---|---|---|---|---|---|",
    ]
    for key in run.new_keys:
        entry = run.pool.get(key)
        decision = run.pool.decision_for(key, run.scope) or {}
        label = decision.get("decision", "undecided")
        if decision.get("exploratory"):
            label += " (exploratory)"
        lines.append(
            "| %s | %s | %s | %s | %s | %s |"
            % (
                key,
                _cell(entry.get("title") or "?"),
                entry.get("year") or "?",
                "yes" if entry["verified"] else "no",
                label,
                _cell(decision.get("reason", "")),
            )
        )
    lines += ["", "## Discovery occurrences", "", "| Candidate | Via | Direction | Depth |", "|---|---|---|---|"]
    for key in run.new_keys:
        for occurrence in run.pool.get(key)["occurrences"]:
            if occurrence["run"] != run.run_id:
                continue
            lines.append(
                "| %s | %s | %s | %d |"
                % (key, occurrence["via"], occurrence["direction"], occurrence["depth"])
            )
    lines += ["", "## Vault hits", "", "| Work | Via | Direction | Depth |", "|---|---|---|---|"]
    for hit in run.vault_hits:
        lines.append(
            "| %s | %s | %s | %d |" % (hit["slug"], hit["via"], hit["direction"], hit["depth"])
        )
    if run.warnings:
        lines += ["", "## Warnings (partial provider failures)", ""]
        lines += ["- %s" % warning for warning in run.warnings]
    return "\n".join(lines) + "\n"
