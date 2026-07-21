"""``/palace viewer export`` — the only write this package performs.

Resolves the four roots, builds the bundle, and writes ONE file at the
user-confirmed output path via temp+rename (a failed export never
leaves a partial file). The output path must be outside all four
private roots — the export is a user-designated artifact, never an
implicit Vault/Source/Workspace write.
"""

import argparse
import os
import sys
import tempfile
from pathlib import Path

from ..tools.config_resolver import ConfigError, resolve_roots
from .export import StaleIndexError, build_bundle, canonical_bytes
from .html_template import render

DEFAULT_FILENAME = "palace-viewer.html"


def _is_inside(path, root):
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def resolve_output_path(output, roots):
    target = Path(output).resolve() if output else Path.cwd() / DEFAULT_FILENAME
    for key in ("vault_dir", "state_dir", "source_dir", "workspace_dir"):
        if _is_inside(target, roots[key]):
            raise ValueError(
                "output path %s is inside the private root %s=%s — choose a "
                "location outside all four roots" % (target, key, roots[key])
            )
    return target


def export(output=None, config_path=None):
    """Build the bundle and write it atomically. Returns the output Path."""
    roots = resolve_roots(config_path)
    target = resolve_output_path(output, roots)
    payload = build_bundle(roots["vault_dir"], roots["state_dir"])
    html = render(canonical_bytes(payload))

    target.parent.mkdir(parents=True, exist_ok=True)
    handle, temp_name = tempfile.mkstemp(dir=str(target.parent), suffix=".part")
    try:
        with os.fdopen(handle, "wb") as fh:
            fh.write(html)
        os.replace(temp_name, str(target))
    except BaseException:
        Path(temp_name).unlink(missing_ok=True)
        raise
    return target


def run(argv):
    parser = argparse.ArgumentParser(
        prog="viewer export", description=__doc__.splitlines()[0]
    )
    parser.add_argument("output", nargs="?", help="output HTML path (default: ./%s)" % DEFAULT_FILENAME)
    parser.add_argument("--config", help="path to .palace.toml")
    args = parser.parse_args(argv)
    try:
        target = export(args.output, args.config)
    except StaleIndexError as err:
        print("viewer export: stale index — %s" % err)
        return 1
    except (ConfigError, ValueError, FileNotFoundError) as err:
        print("viewer export: %s" % err)
        return 1
    print("viewer export: wrote %s" % target)
    return 0


if __name__ == "__main__":
    sys.exit(run(sys.argv[1:]))
