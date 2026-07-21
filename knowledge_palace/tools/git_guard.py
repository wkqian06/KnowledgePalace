"""Git target guard — refuse any Palace Git invocation whose CWD or target is
not the Public Framework, and refuse push without explicit user
authorization.

Advisory defense-in-depth: the protocol's behavioral rules and the runtime
sandbox remain the primary enforcement; this tool gives the orchestrator a
deterministic pre-flight verdict with evidence before it runs `git`.
"""

import argparse
import sys
from pathlib import Path

# Global git options that consume the following argv element.
_VALUE_OPTS = ("-C", "-c", "--git-dir", "--work-tree", "--namespace")
# Directory-targeting options that must stay inside the Framework.
_DIR_OPTS = ("-C", "--git-dir", "--work-tree")


def _inside(path, root):
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def check(git_args, cwd, framework, allow_push=False):
    """Return (allowed, reason). Never executes git."""
    framework = Path(framework).resolve()
    effective_cwd = Path(cwd).resolve()
    if not _inside(effective_cwd, framework):
        return False, "CWD %s is outside the Public Framework %s" % (
            effective_cwd,
            framework,
        )

    args = list(git_args)
    subcommand = None
    tail = []
    i = 0
    while i < len(args):
        arg = args[i]
        if arg in _VALUE_OPTS:
            if i + 1 >= len(args):
                return False, "dangling %s without a value" % arg
            value = args[i + 1]
            if arg in _DIR_OPTS:
                target = (effective_cwd / value).resolve()
                if arg == "-C":
                    effective_cwd = target
                if not _inside(target, framework):
                    return False, "%s target %s is outside the Public Framework %s" % (
                        arg,
                        target,
                        framework,
                    )
            i += 2
            continue
        if arg.startswith("--git-dir=") or arg.startswith("--work-tree="):
            opt, _, value = arg.partition("=")
            target = (effective_cwd / value).resolve()
            if not _inside(target, framework):
                return False, "%s target %s is outside the Public Framework %s" % (
                    opt,
                    target,
                    framework,
                )
            i += 1
            continue
        if arg.startswith("-"):
            i += 1
            continue
        subcommand = arg
        tail = args[i + 1 :]
        break

    if subcommand is None:
        return True, "no subcommand; git invocation stays inside %s" % framework

    if subcommand == "push" and not allow_push:
        return (
            False,
            "push refused: Palace never pushes automatically; rerun with "
            "--user-authorized-push only on an explicit user instruction",
        )

    for arg in tail:
        if arg.startswith("-"):
            continue
        candidate = Path(arg) if Path(arg).is_absolute() else effective_cwd / arg
        try:
            resolved = candidate.resolve()
        except OSError:
            continue
        # ponytail: only arguments that resolve to EXISTING paths are checked —
        # refs like origin/main are not paths and skate through. The guard is
        # advisory; upgrade path: per-subcommand argv parsing if this ever
        # gates unattended automation.
        if resolved.exists() and not _inside(resolved, framework):
            return False, "argument %r resolves to %s, outside the Public Framework %s" % (
                arg,
                resolved,
                framework,
            )

    return True, "allowed: git %s (effective cwd %s)" % (" ".join(git_args), effective_cwd)


def run(argv):
    parser = argparse.ArgumentParser(
        prog="git_guard",
        description=__doc__.splitlines()[0],
        usage="git_guard.py [options] -- <git-args...>",
    )
    parser.add_argument(
        "--framework", help="Framework root (default: this shared core's root)"
    )
    parser.add_argument("--cwd", default=".", help="CWD the git command would run in")
    parser.add_argument(
        "--user-authorized-push",
        action="store_true",
        help="the user explicitly instructed this push",
    )
    parser.add_argument("git_args", nargs=argparse.REMAINDER, metavar="git-args")
    args = parser.parse_args(argv)

    from .config_resolver import framework_root

    framework = Path(args.framework).resolve() if args.framework else framework_root()
    git_args = args.git_args
    if git_args and git_args[0] == "--":
        git_args = git_args[1:]
    if git_args and git_args[0] == "git":
        git_args = git_args[1:]
    allowed, reason = check(
        git_args, Path(args.cwd), framework, allow_push=args.user_authorized_push
    )
    print(("ALLOW: " if allowed else "REFUSE: ") + reason, file=None if allowed else sys.stderr)
    return 0 if allowed else 3


if __name__ == "__main__":
    sys.exit(run(sys.argv[1:]))
