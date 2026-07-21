"""palace doctor — read-only diagnostics. Zero writes, zero network.

Reports: path resolvability and distinctness of the four configured roots,
shared-core presence, skill/agent contract completeness for both runtimes
(Claude Code and Codex), and Graph Index health (absent-rebuildable / fresh /
stale). Later Goals extend the check list; this tool never fixes anything.
"""

import argparse
import os
import sys
from pathlib import Path

from . import PROTOCOL_FILES, ROLES, TEMPLATE_FILES
from .config_resolver import REQUIRED_KEYS, ConfigError, framework_root, resolve_roots


def _presence(name, base, relpaths, checks):
    missing = [str(rel) for rel in relpaths if not (base / rel).is_file()]
    detail = (
        "%d/%d present" % (len(relpaths) - len(missing), len(relpaths))
        if missing
        else "complete (%d files)" % len(relpaths)
    )
    if missing:
        detail += "; missing: " + ", ".join(missing)
    checks.append((name, not missing, detail))


def run_checks(framework, config_path=None):
    """Return a list of (check-name, ok, detail). Performs reads only."""
    framework = Path(framework).resolve()
    checks = []

    roots = None
    try:
        roots = resolve_roots(config_path or framework / ".palace.toml")
        checks.append(
            (
                "config.roots",
                True,
                "; ".join("%s=%s" % (k, roots[k].as_posix()) for k in REQUIRED_KEYS),
            )
        )
        checks.append(("config.roots-distinct", True, "4 roots, pairwise distinct"))
    except ConfigError as err:
        checks.append(("config.roots", False, str(err)))

    if roots is not None:
        # Light staleness check only: an absent index never touches the Vault;
        # a present index costs one fingerprint pass. Full idempotence
        # verification belongs to `graph.builder --check`.
        from ..graph.builder import load_index, vault_fingerprint

        document = load_index(roots["state_dir"])
        if document is None:
            checks.append(
                (
                    "index.graph",
                    True,
                    "absent — rebuildable (python3 -m knowledge_palace.graph.builder --rebuild)",
                )
            )
        else:
            served = document["snapshot"]["vault_fingerprint"]
            current = vault_fingerprint(roots["vault_dir"])
            if served == current:
                checks.append(
                    ("index.graph", True, "fresh (%s)" % document["snapshot"]["snapshot_id"])
                )
            else:
                checks.append(
                    (
                        "index.graph",
                        False,
                        "stale — index %s != vault %s; rebuild" % (served[:12], current[:12]),
                    )
                )

    checks.append(
        (
            "providers.config",
            True,
            "mailto:%s; s2_key:%s (optional env vars; values never printed)"
            % (
                "present" if os.environ.get("PALACE_MAILTO") else "absent",
                "present" if os.environ.get("PALACE_S2_API_KEY") else "absent",
            ),
        )
    )
    if roots is not None:
        snapshots = roots["state_dir"] / "impact" / "snapshots.json"
        checks.append(
            (
                "index.impact",
                True,
                "present (%s)" % snapshots
                if snapshots.is_file()
                else "absent — rebuildable by `palace refresh` (network-gated)",
            )
        )

    if roots is not None:
        from ..graph.identity import parse_frontmatter, split_frontmatter

        missing_pointers = []
        papers_dir = roots["vault_dir"] / "papers"
        for card in sorted(papers_dir.glob("*.md")) if papers_dir.is_dir() else []:
            if card.name == "INDEX.md":
                continue
            fm_lines, _, _ = split_frontmatter(card.read_text(encoding="utf-8"), card.name)
            fields, _ = parse_frontmatter(fm_lines, card.name)
            local = fields.get("local")
            if local and not (roots["source_dir"] / local).is_file():
                missing_pointers.append(card.stem)
        checks.append(
            (
                "source.cache",
                True,  # advisory: missing full text is source_unavailable,
                       # a normal deferred-acquisition state — never a failure
                "all card local: pointers resolve"
                if not missing_pointers
                else "%d source_unavailable (report-only, existing Claims "
                "unaffected): %s" % (len(missing_pointers), missing_pointers[:5]),
            )
        )
    checks.append(
        (
            "providers.institutional",
            True,
            "experimental (disabled) — never reported ready in V1",
        )
    )
    if roots is not None:
        interaction_dir = roots["state_dir"] / "interaction"
        session_count = (
            len([p for p in interaction_dir.iterdir() if p.is_dir()])
            if interaction_dir.is_dir()
            else 0
        )
        checks.append(
            (
                "interaction.sessions",
                True,  # advisory: sessions are deletable Derived State
                "%d session(s)" % session_count
                if session_count
                else "absent — nothing in progress",
            )
        )
    if roots is not None:
        projects_dir = roots["workspace_dir"] / "projects"
        project_count = (
            len([p for p in projects_dir.iterdir() if p.is_dir()])
            if projects_dir.is_dir()
            else 0
        )
        checks.append(
            (
                "workspace.projects",
                True,  # advisory: the Workspace is user territory
                "%d project(s)" % project_count
                if project_count
                else "absent — no research projects yet",
            )
        )
    if roots is not None:
        expansion_dir = roots["state_dir"] / "expansion"
        run_count = (
            len([p for p in expansion_dir.iterdir() if p.is_dir()])
            if expansion_dir.is_dir()
            else 0
        )
        checks.append(
            (
                "expansion.checkpoints",
                True,  # advisory: checkpoints are deletable Derived State
                "%d run checkpoint dir(s)" % run_count
                if run_count
                else "absent — nothing in progress",
            )
        )

    core = framework / "knowledge_palace"
    _presence("shared.protocol", core / "protocol", PROTOCOL_FILES, checks)
    _presence(
        "shared.role-contracts",
        core / "agents",
        ["palace-%s.md" % role for role in ROLES],
        checks,
    )
    _presence("shared.templates", core / "templates", TEMPLATE_FILES, checks)

    _presence(
        "runtime.claude",
        framework,
        [Path(".claude/skills/knowledge-palace/SKILL.md")]
        + [Path(".claude/agents/palace-%s.md" % role) for role in ROLES],
        checks,
    )
    _presence(
        "runtime.codex",
        framework,
        [
            Path(".agents/skills/knowledge-palace/SKILL.md"),
            Path(".agents/skills/knowledge-palace/agents/openai.yaml"),
        ]
        + [Path(".codex/agents/palace-%s.toml" % role) for role in ROLES],
        checks,
    )
    return checks


def run(argv):
    parser = argparse.ArgumentParser(prog="doctor", description=__doc__.splitlines()[0])
    parser.add_argument(
        "--framework", help="Framework root (default: this shared core's root)"
    )
    parser.add_argument("--config", help="path to .palace.toml (default: <framework>/.palace.toml)")
    args = parser.parse_args(argv)
    framework = Path(args.framework).resolve() if args.framework else framework_root()
    checks = run_checks(framework, args.config)
    for name, ok, detail in checks:
        print("%s %s — %s" % ("OK  " if ok else "FAIL", name, detail))
    failed = [name for name, ok, _ in checks if not ok]
    print(
        "doctor: %d checks, %d failed%s"
        % (len(checks), len(failed), (": " + ", ".join(failed)) if failed else "")
    )
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(run(sys.argv[1:]))
