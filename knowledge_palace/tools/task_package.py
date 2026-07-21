"""Deterministic task-package builder.

The single dispatch code path for both runtimes (Claude Code and Codex): a
runtime adapter hands the orchestrator's chosen fixture/inputs and role to
this tool and dispatches the returned package verbatim, so the package schema
cannot drift between runtimes. Deterministic by construction: no timestamps,
no randomness, no CWD dependence.
"""

import argparse
import hashlib
import json
import sys
from pathlib import Path

from . import ROLES, SCHEMA_VERSION
from .config_resolver import framework_root

EXPECTED_OUTPUT = {
    "extractor": "paper-card draft (Verdict/Evidence/Draft/Open questions)",
    "linker": "slug alignments + gap-relation tables (Verdict/Evidence/Draft/Open questions)",
    "scout": "transfer-card candidates (Verdict/Evidence/Draft/Open questions)",
    "auditor": "findings table (Verdict/Evidence/Draft/Open questions)",
    "analyst": "brief/ask/idea/intro draft (Verdict/Evidence/Draft/Open questions)",
    "stylist": "style bank card or profile draft (Verdict/Evidence/Draft/Open questions)",
    "expansion-reviewer": "candidate decision table (Verdict/Evidence/Draft/Open questions)",
    "writer": "section or document draft (Verdict/Evidence/Draft/Open questions)",
    "reviewer": "scholarly findings table (Verdict/Evidence/Draft/Open questions)",
}


def build(fixture_path, role, framework=None):
    """Build the task package for one role over one fixture input."""
    if role not in ROLES:
        raise ValueError("unknown role %r; roles are %s" % (role, list(ROLES)))
    base = Path(framework).resolve() if framework else framework_root()
    fixture = Path(fixture_path).resolve()
    digest = hashlib.sha256(fixture.read_bytes()).hexdigest()
    try:
        shown = fixture.relative_to(base).as_posix()
    except ValueError:
        shown = fixture.name
    return {
        "schema_version": SCHEMA_VERSION,
        "package_kind": "palace-task",
        "role": role,
        "contract": "knowledge_palace/agents/palace-%s.md" % role,
        "protocol": [
            "knowledge_palace/protocol/PROTOCOL.md",
            "knowledge_palace/protocol/COMMANDS.md",
        ],
        "templates_dir": "knowledge_palace/templates",
        "inputs": {
            "fixture": {"path": shown, "sha256": digest},
            "candidates": [],
        },
        "constraints": {
            "read_only": True,
            "tools": ["Read", "Grep", "Glob"],
            "writes_files": False,
            "whole_vault_scan": False,
        },
        "expected_output": EXPECTED_OUTPUT[role],
    }


def to_json(package):
    return json.dumps(package, indent=2, sort_keys=True) + "\n"


def run(argv):
    parser = argparse.ArgumentParser(
        prog="task_package", description=__doc__.splitlines()[0]
    )
    parser.add_argument("--fixture", required=True, help="input file for the role")
    parser.add_argument("--role", required=True, choices=sorted(ROLES))
    parser.add_argument(
        "--framework", help="Framework root (default: this shared core's root)"
    )
    args = parser.parse_args(argv)
    try:
        package = build(args.fixture, args.role, args.framework)
    except (OSError, ValueError) as err:
        print("task_package error: %s" % err, file=sys.stderr)
        return 2
    sys.stdout.write(to_json(package))
    return 0


if __name__ == "__main__":
    sys.exit(run(sys.argv[1:]))
