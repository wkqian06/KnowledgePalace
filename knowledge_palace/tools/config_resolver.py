"""Resolve the four private roots from ``<Framework root>/.palace.toml``.

Contract (PROTOCOL.md "Storage resolution"): relative values resolve against
the config file's directory, never the shell CWD; the four roots must exist
and be pairwise distinct. Python 3.9 floor: ``tomllib`` is unavailable, and
``.palace.toml`` is contractually exactly four ``key = "value"`` lines, so the
strict subset parser below is the spec, not a shortcut.
"""

import argparse
import sys
from pathlib import Path

REQUIRED_KEYS = ("vault_dir", "state_dir", "source_dir", "workspace_dir")


class ConfigError(ValueError):
    """A .palace.toml violation, with file/line evidence in the message."""


def framework_root():
    """The directory that contains this shared core (and .palace.toml)."""
    return Path(__file__).resolve().parents[2]


def parse_palace_toml(text, origin=".palace.toml"):
    """Parse the strict subset: blank lines, # comments, key = "value"."""
    values = {}
    for lineno, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        key, sep, rest = line.partition("=")
        key, rest = key.strip(), rest.strip()
        if not sep or not key.isidentifier():
            raise ConfigError(
                '%s:%d: expected `key = "value"`, got: %r' % (origin, lineno, raw)
            )
        if (
            len(rest) < 2
            or not rest.startswith('"')
            or not rest.endswith('"')
            or '"' in rest[1:-1]
        ):
            raise ConfigError(
                "%s:%d: value must be exactly one double-quoted string, got: %r"
                % (origin, lineno, raw)
            )
        if key in values:
            raise ConfigError("%s:%d: duplicate key %r" % (origin, lineno, key))
        values[key] = rest[1:-1]
    missing = [k for k in REQUIRED_KEYS if k not in values]
    extra = [k for k in values if k not in REQUIRED_KEYS]
    if missing or extra:
        raise ConfigError(
            "%s: keys must be exactly %s; missing=%s extra=%s"
            % (origin, list(REQUIRED_KEYS), missing, extra)
        )
    return values


def resolve_roots(config_path=None):
    """Return {key: absolute Path} for the four roots, fully validated."""
    path = Path(config_path) if config_path else framework_root() / ".palace.toml"
    if not path.is_file():
        raise ConfigError("config not found: %s" % path)
    values = parse_palace_toml(path.read_text(encoding="utf-8"), origin=str(path))
    base = path.resolve().parent
    roots = {}
    for key in REQUIRED_KEYS:
        root = (base / values[key]).resolve()
        if not root.is_dir():
            raise ConfigError(
                "%s: resolved root is not an existing directory: %s" % (key, root)
            )
        roots[key] = root
    seen = {}
    for key in REQUIRED_KEYS:
        root = roots[key]
        if root in seen:
            raise ConfigError(
                "%s and %s resolve to the same directory: %s" % (key, seen[root], root)
            )
        seen[root] = key
    return roots


def run(argv):
    parser = argparse.ArgumentParser(
        prog="config_resolver", description=__doc__.splitlines()[0]
    )
    parser.add_argument("--config", help="path to .palace.toml (default: Framework root)")
    parser.add_argument(
        "--check", action="store_true", help="validate only, print nothing on success"
    )
    args = parser.parse_args(argv)
    try:
        roots = resolve_roots(args.config)
    except ConfigError as err:
        print("config error: %s" % err, file=sys.stderr)
        return 2
    if not args.check:
        for key in REQUIRED_KEYS:
            print("%s = %s" % (key, roots[key].as_posix()))
    return 0


if __name__ == "__main__":
    sys.exit(run(sys.argv[1:]))
